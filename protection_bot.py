import json
import logging
import os
import uuid
import yt_dlp
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
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

if not (API_ID and API_HASH and BOT_TOKEN):
    raise SystemExit("ناقص متغيرات البيئة: API_ID, API_HASH, BOT_TOKEN")

bot = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workers=8)
call_py = PyTgCalls(bot)

QUEUE = {}        # chat_id -> [item, ...]
PLAYING = {}      # chat_id -> item الشغال حاليا
SEARCH_CACHE = {} # مفتاح البحث -> بيانات الأغنية

AUDIO_WORDS = ("تشغيل", "شغل")
VIDEO_WORDS = ("فيديو", "فيد")
SEARCH_WORDS = ("يوت", "بحث")

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "thumb": None,        # file_id لصورة التشغيل
    "reply_photo": True,   # الرد بصورة أو نص فقط
    "audio_q": "high",    # high / medium / low
    "video_q": "720",     # 720 / 480 / 360
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

YTDLP_OPTS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "nocheckcertificate": True,
    "geo_bypass": True,
}

HELP_TEXT = (
    "🎵 <b>بوت موسيقى ARIA</b>\n\n"
    "• <code>شغل</code> + اسم الأغنية ← تشغيل صوت 🎵\n"
    "• <code>فيد</code> + اسم الأغنية ← تشغيل فيديو 🎬\n"
    "• <code>يوت</code> + اسم الأغنية ← اختيار فيديو أو صوت بأزرار\n"
    "• <code>تخطي</code> ← الأغنية التالية ⏭\n"
    "• <code>اسكت</code> ← إيقاف مؤقت ⏸\n"
    "• <code>كمل</code> ← يكمل من وين توقف ▶️\n"
    "• <code>ايقاف</code> ← إيقاف كل الأغاني والخروج ⏹\n\n"
    "⚠️ لازم تكون المكالمة الصوتية مفتوحة والبوت أدمن"
)


# ================== بحث يوتيوب ==================
def search_track(query: str) -> dict:
    q = query if query.startswith("http") else f"ytsearch1:{query}"
    with yt_dlp.YoutubeDL(YTDLP_OPTS) as ydl:
        info = ydl.extract_info(q, download=False)
    if info and "entries" in info:
        entries = [e for e in info["entries"] if e]
        if not entries:
            raise ValueError("no results")
        info = entries[0]
    url = info.get("webpage_url") or info.get("original_url") or info.get("url")
    if not url:
        raise ValueError("no url")
    return {
        "title": info.get("title") or "غير معروف",
        "url": url,
        "dur": int(info.get("duration") or 0),
        "thumb": info.get("thumbnail"),
    }


def fmt_dur(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


# ================== ردود أنيقة (مثل البوتات المشهورة) ==================
async def send_now(chat_id: int, item: dict, video: bool):
    cap = (
        f"{'🎬 فيديو' if video else '🎵 صوت'} <b>• تبدا تشتغل الآن</b>\n\n"
        f"📀 <b>العنوان:</b> {item['title']}\n"
        f"⏱ <b>المدة:</b> {fmt_dur(item['dur']) if item['dur'] else 'غير معروفة'}\n"
        f"👤 <b>طلبها:</b> {item.get('by') or '-'}\n"
        f"🎧 <b>جودة الصوت:</b> {AUDIO_Q_LABEL.get(CONFIG['audio_q'], 'عالية')}"
    )
    await _send_media(chat_id, cap, item)


async def send_queued(chat_id: int, item: dict, pos: int):
    cap = (
        f"📝 <b>انضافت للقائمة</b> • الموقع {pos}\n\n"
        f"📀 <b>العنوان:</b> {item['title']}\n"
        f"⏱ <b>المدة:</b> {fmt_dur(item['dur']) if item['dur'] else 'غير معروفة'}\n"
        f"👤 <b>طلبها:</b> {item.get('by') or '-'}"
    )
    await _send_media(chat_id, cap, item)


async def _send_media(chat_id: int, cap: str, item: dict):
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
    if item.get("video"):
        vq = VIDEO_QUALITY_MAP.get(CONFIG.get("video_q"), VideoQuality.HD_720p)
        return MediaStream(item["url"], aq, vq)
    return MediaStream(item["url"], aq)


async def play_item(chat_id: int, item: dict):
    await call_py.play(chat_id, build_stream(item))
    PLAYING[chat_id] = item


async def play_next(chat_id: int):
    q = QUEUE.get(chat_id)
    if q:
        item = q.pop(0)
        try:
            await play_item(chat_id, item)
            await send_now(chat_id, item, item.get("video", False))
        except Exception as e:
            log.error(f"play error: {e}")
            await bot.send_message(chat_id, "⚠️ تعذر تشغيل هذا المقطع، جاري تجربة التالي...")
            await play_next(chat_id)
    else:
        PLAYING.pop(chat_id, None)
        try:
            await call_py.leave_call(chat_id)
        except Exception:
            pass
        await bot.send_message(chat_id, "✅ القائمة خلصت، طلعت من المكالمة 👋")


async def start_playing(m: Message, item: dict, video: bool, edit=None):
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
                await play_item(chat_id, item)
                msg = (
                    "⚠️ ما قدرت أبث فيديو (لازم مكالمة فيديو مفتوحة بالمجموعة)، شغلتها صوت 🎵\n\n"
                    f"📀 <b>العنوان:</b> {item['title']}"
                )
                if edit:
                    await edit(msg)
                else:
                    await m.reply(msg)
                return
            except Exception:
                pass
        err = (
            "❌ ما قدرت أدخل المكالمة.\n"
            "تأكد إن: المكالمة الصوتية مفتوحة + البوت أدمن بالمجموعة"
        )
        if edit:
            await edit(err)
        else:
            await m.reply(err)
        return
    if edit:
        await edit(
            f"{'🎬 فيديو' if item['video'] else '🎵 صوت'} <b>• تبدا تشتغل الآن</b>\n\n"
            f"📀 <b>العنوان:</b> {item['title']}\n"
            f"👤 <b>طلبها:</b> {item.get('by') or '-'}"
        )
    else:
        await send_now(chat_id, item, item["video"])


async def handle_play(m: Message, query: str, video: bool):
    try:
        item = search_track(query)
    except Exception as e:
        log.error(f"search error: {e}")
        await m.reply("❌ ما لقيت الأغنية، جرّب اسم ثاني")
        return
    item["video"] = video
    item["by"] = (m.from_user.first_name if m.from_user else "") or ""
    await start_playing(m, item, video)


async def handle_search_buttons(m: Message, query: str):
    try:
        item = search_track(query)
    except Exception:
        await m.reply("❌ ما لقيت شي بهالاسم، جرّب اسم ثاني")
        return
    key = uuid.uuid4().hex[:10]
    SEARCH_CACHE[key] = {"item": item, "chat_id": m.chat.id}
    dur = fmt_dur(item["dur"]) if item["dur"] else ""
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


# ================== أزرار اختيار فيديو/صوت ==================
@bot.on_callback_query()
async def on_button(client: Client, cq):
    data = cq.data or ""
    if data.startswith("pl:"):
        _, key, mode = data.split(":")
        rec = SEARCH_CACHE.get(key)
        if not rec:
            await cq.answer("انتهت صلاحية البحث، ابحث من جديد", show_alert=True)
            return
        await cq.answer()
        chat_id = rec["chat_id"]
        item = rec["item"]
        item["video"] = mode == "v"
        item["by"] = (cq.from_user.first_name if cq.from_user else "") or ""
        SEARCH_CACHE.pop(key, None)

        async def edit(txt):
            try:
                await cq.edit_message_text(txt)
            except Exception:
                pass

        if chat_id in PLAYING:
            QUEUE.setdefault(chat_id, []).append(item)
            pos = len(QUEUE[chat_id])
            await edit(f"📝 <b>انضافت للقائمة</b> • الموقع {pos}\n\n📀 {item['title']}")
            return
        try:
            await play_item(chat_id, item)
        except Exception as e:
            if item["video"]:
                log.error(f"video play error: {e}")
                try:
                    item["video"] = False
                    await play_item(chat_id, item)
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
    elif data.startswith("st:"):
        if cq.from_user.id != DEV_ID:
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
            InlineKeyboardButton(f"🎧 جودة الصوت", callback_data="st:audio"),
            InlineKeyboardButton(f"🎬 جودة الفيديو", callback_data="st:video"),
        ],
    ])


# ================== خاص المطور ==================
@bot.on_message(filters.private)
async def private_handler(client: Client, m: Message):
    uid = m.from_user.id if m.from_user else 0

    if uid != DEV_ID:
        await m.reply("👋 هذا بوت موسيقى للمجموعات.\nأضفني لمجموعتك وارفعني أدمن 🎵")
        return

    # صورة جديدة لصورة التشغيل
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


# ================== أوامر الجروب ==================
def match_cmd(text: str, words) -> str | None:
    for w in words:
        if text.startswith(w):
            return text[len(w):].strip()
    return None


@bot.on_message(filters.group & filters.text)
async def group_commands(client: Client, m: Message):
    text = (m.text or "").strip()

    if text in ("الاوامر", "/start", "اوامر"):
        await m.reply(HELP_TEXT)
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
        chat_id = m.chat.id
        if QUEUE.get(chat_id):
            await m.reply("⏭️ تخطيت، نشغل اللي بعده...")
            await play_next(chat_id)
        else:
            PLAYING.pop(chat_id, None)
            try:
                await call_py.leave_call(chat_id)
            except Exception:
                pass
            await m.reply("⏭️ ما فيه أغنية بعدها، طلعت من المكالمة")
        return

    # ايقاف
    if text.startswith("ايقاف"):
        chat_id = m.chat.id
        QUEUE.pop(chat_id, None)
        PLAYING.pop(chat_id, None)
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
            await m.reply("⏸️ سكتّها مؤقتاً، اكتب كمل عشان ترجع")
        except Exception:
            await m.reply("❌ ما فيه أغنية تشتغل")
        return

    # كمل
    if text.startswith("كمل"):
        try:
            await call_py.resume(m.chat.id)
            await m.reply("▶️ كملنا من وين توقفت")
        except Exception:
            await m.reply("❌ ما فيه شي موقّف")


# ================== نهاية الأغنية -> التالية ==================
@call_py.on_update(fl.stream_end())
async def on_stream_end(_: PyTgCalls, update: StreamEnded):
    log.info(f"stream ended in {update.chat_id}")
    PLAYING.pop(update.chat_id, None)
    await play_next(update.chat_id)


log.info("يشتغل بوت الموسيقى...")
call_py.run()
