import asyncio
import json
import logging

from concurrent.futures import ThreadPoolExecutor
import os
import re
import uuid

import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pytgcalls import PyTgCalls
from pytgcalls import filters as fl
from pytgcalls.types import AudioQuality, MediaStream, StreamEnded, VideoQuality

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
log = logging.getLogger("ARIA-MUSIC")

# ================== الإعدادات ==================
API_ID = int(os.environ.get("API_ID", "0") or 0)
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
DEV_ID = 6913101408  # المطور: كل الإعدادات من الخاص

# كوكيز يوتيوب اختيارية (تسويها لاحقاً لو حبيت): تلصق محتوى ملف cookies.txt
YOUTUBE_COOKIES = os.environ.get("YOUTUBE_COOKIES", "").strip()
COOKIE_FILE = None
if YOUTUBE_COOKIES:
    try:
        COOKIE_FILE = "/tmp/yt_cookies.txt"
        with open(COOKIE_FILE, "w") as f:
            f.write(YOUTUBE_COOKIES)
        log.info("YouTube cookies loaded from env")
    except Exception as e:
        log.error(f"cookies write error: {e}")

if not (API_ID and API_HASH and BOT_TOKEN):
    raise SystemExit("ناقص متغيرات البيئة: API_ID, API_HASH, BOT_TOKEN")

BOT_NAME = "موسيقى ARIA"

bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=8)
call_py = PyTgCalls(bot)

QUEUE = {}         # chat_id -> [item, ...]
PLAYING = {}       # chat_id -> item الشغال حاليا
PAUSED = {}        # chat_id -> True/False
LOOP = {}          # chat_id -> True/False
VOLUME = {}        # chat_id -> رقم الصوت
MSG_IDS = {}       # chat_id -> id رسالة "يشغل الآن"
SEARCH_CACHE = {}  # مفتاح البحث -> بيانات الأغنية

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "thumb": None,
    "reply_photo": True,
    "audio_q": "high",
    "video_q": "720",
}
CONFIG = dict(DEFAULT_CONFIG)
try:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            CONFIG.update(json.load(f))
except Exception:
    pass


def save_config():
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(CONFIG, f)
    except Exception as e:
        log.error(f"config save error: {e}")


AUDIO_QUALITY_MAP = {
    "high": AudioQuality.HIGH,
    "medium": getattr(AudioQuality, "MEDIUM", AudioQuality.HIGH),
    "low": getattr(AudioQuality, "LOW", AudioQuality.HIGH),
}
VIDEO_QUALITY_MAP = {
    "720": VideoQuality.HD_720p,
    "480": getattr(VideoQuality, "SD_480p", VideoQuality.HD_720p),
    "360": getattr(VideoQuality, "SD_360p", VideoQuality.HD_720p),
}
AUDIO_Q_LABEL = {"high": "عالية", "medium": "متوسطة", "low": "منخفضة"}

HELP_TEXT = (
    f"🎵 <b>{BOT_NAME}</b>\n\n"
    "• <code>شغل</code> + اسم الأغنية ← تشغيل صوت 🎵\n"
    "• <code>فيد</code> + اسم الأغنية ← تشغيل فيديو 🎬\n"
    "• <code>يوت</code> + اسم الأغنية ← اختيار فيديو أو صوت بأزرار\n"
    "• <code>تخطي</code> ← الأغنية التالية ⏭\n"
    "• <code>اسكت</code> ← إيقاف مؤقت ⏸\n"
    "• <code>كمل</code> ← يكمل من وين توقف ▶️\n"
    "• <code>ايقاف</code> ← إيقاف الكل والخروج ⏹\n"
    "• <code>تكرار</code> ← تشغيل الأغنية على طول 🔁\n"
    "• <code>الصوت</code> + رقم (مثال: الصوت 200) 🔊\n"
    "• <code>قائمة</code> ← عرض قائمة الانتظار 📝\n"
    "• <code>الوقت</code> ← وين وصلت الأغنية ⏱\n"
    "• تقدر تلصق <b>رابط يوتيوب أو ساوند كلاود</b> مباشرة 🔗\n\n"
    "⚠️ لازم تكون المكالمة الصوتية مفتوحة والبوت أدمن"
)


# ================== مصادر التشغيل ==================
class SourceError(Exception):
    pass


def ydl_opts(client=None, flat=False):
    o = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        "nocheckcertificate": True,
        "geo_bypass": True,
        "socket_timeout": 10,
        "retries": 1,
        "extractor_retries": 1,
    }
    if COOKIE_FILE:
        o["cookiefile"] = COOKIE_FILE
    if flat:
        o["extract_flat"] = "in_playlist"
    if client and client != "default":
        o["extractor_args"] = {"youtube": {"player_client": [client]}}
    return o


def flat_search(query, n=5):
    """بحث سريع في يوتيوب بدون فتح صفحة الفيديو (ما ينحجب)"""
    with yt_dlp.YoutubeDL(ydl_opts(flat=True)) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    entries = [e for e in (info or {}).get("entries", []) if e and e.get("id")]
    if not entries:
        raise SourceError("no yt results")
    best = next((e for e in entries if e.get("duration")), entries[0])
    vid = best["id"]
    return {
        "title": best.get("title") or query,
        "q": query,
        "url": f"https://www.youtube.com/watch?v={vid}",
        "dur": int(best.get("duration") or 0),
        "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
    }


def pick_format(info, want_video):
    """يختار أفضل رابط تشغيل مباشر من بيانات yt-dlp"""
    fmts = info.get("formats") or []
    if want_video:
        combined = [f for f in fmts
                    if f.get("vcodec") not in (None, "none")
                    and f.get("acodec") not in (None, "none")
                    and f.get("url")]
        chosen = combined[-1] if combined else None
    else:
        audio = [f for f in fmts
                 if f.get("acodec") not in (None, "none")
                 and f.get("vcodec") in (None, "none")
                 and f.get("url")]
        if not audio:
            audio = [f for f in fmts if f.get("acodec") not in (None, "none") and f.get("url")]
        chosen = audio[-1] if audio else None
    if not chosen or not chosen.get("url"):
        if info.get("url"):
            chosen = {"url": info["url"]}
        else:
            raise SourceError("no formats")
    return {
        "stream_url": chosen["url"],
        "title": info.get("title") or "",
        "dur": int(info.get("duration") or 0),
        "thumb": info.get("thumbnail"),
    }


YT_CLIENTS = ["ios", "mweb"]


def yt_full_extract(url, want_video=False):
    """يجرب عدة واجهات يوتيوب عشان يتفادى الحجب"""
    last_err = None
    for client in YT_CLIENTS:
        try:
            with yt_dlp.YoutubeDL(ydl_opts(client=client)) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise SourceError("empty info")
            return pick_format(info, want_video)
        except Exception as ex:
            last_err = ex
            log.warning(f"extract via {client} failed: {str(ex)[:120]}")
            continue
    raise SourceError(last_err or "all clients failed")


def sc_queries(item):
    """صيغ بحث ذكية لساوند كلاود: نص المستخدم أولاً ثم العنوان المنظف"""
    qs = []
    if item.get("q"):
        qs.append(item["q"])
    title = item.get("title") or ""
    base = re.split(r"\s*[|\-–—،]\s*", title)[0].strip()
    if base:
        qs.append(base)
    # كلمات عربية فقط بدون الكلمات الإنجليزية الزائدة
    ar = [w for w in title.split() if not re.match(r"^[A-Za-z0-9()&.:\-]+$", w)]
    if ar:
        qs.append(" ".join(ar[:6]))
    qs.append(title)
    return list(dict.fromkeys(q for q in qs if q))


def sc_fallback(item):
    """بحث بديل في ساوند كلاود (ما ينحجب من سيرفرات الاستضافة)"""
    for q in sc_queries(item):
        try:
            with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
                info = ydl.extract_info(f"scsearch4:{q}", download=False)
            for e in (info or {}).get("entries") or []:
                if not e:
                    continue
                fmts = [f for f in (e.get("formats") or []) if f.get("acodec") not in (None, "none") and f.get("url")]
                if not fmts:
                    continue
                return {
                    "stream_url": fmts[-1]["url"],
                    "title": e.get("title") or q,
                    "dur": int(e.get("duration") or 0),
                    "thumb": e.get("thumbnail"),
                }
        except Exception:
            continue
    raise SourceError("no sc results")


def resolve_stream(item):
    """يحول الأغنية إلى رابط تشغيل مباشر بأسرع طريقة:
    يشتغل على يوتيوب وساوند كلاود بنفس الوقت ويخذ اللي يخلص أولاً"""
    if item.get("stream_url"):
        return item["stream_url"]

    def yt_try():
        return yt_full_extract(item["url"], want_video=bool(item.get("video")))

    with ThreadPoolExecutor(max_workers=2) as ex:
        yt_fut = ex.submit(yt_try)
        sc_fut = ex.submit(sc_fallback, item)
        # نعطي يوتيوب 8 ثواني بس (أحياناً يكون محجوب وبطيء)
        yt_done = yt_fut.done()
        if not yt_done:
            import time
            deadline = time.time() + 8
            while time.time() < deadline and not yt_fut.done():
                time.sleep(0.2)
        if yt_fut.done() and yt_fut.exception() is None:
            res = yt_fut.result()
            item.update(res)
            item["source"] = "youtube"
            sc_fut.cancel()
            return res["stream_url"]
        # يوتيوب فشل أو بطيء => ساوند كلاود (غالباً جاهز من زمان)
        try:
            res = sc_fut.result(timeout=15)
            res["video"] = False
            item.update(res)
            item["source"] = "soundcloud"
            return res["stream_url"]
        except Exception:
            # ساوند كلاود تعثر مرة، نعطيه محاولة ثانية سريعة
            try:
                res = ex.submit(sc_fallback, item).result(timeout=15)
                res["video"] = False
                item.update(res)
                item["source"] = "soundcloud"
                return res["stream_url"]
            except Exception:
                pass
            # ما فيه ساوند كلاود => ننتظر يوتيوب للآخر
            try:
                res = yt_fut.result(timeout=25)
                item.update(res)
                item["source"] = "youtube"
                return res["stream_url"]
            except Exception as e:
                raise SourceError(e)


def search_track(query):
    """يبحث عن الأغنية ويرجع بياناتها الأساسية"""
    if re.match(r"^https?://", query):
        is_sc = "soundcloud.com" in query
        is_yt = ("youtube.com" in query) or ("youtu.be" in query)
        if is_sc:
            with yt_dlp.YoutubeDL(ydl_opts()) as ydl:
                info = ydl.extract_info(query, download=False)
            if not info:
                raise SourceError("bad sc url")
            item = pick_format(info, False)
            item["url"] = query
            item["source"] = "soundcloud"
            return item
        if is_yt:
            vid = None
            m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})", query)
            if m:
                vid = m.group(1)
            item = {
                "title": "يوتيوب",
                "url": f"https://www.youtube.com/watch?v={vid}" if vid else query,
                "dur": 0,
                "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else None,
            }
            try:
                # جرّب نجيب العنوان فوراً (بحث مسطح ما ينحجب)
                with yt_dlp.YoutubeDL(ydl_opts(flat=True)) as ydl:
                    info = ydl.extract_info(item["url"], download=False)
                if info and info.get("title"):
                    item["title"] = info["title"]
                    item["dur"] = int(info.get("duration") or 0)
            except Exception:
                pass
            return item
        # رابط مباشر لملف صوت/فيديو
        return {"title": query.split("/")[-1][:60], "url": query,
                "stream_url": query, "dur": 0, "source": "direct"}

    # بحث نصي: يوتيوب (مسطح)
    return flat_search(query)


def fmt_dur(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def now_caption(item: dict) -> str:
    vol = VOLUME.get(item.get("_chat_id", 0), 100)
    mode = "🎬 فيديو" if item.get("video") else "🎵 صوت"
    cap = (
        f"{mode} <b>• تبدا تشتغل الآن</b>\n\n"
        f"📀 <b>العنوان:</b> {item['title']}\n"
        f"⏱ <b>المدة:</b> {fmt_dur(item['dur']) if item.get('dur') else 'غير معروفة'}\n"
        f"👤 <b>طلبها:</b> {item.get('by') or '-'}\n"
        f"🔊 <b>الصوت:</b> {vol}"
    )
    if item.get("source") == "soundcloud":
        cap += "\n🎧 <b>المصدر:</b> ساوند كلاود (يوتيوب محجوب مؤقتاً)"
    if LOOP.get(item.get("_chat_id", 0)):
        cap += "\n🔁 <b>التكرار:</b> مفعل"
    return cap


def control_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⏸ اسكت", callback_data="ctl:pause"),
            InlineKeyboardButton("⏭ تخطي", callback_data="ctl:skip"),
        ],
        [
            InlineKeyboardButton("▶️ كمل", callback_data="ctl:resume"),
            InlineKeyboardButton("⏹ ايقاف", callback_data="ctl:stop"),
        ],
    ])


async def send_now(chat_id: int, item: dict):
    item["_chat_id"] = chat_id
    cap = now_caption(item)
    MSG_IDS.pop(chat_id, None)
    markup = control_markup()
    if not CONFIG.get("reply_photo", True):
        m = await bot.send_message(chat_id, cap, reply_markup=markup)
        MSG_IDS[chat_id] = m.id
        return
    thumb = CONFIG.get("thumb")
    if thumb:
        try:
            m = await bot.send_photo(chat_id, thumb, caption=cap, reply_markup=markup)
            MSG_IDS[chat_id] = m.id
            return
        except Exception:
            pass
    if item.get("thumb"):
        try:
            m = await bot.send_photo(chat_id, item["thumb"], caption=cap, reply_markup=markup)
            MSG_IDS[chat_id] = m.id
            return
        except Exception:
            pass
    m = await bot.send_message(chat_id, cap, reply_markup=markup)
    MSG_IDS[chat_id] = m.id


async def send_queued(chat_id: int, item: dict, pos: int):
    cap = (
        f"📝 <b>انضافت للقائمة</b> • الموقع {pos}\n\n"
        f"📀 <b>العنوان:</b> {item['title']}\n"
        f"⏱ <b>المدة:</b> {fmt_dur(item['dur']) if item.get('dur') else 'غير معروفة'}\n"
        f"👤 <b>طلبها:</b> {item.get('by') or '-'}"
    )
    await _send_plain_media(chat_id, cap, item)


async def _send_plain_media(chat_id: int, cap: str, item: dict):
    if not CONFIG.get("reply_photo", True):
        await bot.send_message(chat_id, cap)
        return
    thumb = CONFIG.get("thumb")
    if thumb:
        try:
            await bot.send_photo(chat_id, thumb, caption=cap)
            return
        except Exception:
            pass
    if item.get("thumb"):
        try:
            await bot.send_photo(chat_id, item["thumb"], caption=cap)
            return
        except Exception:
            pass
    await bot.send_message(chat_id, cap)


# ================== التشغيل ==================
def build_stream(item: dict) -> MediaStream:
    aq = AUDIO_QUALITY_MAP.get(CONFIG.get("audio_q"), AudioQuality.HIGH)
    url = item.get("stream_url") or item["url"]
    if item.get("video"):
        vq = VIDEO_QUALITY_MAP.get(CONFIG.get("video_q"), VideoQuality.HD_720p)
        return MediaStream(url, aq, vq)
    return MediaStream(url, aq)


async def play_item(chat_id: int, item: dict):
    # نجيب رابط التشغيل في وقت التشغيل (ما تنتهي صلاحيته وهو بالقائمة)
    if not item.get("stream_url"):
        item["stream_url"] = await asyncio.to_thread(resolve_stream, item)
    await call_py.play(chat_id, build_stream(item))
    PLAYING[chat_id] = item
    PAUSED[chat_id] = False


async def cleanup_chat(chat_id: int):
    QUEUE.pop(chat_id, None)
    PLAYING.pop(chat_id, None)
    PAUSED.pop(chat_id, None)
    LOOP.pop(chat_id, None)
    VOLUME.pop(chat_id, None)
    MSG_IDS.pop(chat_id, None)


async def prefetch_next(chat_id: int):
    """يجيب رابط الأغنية الجاية قبل ما تخلص الحالية، عشان تبدأ فوراً"""
    try:
        q = QUEUE.get(chat_id)
        if q and not q[0].get("stream_url"):
            await asyncio.to_thread(resolve_stream, q[0])
    except Exception:
        pass


async def play_next(chat_id: int):
    if LOOP.get(chat_id) and chat_id in PLAYING:
        item = PLAYING[chat_id]
        # نعيد جلب الرابط عشان ما تنتهي صلاحيته
        item.pop("stream_url", None)
        try:
            await play_item(chat_id, item)
            await bot.send_message(chat_id, f"🔁 <b>تكرار:</b> رجعت شغلت {item['title']}")
            return
        except Exception as e:
            log.error(f"loop error: {e}")

    q = QUEUE.get(chat_id)
    if q:
        item = q.pop(0)
        try:
            await play_item(chat_id, item)
            await send_now(chat_id, item)
            asyncio.create_task(prefetch_next(chat_id))
        except Exception as e:
            log.error(f"play error: {e}")
            await bot.send_message(chat_id, "⚠️ تعذر تشغيل هذا المقطع، جاري تجربة التالي...")
            await play_next(chat_id)
    else:
        await cleanup_chat(chat_id)
        try:
            await call_py.leave_call(chat_id)
        except Exception:
            pass
        await bot.send_message(chat_id, "✅ القائمة خلصت، طلعت من المكالمة 👋")


async def do_skip(chat_id: int) -> str:
    q = QUEUE.get(chat_id)
    if q:
        await play_next(chat_id)
        return "⏭️ تم التخطي، شغلت اللي بعدها"
    # ما فيه شي بعدها
    LOOP.pop(chat_id, None)
    await cleanup_chat(chat_id)
    try:
        await call_py.leave_call(chat_id)
    except Exception:
        pass
    return "⏭️ ما فيه أغنية بعدها، طلعت من المكالمة"


async def start_playing(m, item: dict, video: bool, edit=None):
    chat_id = m.chat.id
    if chat_id in PLAYING:
        QUEUE.setdefault(chat_id, []).append(item)
        pos = len(QUEUE[chat_id])
        if edit:
            await edit(f"📝 <b>انضافت للقائمة</b> • الموقع {pos}\n\n📀 {item['title']}")
        else:
            await send_queued(chat_id, item, pos)
        return
    try:
        await play_item(chat_id, item)
    except Exception as e:
        if video:
            log.error(f"video play error: {e}")
            try:
                item["video"] = False
                item.pop("stream_url", None)
                await play_item(chat_id, item)
                msg = (
                    "⚠️ ما فيه مكالمة فيديو مفتوحة، شغلتها صوت 🎵\n\n"
                    f"📀 <b>العنوان:</b> {item['title']}"
                )
                if edit:
                    await edit(msg)
                else:
                    await m.reply(msg)
                return
            except Exception:
                pass
        err = "❌ ما قدرت أدخل المكالمة.\nتأكد إن: المكالمة الصوتية مفتوحة + البوت أدمن بالمجموعة"
        if edit:
            await edit(err)
        else:
            await m.reply(err)
        return
    asyncio.create_task(prefetch_next(chat_id))
    if edit:
        await edit(
            f"{'🎬 فيديو' if item['video'] else '🎵 صوت'} <b>• تبدا تشتغل الآن</b>\n\n"
            f"📀 <b>العنوان:</b> {item['title']}\n"
            f"👤 <b>طلبها:</b> {item.get('by') or '-'}"
        )
    else:
        await send_now(chat_id, item)


async def handle_play(m, query: str, video: bool):
    try:
        item = await asyncio.to_thread(search_track, query)
    except SourceError:
        await m.reply("❌ ما لقيت الأغنية، جرّب اسم ثاني")
        return
    except Exception as e:
        log.error(f"search error: {e}")
        await m.reply("❌ صار خطأ بالبحث، جرّب مرة ثانية")
        return
    item["video"] = video
    item["by"] = (m.from_user.first_name if m.from_user else "") or ""
    status = await m.reply("🔎 جاري تجهيز الأغنية...")
    try:
        await start_playing(m, item, video)
    finally:
        try:
            await status.delete()
        except Exception:
            pass


async def handle_search_buttons(m, query: str):
    try:
        item = await asyncio.to_thread(search_track, query)
    except Exception:
        await m.reply("❌ ما لقيت شي بهالاسم، جرّب اسم ثاني")
        return
    key = uuid.uuid4().hex[:10]
    SEARCH_CACHE[key] = {"item": item, "chat_id": m.chat.id}
    dur = fmt_dur(item["dur"]) if item.get("dur") else ""
    markup = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"pl:{key}:v"),
            InlineKeyboardButton("🎵 صوت", callback_data=f"pl:{key}:a"),
        ]]
    )
    await m.reply(
        f"🔎 <b>{item['title']}</b> {f'({dur})' if dur else ''}\nاختار طريقة التشغيل:",
        reply_markup=markup,
    )


# ================== أزرار التحكم ==================
@bot.on_callback_query()
async def on_button(client, cq):
    data = cq.data or ""
    uid = cq.from_user.id if cq.from_user else 0
    chat_id = cq.message.chat.id if cq.message else 0

    if data.startswith("pl:"):
        _, key, mode = data.split(":")
        rec = SEARCH_CACHE.get(key)
        if not rec:
            await cq.answer("انتهت صلاحية البحث، ابحث من جديد", show_alert=True)
            return
        await cq.answer()
        item = rec["item"]
        item["video"] = mode == "v"
        item["by"] = (cq.from_user.first_name if cq.from_user else "") or ""
        target_chat = rec["chat_id"]
        SEARCH_CACHE.pop(key, None)

        async def edit(txt):
            try:
                await cq.edit_message_text(txt)
            except Exception:
                pass

        if target_chat in PLAYING:
            QUEUE.setdefault(target_chat, []).append(item)
            pos = len(QUEUE[target_chat])
            await edit(f"📝 <b>انضافت للقائمة</b> • الموقع {pos}\n\n📀 {item['title']}")
            return
        try:
            await play_item(target_chat, item)
        except Exception as e:
            if item["video"]:
                log.error(f"video play error: {e}")
                try:
                    item["video"] = False
                    item.pop("stream_url", None)
                    await play_item(target_chat, item)
                    await edit(
                        "⚠️ ما فيه مكالمة فيديو، شغلتها صوت 🎵\n\n"
                        f"📀 <b>العنوان:</b> {item['title']}"
                    )
                    return
                except Exception:
                    pass
            await edit("❌ ما قدرت أدخل المكالمة.\nتأكد إن المكالمة مفتوحة والبوت أدمن")
            return
        await edit(
            f"{'🎬 فيديو' if item['video'] else '🎵 صوت'} <b>• تبدا تشتغل الآن</b>\n\n"
            f"📀 <b>العنوان:</b> {item['title']}\n"
            f"👤 <b>طلبها:</b> {item.get('by') or '-'}"
        )
        asyncio.create_task(prefetch_next(chat_id))
        return

    if data.startswith("ctl:"):
        action = data[4:]
        if action == "pause":
            try:
                await call_py.pause(chat_id)
                PAUSED[chat_id] = True
                await cq.answer("⏸️ سكتّتها مؤقتاً")
            except Exception:
                await cq.answer("❌ ما فيه أغنية تشتغل", show_alert=True)
        elif action == "resume":
            try:
                await call_py.resume(chat_id)
                PAUSED[chat_id] = False
                await cq.answer("▶️ كملنا من وين توقفت")
            except Exception:
                await cq.answer("❌ ما فيه شي موقّف", show_alert=True)
        elif action == "skip":
            if chat_id not in PLAYING:
                await cq.answer("❌ ما فيه أغنية تشتغل", show_alert=True)
                return
            await cq.answer("⏭️ تخطيت")
            await do_skip(chat_id)
        elif action == "stop":
            await cq.answer("⏹️ تم الإيقاف")
            await cleanup_chat(chat_id)
            try:
                await call_py.leave_call(chat_id)
            except Exception:
                pass
            try:
                await cq.edit_message_text("⏹️ تم إيقاف كل الأغاني والخروج من المكالمة")
            except Exception:
                pass
        return

    if data.startswith("st:"):
        if uid != DEV_ID:
            await cq.answer("الإعدادات للمطور فقط 🔒", show_alert=True)
            return
        await cq.answer()
        action = data[3:]
        if action == "photo":
            CONFIG["reply_photo"] = not CONFIG.get("reply_photo", True)
        elif action == "delthumb":
            CONFIG["thumb"] = None
        elif action == "audio":
            order = ["high", "medium", "low"]
            i = order.index(CONFIG.get("audio_q", "high"))
            CONFIG["audio_q"] = order[(i + 1) % 3]
        elif action == "video":
            order = ["720", "480", "360"]
            i = order.index(CONFIG.get("video_q", "720"))
            CONFIG["video_q"] = order[(i + 1) % 3]
        save_config()
        await cq.edit_message_text(settings_text(), reply_markup=settings_markup())


# ================== إعدادات المطور ==================
def settings_text() -> str:
    photo_state = "مفعل ✅" if CONFIG.get("reply_photo", True) else "معطل ❌"
    return (
        "⚙️ <b>إعدادات البوت</b> (خاصة بالمطور)\n\n"
        f"🖼 <b>صورة التشغيل:</b> {'موجودة ✅' if CONFIG.get('thumb') else 'افتراضية (صورة الأغنية)'}\n"
        f"🖼 <b>الرد بصورة:</b> {photo_state}\n"
        f"🎧 <b>جودة الصوت:</b> {AUDIO_Q_LABEL.get(CONFIG.get('audio_q'), 'عالية')}\n"
        f"🎬 <b>جودة الفيديو:</b> {CONFIG.get('video_q', '720')}p\n\n"
        "💡 <b>لتغيير صورة التشغيل:</b> أرسل أي صورة هنا مباشرة"
    )


def settings_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🖼 الرد بصورة", callback_data="st:photo"),
            InlineKeyboardButton("🗑 حذف الصورة", callback_data="st:delthumb"),
        ],
        [
            InlineKeyboardButton("🎧 جودة الصوت", callback_data="st:audio"),
            InlineKeyboardButton("🎬 جودة الفيديو", callback_data="st:video"),
        ],
    ])


@bot.on_message(filters.private)
async def private_handler(client, m):
    uid = m.from_user.id if m.from_user else 0

    if uid != DEV_ID:
        await m.reply(f"👋 هذا <b>{BOT_NAME}</b> للمجموعات.\nأضفني لمجموعتك وارفعني أدمن 🎵")
        return

    if m.photo:
        CONFIG["thumb"] = m.photo.file_id
        save_config()
        await m.reply("✅ تم حفظ صورة التشغيل، راح تطلع مع كل أغنية 🖼")
        await m.reply(settings_text(), reply_markup=settings_markup())
        return

    text = (m.text or "").strip()
    if text in ("/start", "الاعدادات", "settings", "/settings"):
        await m.reply(settings_text(), reply_markup=settings_markup())
    elif text in ("/delthumb", "حذف الصورة"):
        CONFIG["thumb"] = None
        save_config()
        await m.reply("🗑 تم حذف صورة التشغيل ورجعت لصورة الأغنية الافتراضية")
    elif text in ("/help", "الاوامر"):
        await m.reply(HELP_TEXT)
    else:
        await m.reply("أرسل صورة لتكون صورة التشغيل 🖼 أو اكتب <code>الاعدادات</code> ⚙️")


# كلمات الأوامر (كلها اختصارات لبعضها، وتشمل كلمات النسخة القديمة)
VIDEO_WORDS = ["فيد", "فيديو", "شغل فيديو", "تشغيل فيديو", "v "]
AUDIO_WORDS = ["شغل", "تشغيل", "صوت", "اسمع", "play", "p "]
SEARCH_WORDS = ["يوت", "بحث", "yt", "search"]

# ================== أوامر الجروب ==================
def match_cmd(text: str, words):
    for w in words:
        if text.startswith(w):
            return text[len(w):].strip()
    return None


@bot.on_message(filters.group & filters.text)
async def group_commands(client, m):
    text = (m.text or "").strip()

    if text in ("الاوامر", "/start", "اوامر"):
        await m.reply(HELP_TEXT)
        return

    # روابط مباشرة
    if text.startswith("http://") or text.startswith("https://"):
        q = text.split()[0]
        await handle_play(m, q, video=False)
        return

    # فيديو
    q = match_cmd(text, VIDEO_WORDS)
    if q is not None:
        if not q:
            await m.reply("اكتب اسم الأغنية بعد الأمر ✍️ مثال: فيد انا مشيت")
            return
        await handle_play(m, q, video=True)
        return

    # صوت
    q = match_cmd(text, AUDIO_WORDS)
    if q is not None:
        if not q:
            await m.reply("اكتب اسم الأغنية بعد الأمر ✍️ مثال: شغل انا مشيت")
            return
        await handle_play(m, q, video=False)
        return

    # بحث بأزرار
    q = match_cmd(text, SEARCH_WORDS)
    if q is not None:
        if not q:
            await m.reply("اكتب اسم الأغنية بعد الأمر ✍️ مثال: يوت انا مشيت")
            return
        await handle_search_buttons(m, q)
        return

    # تخطي
    if text.startswith("تخطي"):
        if m.chat.id not in PLAYING:
            await m.reply("❌ ما فيه أغنية تشتغل")
            return
        await m.reply(await do_skip(m.chat.id))
        return

    # ايقاف
    if text.startswith("ايقاف"):
        chat_id = m.chat.id
        await cleanup_chat(chat_id)
        try:
            await call_py.leave_call(chat_id)
        except Exception:
            pass
        await m.reply("⏹️ تم إيقاف كل الأغاني والخروج من المكالمة")
        return

    # اسكت
    if text.startswith("اسكت"):
        try:
            await call_py.pause(m.chat.id)
            PAUSED[m.chat.id] = True
            await m.reply("⏸️ سكتّها مؤقتاً، اكتب كمل عشان ترجع")
        except Exception:
            await m.reply("❌ ما فيه أغنية تشتغل")
        return

    # كمل
    if text.startswith("كمل"):
        try:
            await call_py.resume(m.chat.id)
            PAUSED[m.chat.id] = False
            await m.reply("▶️ كملنا من وين توقفت")
        except Exception:
            await m.reply("❌ ما فيه شي موقّف")
        return

    # تكرار
    if text.startswith("تكرار"):
        chat_id = m.chat.id
        if chat_id not in PLAYING:
            await m.reply("❌ ما فيه أغنية تشتغل عشان أكررها")
            return
        LOOP[chat_id] = not LOOP.get(chat_id, False)
        if LOOP[chat_id]:
            await m.reply("🔁 فعلت التكرار: الأغنية بتضل تعيد")
        else:
            await m.reply("➡️ أوقفت التكرار")
        return

    # الصوت (مستوى الصوت)
    if text.startswith("الصوت"):
        rest = text[len("الصوت"):].strip()
        try:
            vol = int(rest)
            assert 1 <= vol <= 200
        except Exception:
            await m.reply("اكتب رقم من 1 إلى 200 ✍️ مثال: الصوت 200")
            return
        try:
            await call_py.change_volume_call(m.chat.id, vol)
            VOLUME[m.chat.id] = vol
            await m.reply(f"🔊 غيرت الصوت إلى {vol}%")
        except Exception:
            await m.reply("❌ ما فيه أغنية تشتغل")
        return

    # قائمة الانتظار
    if text.startswith("قائمة") or text.startswith("الطابور"):
        chat_id = m.chat.id
        cur = PLAYING.get(chat_id)
        q = QUEUE.get(chat_id, [])
        if not cur and not q:
            await m.reply("📝 القائمة فاضية")
            return
        lines = [f"▶️ <b>تشتغل الآن:</b> {cur['title']}" if cur else ""]
        for i, it in enumerate(q[:10], 1):
            lines.append(f"{i}️⃣ {it['title']} • طلبها: {it.get('by') or '-'}")
        if len(q) > 10:
            lines.append(f"... وباقي {len(q) - 10} أغنية")
        await m.reply("📝 <b>قائمة الانتظار:</b>\n\n" + "\n".join(l for l in lines if l))
        return

    # الوقت (وين وصلت الأغنية)
    if text.startswith("الوقت"):
        try:
            t = await call_py.time(m.chat.id)
            secs = int(t)
            cur = PLAYING.get(m.chat.id, {})
            total = cur.get("dur", 0)
            done = fmt_dur(secs)
            whole = fmt_dur(total) if total else "?"
            await m.reply(f"⏱ <b>تقدم الأغنية:</b> {done} / {whole}")
        except Exception:
            await m.reply("❌ ما فيه أغنية تشتغل")
        return


# ================== نهاية الأغنية ==================
@call_py.on_update(fl.stream_end())
async def on_stream_end(_: PyTgCalls, update: StreamEnded):
    log.info(f"stream ended in {update.chat_id}")
    PLAYING.pop(update.chat_id, None)
    await play_next(update.chat_id)


log.info(f"يشتغل {BOT_NAME}...")
call_py.run()
