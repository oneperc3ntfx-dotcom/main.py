import os
import logging
import sqlite3
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
MAIN_GROUP = os.getenv("MAIN_GROUP_LINK")

GROUPS = {
    "HFM": os.getenv("HFM_GROUP_LINK"),
    "EXNESS": os.getenv("EXNESS_GROUP_LINK"),
    "VALETAX": os.getenv("VALETAX_GROUP_LINK"),
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    step TEXT
)
""")
conn.commit()

def update_user(uid, field, value):
    cursor.execute(f"UPDATE members SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()

def save_user(uid, username):
    cursor.execute("INSERT OR IGNORE INTO members (user_id, username, step) VALUES (?, ?, 'start')",
                   (uid, username))
    conn.commit()

def get_user(uid):
    cursor.execute("SELECT * FROM members WHERE user_id=?", (uid,))
    return cursor.fetchone()


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username)

    keyboard = [[InlineKeyboardButton("🤝 Join Mitra", callback_data="menu_join")]]

    await update.message.reply_text(
        "🚀 ONE PERCENT FX BOT",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= MENU =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("HFM", callback_data="broker_HFM")],
        [InlineKeyboardButton("EXNESS", callback_data="broker_EXNESS")],
        [InlineKeyboardButton("VALETAX", callback_data="broker_VALETAX")]
    ]

    await q.message.reply_text("Pilih broker:", reply_markup=InlineKeyboardMarkup(keyboard))


# ================= BROKER =================
async def broker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    broker = q.data.split("_")[1]

    update_user(uid, "broker", broker)
    update_user(uid, "step", "waiting_photo")

    await q.message.reply_text(f"""
📌 LANGKAH 1

🔗 Join grup:
{GROUPS[broker]}

📸 Setelah itu kirim screenshot akun MT5 (saldo + ID)
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
📌 Cara lihat ID Telegram:
https://t.me/caralihatidtele

────────────────────
Kirim format di atas ya 👇
""")


# ================= FORM =================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    update_user(uid, "form", update.message.text)
    update_user(uid, "step", "confirm")

    keyboard = [[InlineKeyboardButton("✅ SAYA SUDAH REGISTRASI", callback_data=f"confirm_{uid}")]]

    await update.message.reply_text(
        "KONFIRMASI DATA",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CONFIRM =================
async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = int(q.data.split("_")[1])
    data = get_user(uid)

    file_id = data[3]
    form = data[4]

    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{uid}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=f"""
📥 NEW MEMBER

{form}
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await context.bot.send_message(
        uid,
        "⏳ MOHON TUNGGU SEBENTAR...\nKami cek data kamu dulu ya 🔍"
    )


# ================= ADMIN =================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    action, uid = q.data.split("_")
    uid = int(uid)

    if action == "approve":
        await context.bot.send_message(
            uid,
            "🎉 SELAMAT BERGABUNG 🚀\n\n👉 LINK SIGNAL GROUP AKAN DIBERIKAN DI SINI"
        )

    else:
        await context.bot.send_message(
            uid,
            "❌ MOHON MAAF\nREGISTRASI KAMU ADA KESALAHAN\n\nHubungi @ADMOnePercentsFX"
        )

    await q.message.edit_text("DONE")


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
    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    logger.info("BOT RUNNING FIXED VERSION")
    app.run_polling()


if __name__ == "__main__":
    main()
