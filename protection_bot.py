import os
import asyncio
import json
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioVideoPiped, AudioPiped
import yt_dlp

# ==================== [ إعدادات البيانات ] ====================

# الأيدي الحسابي الخاص بك (سوكار) لحماية لوحة التحكم لك وحدك
DEVELOPER_ID = 6913101408  

# بيانات الحساب المساعد (Userbot) الخاص بك
ASSISTANT_API_ID = 37284623
ASSISTANT_API_HASH = '4e5dd535ba915df2bcdd968d167cd3cb'

# كود الجلسة (String Session) النصي الطويل الذي أرسلته (تم الدمج بنجاح)
ASSISTANT_SESSION = '1BJWap1wBuxxZOH7XqLOV4x2l_ulSey8IZ6TkYsUixYI-MydO68HvcpBwMKhcOqYqFMOKuvM7pY1eEu3i_jRrwWzXv__CPb1-LKHZnw5AM4WuadsTmRTHWFBVMPdXIe6EJZK7MEBBbRxEBuQBsTDASfH7hNFlXsdKV7NLjJPtgcDi7fJs8_dmUpUigt_1qh-AnqpT3uhKKOyhheUshBNs3MeaRM7sviGpK0q_a3zJygPgOM-sOugUVnEsgXx6RAvi0UpuQdJATdWkI1KGPUvOKut3VanOL4kJ2rFLOkSlzgWMEFarA5OXlOVYktgpUjiyoHOAUIXFg1MMapDSXFWVy01hAmjzu2U='

# ⚠️ ضع هنا توكن البوت الرسمي الخاص بك المستخرج من @BotFather
BOT_TOKEN = '8750112907:AAHUhh9WI1E_BMW6TczwFL1jJRzLsYAIqPQ'

# ==============================================================

bot = TelegramClient('aria_bot_session', ASSISTANT_API_ID, ASSISTANT_API_HASH).start(bot_token=BOT_TOKEN)
assistant = TelegramClient(StringSession(ASSISTANT_SESSION), ASSISTANT_API_ID, ASSISTANT_API_HASH)
call_py = PyTgCalls(assistant)

CHANNEL_USER = "@ARIA1D"
↢ تحميل من اليوتيوب والساوند والتيك.\n"
            "↢ تشغيل المقاطع بالمكالمات : اكتب الDB_FILE = "bot_settings.json"

DB_FILE = "t_settings.json"

def load_settings():
    import os
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "text": (
            "↢ اهلا انا بوت اسمي اريا\n\n"
            "↞ موهبتي :\n"
            "↢ اعلى بوت في مستوى الحمايه للقروبات\n"
            "↢ مافيه مطورين في البوت غير المطور الاساسي سوكار\n"
            "↢ يسموني وحش الحمايه 🦦\n\n"
            "↞ وظيفتي :\n"
            "↢ حماية القروب وخدمتك وتسليتك انت واعضائك.\n"
            "↢ تحميل من اليوتيوب والساوند والتيك.\n"
            "↢ تشغيل المقاطع بالمكالمات : اكتب المكالمه.\n"
            "↢ كت تويت اسئله جديده ماهي ممله وتتجدد.\n"
            "↢ قفل الاوامر وتحطها للرتب اللي ودك.\n\n"
            "انت ارفعني بس مشرفه واعطيني صلاحيات اتفعل تلقائي ، واترك الباقي علي دنا هبسطك ♡"
        ),
        "image": "https://telegra.ph",
        "users": []
    }

    }

def save_settings(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

settings = load_settings()
USER_STATES = {}

DEV_KEYBOARD = [
    [Button.inline("📝 تعديل نص الترحيب", data="dev_edit_text")],
    [Button.inline("🖼️ تغيير صورة الترحيب", data="dev_edit_img")],
    [Button.inline("📢 إرسال إذاعة للمستخدمين", data="dev_broadcast")],
    [Button.inline("❌ إغلاق اللوحة", data="dev_close")]
]

MAIN_KEYBOARD = [
    [Button.inline("1", data="btn_1"), Button.inline("2", data="btn_2")],
    [Button.inline("3", data="btn_3"), Button.inline("4", data="btn_4")],
    [Button.inline("5", data="btn_5"), Button.inline("6", data="btn_6")],
    [Button.url("تحديثات اريا 🦦", f"https://t.me{CHANNEL_USER.strip('@')}")]
]
BACK_BUTTON = [[Button.inline("🔙 العودة للقائمة الرئيسية", data="back_main")]]

def get_stream_url(query, video=False):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' if video else 'bestaudio[ext=m4a]/best',
        'default_search': 'ytsearch', 'quiet': True, 'noplaylist': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch:{query}", download=False)
        if 'entries' in info and len(info['entries']) > 0:
            return info['entries'][0]['url'], info['entries'][0]['title']
    return None, None

@bot.on(events.NewMessage(pattern='(?i)^/start|^الاوامر'))
async def send_welcome(event):
    global settings
    user_id = event.sender_id
    if user_id not in settings["users"]:
        settings["users"].append(user_id)
        save_settings(settings)
        
    if event.is_private and user_id == DEVELOPER_ID:
        await bot.send_file(
            event.chat_id, settings["image"],
            caption=f"👑 أهلاً بك يا مطوري سوكار في لوحة التحكم الخاصة بك:\n\n{settings['text']}",
            buttons=DEV_KEYBOARD
        )
    else:
        await bot.send_file(event.chat_id, settings["image"], caption=settings["text"], buttons=MAIN_KEYBOARD)

@bot.on(events.NewMessage(pattern=r'^تشغيل (.+)'))
async def play_audio_cmd(event):
    query = event.pattern_match.group(1)
    status_msg = await event.reply(f"🔍 [المساعد] جاري البحث عن `{query}` وبثها صوتياً...")
    try:
        loop = asyncio.get_event_loop()
        stream_url, title = await loop.run_in_executor(None, lambda: get_stream_url(query, video=False))
        if not stream_url: return await status_msg.edit("❌ لم أجد نتائج.")
        await call_py.join_group_call(event.chat_id, AudioPiped(stream_url))
        await status_msg.edit(f"🎵 بدأ تشغيل الصوت:\n**[{title}]**")
    except Exception as e:
        await status_msg.edit("❌ حدث خطأ، تأكد من تشغيل المكالمة وتثبيت FFmpeg.")

@bot.on(events.NewMessage(pattern=r'^فيديو (.+)'))
async def play_video_cmd(event):
    query = event.pattern_match.group(1)
    status_msg = await event.reply(f"🎬 [المساعد] جاري البحث عن `{query}` وبثها فيديو...")
    try:
        loop = asyncio.get_event_loop()
        stream_url, title = await loop.run_in_executor(None, lambda: get_stream_url(query, video=True))
        if not stream_url: return await status_msg.edit("❌ لم أجد نتائج.")
        await call_py.join_group_call(event.chat_id, AudioVideoPiped(stream_url))
        await status_msg.edit(f"📺 بدأ بث الفيديو بنجاح:\n**[{title}]**")
    except Exception as e:
        await status_msg.edit("❌ حدث خطأ، تأكد من فتح المكالمة المرئية.")

@bot.on(events.NewMessage(pattern=r'^(ايقاف|إنهاء|انهاء)'))
async def stop_call_cmd(event):
    try:
        await call_py.leave_group_call(event.chat_id)
        await event.reply("⏹️ غادر الحساب المساعد المكالمة وتم إيقاف البث.")
    except Exception: pass

@bot.on(events.NewMessage(func=lambda e: e.is_private and e.sender_id == DEVELOPER_ID))
async def developer_inputs(event):
    global settings
    user_id = event.sender_id
    state = USER_STATES.get(user_id)
    if not state: return

    if state == "waiting_for_text":
        settings["text"] = event.text
        save_settings(settings)
        USER_STATES.pop(user_id, None)
        await event.reply("✅ تم تحديث نص الترحيب بنجاح!")
    elif state == "waiting_for_img":
        if event.photo:
            path = await event.download_media(file="welcome_bg.jpg")
            settings["image"] = path
            save_settings(settings)
            USER_STATES.pop(user_id, None)
            await event.reply("✅ تم تحديث صورة الترحيب بنجاح!")
        else:
            await event.reply("❌ يرجى إرسال صورة صالحة.")
    elif state == "waiting_for_broadcast":
        USER_STATES.pop(user_id, None)
        await event.reply("📢 جاري بدء الإذاعة...")
        count = 0
        for u_id in settings["users"]:
            try:
                await bot.send_message(u_id, event.message)
                count += 1
                await asyncio.sleep(0.2)
            except Exception: pass
        await event.reply(f"🎯 تم إرسال الإذاعة إلى {count} مستخدم.")

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    global settings
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data.startswith("dev_") and user_id == DEVELOPER_ID:
        if data == "dev_edit_text":
            USER_STATES[user_id] = "waiting_for_text"
            await event.respond("💬 أرسل الآن نص الترحيب الجديد كاملاً:")
        elif data == "dev_edit_img":
            USER_STATES[user_id] = "waiting_for_img"
            await event.respond("🖼️ قم بإرسال الصورة الجديدة الآن:")
        elif data == "dev_broadcast":
            USER_STATES[user_id] = "waiting_for_broadcast"
            await event.respond("📢 أرسل الرسالة التي تريد إذاعتها للكل:")
        elif data == "dev_close":
            await event.edit("🔒 تم إغلاق لوحة تحكم المطور.", buttons=MAIN_KEYBOARD)
        return

    if data == "back_main":
        await event.edit(settings["text"], buttons=MAIN_KEYBOARD)
    elif data == "btn_1":
        text_1 = (
            "↢ أهلاً فيك يا حلو ♡\n• قائمة اوامر Admin\n\n"
            "- اوامر الرفع والتنزيل :\n"
            "↢ رفع - تنزيل مالك اساسي | مالك | مشرف | منشئ | مدير | ادمن | مميز\n"
            "↢ تنزيل الكل - لازاله جميع الرتب اعلاه\n\n"
            "- اوامر المسح :\n"
            "↢ مسح الكل | المنشئين | المدراء | المالكين | الادمنيه | المميزين | المحظورين | المكتومين\n"
            "↢ مسح قائمة المنع | الردود | الاوامر المضافه | مسح + عدد | مسح بالرد | مسح الايدي\n\n"
            "- اوامر الطرد والحظر :\n"
            "↢ تقييد + الوقت | حظر | طرد | كتم | تقييد | الغاء الحظر | الغاء الكتم\n"
            f"قناة التحديثات : {CHANNEL_USER} 🦦"
        )
            await event.edit(text_1, buttons=BACK_BUTTON)
    
    elif data == "btn_2":
        text_2 = (
            "- قائمة الاعدادات :\n"
            "• اكتب في قروبك كذا ↓\n"
            "↢ الرابط | المالكين | المالكين الاساسين | المنشئين | الادمنيه | المدراء | المميزين | المحظورين | القوانين | معلوماتي | الحمايه | الاعدادت\n\n"
            "- اوامر وضع الاعدادات :\n"
            "↢ مسح الرابط | انشاء رابط | ضع الترحيب | ضع قوانين | ضـع رابط | اضف امر | تعيين الايدي\n"
            f"قناة تحديثات اريا : {CHANNEL_USER} 🦦"
        )
        await event.edit(text_2, buttons=BACK_BUTTON)

    elif data == "btn_3":
        text_3 = (
            "- قائمة القفل - التعطيل :\n\n"
            "اولا : اوامر القفل والفتح :\n"
            "↢ قفل - فتح ( جمثون | السب | الايرانيه | الكتابه | التعديل | الفيديو | الصور | الملصقات | المتحركه | الروابط | التاك | البوتات | المعرفات | التكرار | التوجيه )\n\n"
            "ثانيا : اوامر التفعيل - التعطيل :\n"
            "↢ تفعيل - تعطيل ( ضافني | الاذكار | الثنائي | افتاري | التسليه | الكت | الترحيب | الردود | الانذار | الايدي | الرابط | الحمايه )"
        )
        await event.edit(text_3, buttons=BACK_BUTTON)
    
    elif data == "btn_4":
        text_4 = (
            "• اهلا بك عزيزي - اوامر التسلية :\n"
            "━━━━━━━━━━━━\n"
            "• رفع - تنزيل : ( هطف | بثر | حمار | كلب | عتوي | لحجي | خروف | خفيف )\n"
            "• رفع بقلبي : تنزيل من قلبي\n"
            "• طلاق - زواج | زوجي - زوجتي | تتزوجني\n"
            "• اكتموه (تصويت)"
        )
        await event.edit(text_4, buttons=BACK_BUTTON)
    
    elif data == "btn_5":
        text_5 = (
            "• اهلا بك عزيزي - اوامر الخدميه :\n"
            "━━━━━━━━━━━━\n"
            "• نسبه الحب | نسبه الغباء | تحبه - بالرد\n"
            "• ارسل + الكلام + اليوزر زاجل\n"
            "• قوقل + كلام البحث | تطبيق + الاسم\n"
            "• قران | اذكار | شعر ، قصائد | اقتباسات | thred\n"
            "• اطربني | اغاني | ميمز | ايدت\n"
            "• افتارات (بنات ، عيال ، تطقيم ، انمي)\n"
            "━━━━━━━━━━━━\n"
            "التحميل :\n"
            "• ساوند + الرابط | تيك + الرابط | تويتر + الرابط"
        )
        await event.edit(text_5, buttons=BACK_BUTTON)
    
    elif data == "btn_6":
        await event.answer("هذا القسم فارغ حالياً.. ⚙️", alert=True)

async def start_all():
    await bot.start()
    await assistant.start()
    await call_py.start()
    print("🤖 البوت يعمل بنجاح...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_all())
    
