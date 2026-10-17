import asyncio
import os
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

# ==================== [ إعدادات البيانات ] ====================
DEVELOPER_ID = 6913101408  

ASSISTANT_API_ID = 37284623
ASSISTANT_API_HASH = '4e5dd535ba915df2bcdd968d167cd3cb'
ASSISTANT_SESSION = '1BJWap1wBuxxZOH7XqLOV4x2l_ulSey8IZ6TkYsUixYI-MydO68HvcpBwMKhcOqYqFMOKuvM7pY1eEu3i_jRrwWzXv__CPb1-LKHZnw5AM4WuadsTmRTHWFBVMPdXIe6EJZK7MEBBbRxEBuQBsTDASfH7hNFlXsdKV7NLjJPtgcDi7fJs8_dmUpUigt_1qh-AnqpT3uhKKOyhheUshBNs3MeaRM7sviGpK0q_a3zJygPgOM-sOugUVnEsgXx6RAvi0UpuQdJATdWkI1KGPUvOKut3VanOL4kJ2rFLOkSlzgWMEFarA5OXlOVYktgpUjiyoHOAUIXFg1MMapDSXFWVy01hAmjzu2U='
BOT_TOKEN = '8750112907:AAHUhh9WI1E_BMW6TczwFL1jJRzLsYAIqPQ'

# ==============================================================

bot = TelegramClient('aria_bot_session', ASSISTANT_API_ID, ASSISTANT_API_HASH).start(bot_token=BOT_TOKEN)
assistant = TelegramClient(StringSession(ASSISTANT_SESSION), ASSISTANT_API_ID, ASSISTANT_API_HASH)
call_py = PyTgCalls(assistant)

@bot.on(events.NewMessage(pattern='^(تشغيل|فيد|فيديو)(.*)'))
async def play_handler(event):
    cmd = event.pattern_match.group(1)
    query = event.pattern_match.group(2).strip()
    chat_id = event.chat_id
    
    if not query:
        await event.reply("• يرجى كتابة اسم الأغنية أو الرابط بعد الأمر!")
        return

    await event.reply(f"⏳ جاري البحث عن [{query}] وتشغيلها في المكالمة...")
    
    # رابط بث تجريبي متوافق مع الحساب المساعد، يمكنك استبداله بروابط البحث المباشرة
    stream_url = "http://docs.evostream.com/sample_content/assets/sintel1m720p.mp4"
    
    try:
        if cmd == "تشغيل":
            # تشغيل صوت فقط
            await call_py.play(chat_id, MediaStream(stream_url, video_flags=MediaStream.NO_VIDEO))
        else:
            # تشغيل فيديو وصوت معاً
            await call_py.play(chat_id, MediaStream(stream_url))
    except Exception as e:
        await event.reply(f"❌ حدث خطأ أثناء التشغيل: {str(e)}")

@bot.on(events.NewMessage(pattern='^(توقف|ايقاف|إيقاف|تخطي)$'))
async def control_handler(event):
    cmd = event.text
    chat_id = event.chat_id
    
    try:
        if cmd == "توقف":
            await call_py.pause(chat_id)
            await event.reply("⏸️ تم إيقاف التشغيل مؤقتاً.")
        elif cmd in ["إيقاف", "ايقاف"]:
            await call_py.leave(chat_id)
            await event.reply("⏹️ تم إيقاف التشغيل نهائياً ومغادرة حساب المساعد.")
        elif cmd == "تخطي":
            await call_py.drop(chat_id)
            await event.reply("⏭️ تم تخطي المادة الصوتية الحالية ونزول الحساب المساعد.")
    except Exception as e:
        await event.reply(f"⚠️ أمر التحكم واجه مشكلة أو الحساب غير متصل حالياً.")

async def start_all():
    await bot.start()
    await assistant.start()
    await call_py.start()
    print("🎵 بوت الأغاني والمكالمات يعمل بنجاح الآن...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(start_all())
