import os
import logging
import sqlite3
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MAIN_GROUP = int(os.getenv("MAIN_GROUP_LINK"))  # MUST BE -100xxxx

SIGNAL_GROUP = os.getenv("SIGNAL_GROUP_LINK")

GROUPS = {
    "HFM": os.getenv("HFM_GROUP_LINK"),
    "EXNESS": os.getenv("EXNESS_GROUP_LINK"),
    "VALETAX": os.getenv("VALETAX_GROUP_LINK"),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ================= DATABASE =================
conn = sqlite3.connect("members.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    broker TEXT,
    photo TEXT,
    form TEXT,
    step TEXT,
    status TEXT DEFAULT 'pending',
    invite_used INTEGER DEFAULT 0
)
""")
conn.commit()


# ================= DB HELPERS =================
def save_user(uid, username):
    cursor.execute("""
    INSERT OR IGNORE INTO members (user_id, username, step, status)
    VALUES (?, ?, 'start', 'pending')
    """, (uid, username))
    conn.commit()


def update_user(uid, field, value):
    cursor.execute(f"UPDATE members SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()


def get_user(uid):
    cursor.execute("SELECT * FROM members WHERE user_id=?", (uid,))
    return cursor.fetchone()


def get_all():
    cursor.execute("SELECT * FROM members")
    return cursor.fetchall()


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("🤝 JOIN MITRA", callback_data="menu_join")]
    ]

    await update.message.reply_text(
        "🚀 ONE PERCENT FX BOT",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= MENU =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("HFM", callback_data="broker_HFM")],
        [InlineKeyboardButton("EXNESS", callback_data="broker_EXNESS")],
        [InlineKeyboardButton("VALETAX", callback_data="broker_VALETAX")],
    ]

    await q.message.reply_text(
        "Pilih broker:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= BROKER =================
async def broker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    br = q.data.split("_")[1]

    update_user(uid, "broker", br)
    update_user(uid, "step", "waiting_photo")

    await q.message.reply_text(f"""
📌 LANGKAH 1

👉 CARA PINDAH MITRA:
Silahkan buka link di bawah ini:

🔗 {GROUPS[br]}

📸 Kirim screenshot akun MT5 (saldo + ID)
""")


# ================= PHOTO =================
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    file_id = update.message.photo[-1].file_id

    update_user(uid, "photo", file_id)
    update_user(uid, "step", "waiting_form")

    await update.message.reply_text(f"""
📋 LANGKAH 2 - DATA AKHIR 🚀

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER:

────────────────────

📌 CARA MELIHAT USER ID TELEGRAM:
👉 https://t.me/caralihatidtele

────────────────────
⚠️ Kirim data sesuai format ya!
""")


# ================= TEXT =================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    user = get_user(uid)
    if not user:
        return

    if user[5] != "waiting_form":
        await update.message.reply_text("❌ Klik /start untuk mulai")
        return

    update_user(uid, "form", update.message.text)
    update_user(uid, "step", "confirm")

    keyboard = [
        [InlineKeyboardButton("✅ SAYA SUDAH REGISTRASI", callback_data=f"confirm_{uid}")]
    ]

    await update.message.reply_text(
        "KONFIRMASI DATA",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= CONFIRM =================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])
    data = get_user(uid)

    update_user(uid, "status", "pending_admin")

    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        photo=data[3],
        caption=f"📥 NEW MEMBER\n\n{data[4]}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await context.bot.send_message(uid, "⏳ WAITING APPROVAL...")


# ================= AUTO REVOKE =================
async def revoke_later(context: ContextTypes.DEFAULT_TYPE):
    uid = context.job.data["uid"]
    link = context.job.data["link"]

    try:
        await context.bot.revoke_chat_invite_link(
            chat_id=MAIN_GROUP,
            invite_link=link
        )
    except Exception as e:
        logger.error(e)


# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, uid = q.data.split("_")
    uid = int(uid)

    if action == "approve":

        expire = datetime.utcnow() + timedelta(minutes=10)

        invite = await context.bot.create_chat_invite_link(
            chat_id=MAIN_GROUP,
            member_limit=1,
            expire_date=expire
        )

        update_user(uid, "status", "approved")
        update_user(uid, "invite_used", 1)

        await context.bot.send_message(
            uid,
            f"""
🎉 APPROVED 🚀

💎 1 USER = 1 PRIVATE LINK
⏳ EXPIRE 10 MENIT

👉 {invite.invite_link}

🔥 Selamat bergabung
"""
        )

        context.job_queue.run_once(
            revoke_later,
            when=600,
            data={"uid": uid, "link": invite.invite_link},
        )

    else:
        update_user(uid, "status", "rejected")

        await context.bot.send_message(
            uid,
            "❌ REJECTED\nHubungi @ADMOnePercentsFX"
        )

    try:
        await q.message.edit_text("DONE")
    except:
        pass


# ================= /MEMBER =================
async def member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_all()

    if not data:
        await update.message.reply_text("📭 Belum ada member")
        return

    text = "📊 LIST MEMBER ONE PERCENT FX\n\n"

    for d in data:
        text += f"""
💰 ID WALLET BROKER: {d[3] if d[3] else '-'}
🆔 USER ID TELEGRAM: {d[0]}
👤 USERNAME TELEGRAM: {d[1]}
🏦 BROKER: {d[2]}
📌 STATUS: {d[6]}

────────────────────
"""

    await update.message.reply_text(text)


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data

    if d == "menu_join":
        return await menu_join(update, context)

    if d.startswith("broker_"):
        return await broker(update, context)

    if d.startswith("confirm_"):
        return await confirm(update, context)

    if d.startswith("approve") or d.startswith("reject"):
        return await admin(update, context)


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("member", member))

    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    logger.info("BOT RUNNING FINAL VERSION")
    app.run_polling()


if __name__ == "__main__":
    main()
