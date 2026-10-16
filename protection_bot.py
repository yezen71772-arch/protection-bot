# -*- coding: utf-8 -*-
"""
بوت حماية الجروبات - النسخة الخاصة المطورة
المميزات: حظر/طرد بالكتابة + رتب (مالك أساسي، مالك، مدير، مميز) + ألعاب + أمر ايدي
التثبيت:  pip install "python-telegram-bot[job-queue]"
ضع التوكن ثم شغّل:  python protection_bot.py
"""

import json, os, re, time, random
from telegram import Update, ChatPermissions
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          ContextTypes, filters)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")   # يقرأ التوكن من متغير البيئة

DEVELOPER_ID = 6913101408   # مطور البوت - صلاحيات عليا في كل الجروبات

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "antilink": True,
    "antiflood": True,
    "badwords": True,
    "welcome": True,
    "flood_limit": 7,
    "bad_words_list": ["كلب", "حمار", "تافه", "idiot", "stupid"],
    "welcome_msg": "أهلاً بك {name} في {chat} 🌹 اتبع القوانين واحترم الأعضاء",
    "ranks": {},   # {user_id: "مالك"}
}

# رتب البوت ومستوياتها
RANK_LEVELS = {"مالك اساسي": 4, "مالك": 3, "مدير": 2, "مميز": 1}
RANK_BADGES = {"مالك اساسي": "👑 مالك أساسي", "مالك": "🎖 مالك",
               "مدير": "⭐ مدير", "مميز": "🌟 مميز"}

# ---------- حفظ الإعدادات ----------
def load_all():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_all(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_settings(chat_id):
    data = load_all()
    s = {**DEFAULT_SETTINGS, **data.get(str(chat_id), {})}
    s["ranks"] = s.get("ranks") or {}
    return s

def set_setting(chat_id, key, value):
    data = load_all()
    cid = str(chat_id)
    data.setdefault(cid, {}).update({key: value, "chat_id": chat_id})
    save_all(data)

def set_rank(chat_id, user_id, rank):
    s = get_settings(chat_id)
    ranks = s["ranks"]
    if rank is None:
        ranks.pop(str(user_id), None)
    else:
        ranks[str(user_id)] = rank
    set_setting(chat_id, "ranks", ranks)

async def get_user_rank(update, chat) -> str:
    """مالك أساسي = منشئ الجروب تلقائياً، ثم الرتب المخزنة"""
    member = await chat.get_member(update.effective_user.id)
    if member.status == "creator":
        return "مالك اساسي"
    s = get_settings(chat.id)
    return s["ranks"].get(str(update.effective_user.id), "")

async def get_target_rank(chat, user_id) -> str:
    try:
        member = await chat.get_member(user_id)
        if member.status == "creator":
            return "مالك اساسي"
    except Exception:
        pass
    s = get_settings(chat.id)
    return s["ranks"].get(str(user_id), "")

async def user_level(update, chat):
    """مستوى القوة: المطور ثم الرتبة أو أدمن تيليجرام"""
    if update.effective_user.id == DEVELOPER_ID:
        return 999
    member = await chat.get_member(update.effective_user.id)
    if member.status in ("administrator", "creator"):
        return 99
    return RANK_LEVELS.get(await get_user_rank(update, chat), 0)

# ---------- الأوامر ----------
async def start(update, ctx):
    await update.message.reply_text(
        "أنا بوت حماية الجروبات 🛡\n\n"
        "<b>أوامر الإدارة (بالرد على الشخص):</b>\n"
        "حظر - حظر الشخص ومنعه من العودة\n"
        "طرد - طرد الشخص (يقدر يرجع)\n"
        "الغاء الحظر - فك الحظر\n"
        "كتم - منع الكتابة مؤقتاً\n"
        "فك الكتم - السماح بالكتابة\n\n"
        "<b>الرتب (يرفعها مالك الجروب بالرد):</b>\n"
        "رفع مالك / رفع مدير / رفع مميز\n"
        "تنزيل - إزالة الرتبة\n\n"
        "<b>معلومات:</b>\n"
        "ايدي - بيانات الحساب\n"
        "/settings - إعدادات الحماية\n"
        "antilink/antiflood/badwords/welcome on|off\n\n"
        "<b>الألعاب:</b>\n"
        "لعبة - تخمين رقم (1-100)\n"
        "نرد - زر النرد\n"
        "حجره ورقه مقص - ضد البوت",
        parse_mode="HTML")

async def toggle_cmd(update, ctx):
    if await user_level(update, update.effective_chat) < 3:
        return await update.message.reply_text("الأمر لمدير الجروب فأعلى ⚠")
    key = update.message.text.split()[0].lstrip("/").lower()
    arg = (ctx.args[0].lower() if ctx.args else "")
    if arg not in ("on", "off"):
        return await update.message.reply_text("استخدم: /%s on أو off" % key)
    set_setting(update.effective_chat.id, key, arg == "on")
    await update.message.reply_text("✅ تم " + ("تشغيل " if arg == "on" else "إيقاف ") + key)

async def dev_cmd(update, ctx):
    """أمر خاص بالمطور"""
    if update.effective_user.id != DEVELOPER_ID:
        return await update.message.reply_text("⚠ هذا الأمر لمطور البوت فقط")
    data = load_all()
    groups = [d for d in data.values() if d.get("chat_id")]
    total_ranks = sum(len(d.get("ranks", {})) for d in groups)
    await update.message.reply_text(
        "👨‍💻 <b>لوحة المطور</b>\n"
        "الجروبات المسجلة: <code>%d</code>\n"
        "مجموع الرتب الممنوحة: <code>%d</code>\n"
        "الحالة: يعمل ✅"
        % (len(groups), total_ranks), parse_mode="HTML")

async def show_settings(update, ctx):
    s = get_settings(update.effective_chat.id)
    fmt = lambda b: "مفعّل ✅" if b else "متوقف ❌"
    await update.message.reply_text(
        "⚙ إعدادات الجروب:\nحذف الروابط: %s\nالحماية من السبام: %s\n"
        "الكلمات المسيئة: %s\nالترحيب: %s\nحد الرسائل: %s/10ث"
        % (fmt(s["antilink"]), fmt(s["antiflood"]), fmt(s["badwords"]),
           fmt(s["welcome"]), s["flood_limit"]))

# ---------- أوامر النصوص العربية (حظر/طرد/رتب/ايدي) ----------
async def get_target(update):
    """الشخص المستهدف: بالرد أو بالمنشن"""
    msg = update.message
    if msg.reply_to_message and msg.reply_to_message.from_user:
        return msg.reply_to_message.from_user
    if msg.reply_to_message and msg.reply_to_message.forward_from:
        return msg.reply_to_message.forward_from
    for ent in (msg.entities or []):
        if ent.type == "text_mention":
            return ent.user
    return None

async def cmd_ban(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 2:
        return await update.message.reply_text("⚠ هذا الأمر لمدير فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي تحظره")
    if target.id == update.effective_user.id:
        return await update.message.reply_text("ما تقدر تحظر نفسك 😅")
    if target.id == ctx.bot.id:
        return await update.message.reply_text("ما أقدر أحظر نفسي 😅")
    if target.id == DEVELOPER_ID:
        return await update.message.reply_text("⚠ ما أحد يقدر يحظر مطور البوت!")
    try:
        await chat.ban_member(target.id)
    except Exception:
        return await update.message.reply_text("❌ تأكد أن عندي صلاحية حظر الأعضاء")
    await update.message.reply_text(
        "⛔ تم حظر %s من الجروب\nبواسطة: %s" % (target.first_name, update.effective_user.first_name))

async def cmd_kick(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 1:
        return await update.message.reply_text("⚠ هذا الأمر للمميز فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي طرده")
    if target.id == DEVELOPER_ID:
        return await update.message.reply_text("⚠ ما أحد يقدر يطرد مطور البوت!")
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id)   # يقدر يرجع
    except Exception:
        return await update.message.reply_text("❌ تأكد أن عندي صلاحية حظر الأعضاء")
    await update.message.reply_text(
        "👟 تم طرد %s من الجروب (يقدر يرجع)\nبواسطة: %s"
        % (target.first_name, update.effective_user.first_name))

async def cmd_unban(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 2:
        return await update.message.reply_text("⚠ هذا الأمر لمدير فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص أو اكتب الغاء الحظر + الايدي الرقمي")
    args = update.message.text.split()
    uid = target.id
    if len(args) > 1 and args[1].lstrip("-").isdigit():
        uid = int(args[1])
    try:
        await chat.unban_member(uid)
    except Exception:
        return await update.message.reply_text("❌ ما قدرت أفك الحظر")
    await update.message.reply_text("✅ تم فك الحظر عن %s" % target.first_name)

async def cmd_mute(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 1:
        return await update.message.reply_text("⚠ هذا الأمر للمميز فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي تكتمه")
    try:
        await chat.restrict_member(target.id, ChatPermissions.no_permissions())
    except Exception:
        return await update.message.reply_text("❌ تأكد أن عندي صلاحية كتم الأعضاء")
    await update.message.reply_text("🔇 تم كتم %s" % target.first_name)

async def cmd_unmute(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 1:
        return await update.message.reply_text("⚠ هذا الأمر للمميز فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي تفك كتمه")
    try:
        await chat.restrict_member(target.id, ChatPermissions.all_permissions())
    except Exception:
        return await update.message.reply_text("❌ ما قدرت أفك الكتم")
    await update.message.reply_text("🔊 تم فك الكتم عن %s" % target.first_name)

async def cmd_promote(update, ctx):
    """رفع مالك / رفع مدير / رفع مميز (بالرد)"""
    chat = update.effective_chat
    text = update.message.text.strip()
    rank = None
    for r in RANK_LEVELS:
        if ("رفع " + r) in text:
            rank = r
            break
    if not rank:
        return
    if await user_level(update, chat) < 3:
        return await update.message.reply_text("⚠ رفع الرتب لمالك فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي ترفعه")
    if target.id == update.effective_user.id:
        return await update.message.reply_text("ما تقدر ترفع نفسك 😅")
    # مالك أساسي فقط يقدر يرفع مالك
    if rank == "مالك" and await get_user_rank(update, chat) != "مالك اساسي":
        return await update.message.reply_text("⚠ رفع مالك يحتاج المالك الأساسي")
    trank = await get_target_rank(chat, target.id)
    if RANK_LEVELS.get(trank, 0) >= RANK_LEVELS[rank]:
        return await update.message.reply_text("الشخص رتبته أعلى أصلاً ⚠")
    set_rank(chat.id, target.id, rank)
    await update.message.reply_text(
        "🎉 تم رفع %s إلى رتبة %s\nبواسطة: %s"
        % (target.first_name, RANK_BADGES[rank], update.effective_user.first_name))

async def cmd_demote(update, ctx):
    chat = update.effective_chat
    if await user_level(update, chat) < 3:
        return await update.message.reply_text("⚠ تنزيل الرتب لمالك فأعلى")
    target = await get_target(update)
    if not target:
        return await update.message.reply_text("رد على الشخص اللي تبي تنزله")
    if target.id == DEVELOPER_ID:
        return await update.message.reply_text("⚠ ما أحد يقدر ينزل مطور البوت!")
    if await get_target_rank(chat, target.id) == "مالك اساسي":
        return await update.message.reply_text("ما نقدر ننزل المالك الأساسي ⚠")
    set_rank(chat.id, target.id, None)
    await update.message.reply_text("📥 تم تنزيل %s من الرتب" % target.first_name)

async def cmd_id(update, ctx):
    chat = update.effective_chat
    target = await get_target(update) or update.effective_user
    if target.id == DEVELOPER_ID:
        rank, badge = "مطور", "👨‍💻 مطور البوت"
    else:
        rank = await get_target_rank(chat, target.id)
        badge = RANK_BADGES.get(rank, "👤 عضو")
    uname = "@" + target.username if target.username else "لا يوجد"
    await update.message.reply_text(
        "📇 <b>بيانات الحساب</b>\n"
        "الاسم: %s\n"
        "المعرف: %s\n"
        "الايدي: <code>%s</code>\n"
        "الرتبة: %s\n"
        "رتبة البوت: %s\n"
        "ايدي الجروب: <code>%s</code>"
        % (target.first_name, uname, target.id, badge, badge,
           chat.id),
        parse_mode="HTML")

# ---------- الألعاب ----------
GAMES = {}

async def cmd_game(update, ctx):
    chat = update.effective_chat
    num = random.randint(1, 100)
    GAMES[chat.id] = {"num": num, "by": update.effective_user.first_name}
    await update.message.reply_text(
        "🎲 بدأت لعبة تخمين الرقم!\nاخترت رقم بين 1 و 100، من يخمنه أول؟\n"
        "اكتب رقمك مباشرة، أو (الغاء اللعبة) للإيقاف")

async def cmd_cancel_game(update, ctx):
    if GAMES.pop(update.effective_chat.id, None):
        await update.message.reply_text("🛑 تم إيقاف اللعبة")

async def cmd_dice(update, ctx):
    await update.message.reply_dice()

async def cmd_rps(update, ctx):
    bot_choice = random.choice(["حجره", "ورقه", "مقص"])
    emoji = {"حجره": "✊", "ورقه": "✋", "مقص": "✌️"}
    await update.message.reply_text(
        "اخترت %s %s\nاكتب (حجره ورقه مقص) مرة ثانية للعب مجدداً"
        % (bot_choice, emoji[bot_choice]))

# ---------- الحماية ----------
LINK_RE = re.compile(r"(https?://|t\.me/|www\.|\S+\.(com|net|org|xyz|io|me)\b)", re.I)
BAN_WORDS = {"حظر", "طرد", "الغاء الحظر", "فك الحظر", "كتم", "فك الكتم",
             "رفع مالك", "رفع مدير", "رفع مميز", "تنزيل", "ايدي",
             "لعبة", "نرد", "حجره ورقه مقص", "الغاء اللعبة"}

async def check_message(update: Update, ctx):
    msg = update.message
    if not msg or not msg.text or msg.from_user.is_bot:
        return
    chat = update.effective_chat
    text = msg.text.strip()
    low = text.lower()
    s = get_settings(chat.id)

    # ----- الأوامر النصية -----
    if text.startswith("حظر"):
        return await cmd_ban(update, ctx)
    if text.startswith("طرد"):
        return await cmd_kick(update, ctx)
    if text.startswith("الغاء الحظر") or text.startswith("فك الحظر"):
        return await cmd_unban(update, ctx)
    if text.startswith("كتم"):
        return await cmd_mute(update, ctx)
    if text.startswith("فك الكتم"):
        return await cmd_unmute(update, ctx)
    if text.startswith("رفع ") and any("رفع " + r in text for r in RANK_LEVELS):
        return await cmd_promote(update, ctx)
    if text == "تنزيل":
        return await cmd_demote(update, ctx)
    if text == "ايدي" or text == "أيدي" or text == "/id" or text.startswith("ايدي "):
        return await cmd_id(update, ctx)
    if text == "لعبة" or text == "اللعبة":
        return await cmd_game(update, ctx)
    if text == "الغاء اللعبة":
        return await cmd_cancel_game(update, ctx)
    if text == "نرد":
        return await cmd_dice(update, ctx)
    if low in ("حجره", "ورقه", "مقص", "حجره ورقه مقص"):
        return await cmd_rps(update, ctx)

    # ----- تخمين رقم اللعبة -----
    game = GAMES.get(chat.id)
    if game and text.isdigit() and 1 <= int(text) <= 100:
        g = int(text)
        if g == game["num"]:
            GAMES.pop(chat.id)
            await msg.reply_text("🎉 مبروك %s! الرقم الصحيح هو %d، فزت باللعبة!"
                                 % (msg.from_user.first_name, g))
        elif g < game["num"]:
            await msg.reply_text("⬆ رقمك أقل، جرب رقم أكبر")
        else:
            await msg.reply_text("⬇ رقمك أعلى، جرب رقم أصغر")
        return

    # ----- الحماية: تجاهل المشرفين وأصحاب الرتب -----
    if await user_level(update, chat) >= 1:
        return

    # 1) الروابط
    if s["antilink"] and LINK_RE.search(text):
        try:
            await msg.delete()
            await chat.restrict_member(msg.from_user.id, ChatPermissions.no_permissions())
            await chat.send_message("🚫 ممنوع نشر الروابط %s - تم كتمه"
                                    % msg.from_user.first_name)
        except Exception:
            pass
        return

    # 2) الكلمات المسيئة
    if s["badwords"] and any(w in low for w in s["bad_words_list"]):
        try:
            await msg.delete()
        except Exception:
            pass
        return

    # 3) السبام
    if s["antiflood"]:
        uid = (chat.id, msg.from_user.id)
        now = time.time()
        hist = ctx.bot_data.setdefault("flood", {}).setdefault(uid, [])
        hist[:] = [t for t in hist if now - t < 10]
        hist.append(now)
        if len(hist) > s["flood_limit"]:
            hist.clear()
            try:
                await chat.restrict_member(msg.from_user.id, ChatPermissions.no_permissions())
                await chat.send_message("🔇 تم كتم %s بسبب التكرار" % msg.from_user.first_name)
            except Exception:
                pass

# ---------- الترحيب ----------
async def welcome(update: Update, ctx):
    chat = update.effective_chat
    s = get_settings(chat.id)
    if not s["welcome"]:
        return
    for u in update.message.new_chat_members:
        if u.is_bot:
            continue
        await chat.send_message(s["welcome_msg"].format(name=u.first_name, chat=chat.title))

# ---------- التشغيل ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("settings", show_settings))
    app.add_handler(CommandHandler("dev", dev_cmd))
    for cmd in ("antilink", "antiflood", "badwords", "welcome"):
        app.add_handler(CommandHandler(cmd, toggle_cmd))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & ~filters.COMMAND, check_message))
    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
