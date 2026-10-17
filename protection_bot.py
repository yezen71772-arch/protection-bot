import asyncio
import json
import os
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
# from pytgcalls import PyTgCalls
# from pytgcalls.types import AudioVideoPiped, AudioPiped


# ==================== [ إعدادات البيانات ] ====================

# الأيدي الحسابي الخاص بك (سوكار) لحماية لوحة التحكم لك وحدك
DEVELOPER_ID = 6913101408  

# بيانات الحساب المساعد (Userbot) الخاص بك
ASSISTANT_API_ID = 37284623
ASSISTANT_API_HASH = '4e5dd535ba915df2bcdd968d167cd3cb'

# كود الجلسة (String Session) النصي الطويل
ASSISTANT_SESSION = '1BJWap1wBuxxZOH7XqLOV4x2l_ulSey8IZ6TkYsUixYI-MydO68HvcpBwMKhcOqYqFMOKuvM7pY1eEu3i_jRrwWzXv__CPb1-LKHZnw5AM4WuadsTmRTHWFBVMPdXIe6EJZK7MEBBbRxEBuQBsTDASfH7hNFlXsdKV7NLjJPtgcDi7fJs8_dmUpUigt_1qh-AnqpT3uhKKOyhheUshBNs3MeaRM7sviGpK0q_a3zJygPgOM-sOugUVnEsgXx6RAvi0UpuQdJATdWkI1KGPUvOKut3VanOL4kJ2rFLOkSlzgWMEFarA5OXlOVYktgpUjiyoHOAUIXFg1MMapDSXFWVy01hAmjzu2U='

# توكن البوت الرسمي الخاص بك المستخرج من @BotFather
BOT_TOKEN = '8750112907:AAHUhh9WI1E_BMW6TczwFL1jJRzLsYAIqPQ'

CHANNEL_USER = "@ARIA1D"
DB_FILE = "t_settings.json"

# ==============================================================

bot = TelegramClient('aria_bot_session', ASSISTANT_API_ID, ASSISTANT_API_HASH).start(bot_token=BOT_TOKEN)
assistant = TelegramClient(StringSession(ASSISTANT_SESSION), ASSISTANT_API_ID, ASSISTANT_API_HASH)
#call_py = PyTgCalls(assistant)

def load_settings():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "text": (
            "اهلا انا بوت اسمي اريا\n\n"
            "موهبتي :\n"
            "اعلى بوت في مستوى الحمايه للقروبات\n"
            "مافيه مطورين في البوت غير المطور الاساسي سوكار\n"
            "يسموني وحش الحمايه\n\n"
            "وظيفتي :\n"
            "حماية القروب وخدمتك وتسليتك انت واعضائك.\n"
            "تحميل من اليوتيوب والساوند والتيك."
        ),
        "image": "https://telegra.ph",
        "users": []
    }

settings = load_settings()

MAIN_KEYBOARD = [
    [Button.inline("اوامر التفعيل", data="btn_1"), Button.inline("الاعدادات", data="btn_2")],
    [Button.inline("الحماية والقفل", data="btn_3"), Button.inline("التسلية", data="btn_4")],
    [Button.inline("الخدمية والتحميل", data="btn_5"), Button.inline("قسم فارغ", data="btn_6")]
]

BACK_BUTTON = [Button.inline("رجوع للخلف ↩️", data="back_main")]

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    if event.sender_id == DEVELOPER_ID or event.is_group:
        await event.respond(settings["text"], buttons=MAIN_KEYBOARD)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    global settings
    data = event.data.decode('utf-8')
    user_id = event.sender_id
    
    if data == "back_main":
        await event.edit(settings["text"], buttons=MAIN_KEYBOARD)
    
    elif data == "btn_1":
        text_1 = (
            "- اوامر التفعيل - التعطيل :\n"
            "↢ تفعيل - تعطيل ( ضافني | الاذكار | الثنائي | افتاري | التسليه | الكت | الترحيب | الردود | الانذار | الايدي | الرابط | الحمايه )"
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
    # await assistant.start()
    # await call_py.start()
    print("🤖 البوت يعمل بنجاح...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_all())
