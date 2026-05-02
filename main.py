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
MAIN_GROUP = int(os.getenv("MAIN_GROUP_LINK"))

GROUPS = {
    "HFM": os.getenv("HFM_GROUP_LINK"),
    "EXNESS": os.getenv("EXNESS_GROUP_LINK"),
    "VALETAX": os.getenv("VALETAX_GROUP_LINK"),
}

logging.basicConfig(level=logging.INFO)

# ================= DB =================
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
    invite_used INTEGER DEFAULT 0,
    flow TEXT DEFAULT 'mitra'
)
""")
conn.commit()


def save_user(uid, username):
    cursor.execute("""
    INSERT OR IGNORE INTO members (user_id, username, step, status, flow)
    VALUES (?, ?, 'start', 'pending', 'mitra')
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
        [InlineKeyboardButton("🤝 PINDAH MITRA", callback_data="menu_mitra")],
        [InlineKeyboardButton("📌 SUDAH DAFTAR LINK BIO", callback_data="bio_done")]
    ]

    await update.message.reply_text(
        "🚀 ONE PERCENT FX BOT",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= RANDOM CHAT HANDLER =================
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    # tetap simpan user walaupun spam chat
    save_user(uid, update.effective_user.username)

    await update.message.reply_text(
        "❌ SAYA TIDAK MENGERTI\n\nSILAHKAN KLIK /START"
    )


# ================= ADMIN APPROVE =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])
    user = get_user(uid)

    expire = datetime.utcnow() + timedelta(minutes=10)

    invite = await context.bot.create_chat_invite_link(
        chat_id=MAIN_GROUP,
        member_limit=1,
        expire_date=expire
    )

    update_user(uid, "status", "approved")

    await context.bot.send_message(
        uid,
        f"""
🎉 APPROVED

🔗 LINK JOIN:
{invite.invite_link}

⏳ EXPIRE 10 MENIT
"""
    )

    await q.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ COMPLETED", callback_data="done")]
        ])
    )


# ================= REJECT =================
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])

    update_user(uid, "status", "rejected")

    await context.bot.send_message(uid, "❌ REJECTED")

    await q.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ COMPLETED", callback_data="done")]
        ])
    )


# ================= ADMIN ROUTER =================
async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data.startswith("approve_"):
        return await approve(update, context)

    if data.startswith("reject_"):
        return await reject(update, context)


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data

    if d == "menu_mitra":
        return await update.callback_query.message.reply_text("MENU MITRA")

    if d == "bio_done":
        return await update.callback_query.message.reply_text("MENU BIO")

    if d.startswith("approve") or d.startswith("reject"):
        return await admin_router(update, context)

    if d == "done":
        return await update.callback_query.answer("SUDAH SELESAI", show_alert=True)


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(CallbackQueryHandler(admin_router))

    # fallback chat random
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))

    app.run_polling()


if __name__ == "__main__":
    main()
