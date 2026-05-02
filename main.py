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

GROUPS = {
    "HFM": os.getenv("HFM_GROUP_LINK"),
    "EXNESS": os.getenv("EXNESS_GROUP_LINK"),
    "VALETAX": os.getenv("VALETAX_GROUP_LINK"),
}

MAIN_GROUP = os.getenv("MAIN_GROUP_LINK")

# ================= LOGGING =================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ================= DATABASE =================
conn = sqlite3.connect("members.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS members (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    broker TEXT,
    wallet_id TEXT,
    telegram_id TEXT,
    form TEXT,
    photo TEXT,
    status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()

# ================= DB FUNCTIONS =================
def save_user(user_id, username):
    cursor.execute("""
    INSERT OR IGNORE INTO members (user_id, username, status)
    VALUES (?, ?, 'new')
    """, (user_id, username))
    conn.commit()


def update_user(user_id, field, value):
    cursor.execute(f"""
    UPDATE members SET {field}=? WHERE user_id=?
    """, (value, user_id))
    conn.commit()


def get_all_members():
    cursor.execute("SELECT * FROM members")
    return cursor.fetchall()


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    save_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("🤝 Join Gratis / Mitra", callback_data="menu_join")]
    ]

    await update.message.reply_text(
        "👋 Selamat datang di ONE PERCENT FX\n\nSilahkan pilih menu di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= MENU JOIN =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🏦 HFM", callback_data="broker_HFM")],
        [InlineKeyboardButton("🏦 EXNESS", callback_data="broker_EXNESS")],
        [InlineKeyboardButton("🏦 VALETAX", callback_data="broker_VALETAX")]
    ]

    await query.message.reply_text(
        "💡 Pilih broker yang kamu gunakan:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= BROKER SELECT =================
async def broker_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    broker = query.data.split("_")[1]

    update_user(user_id, "broker", broker)
    update_user(user_id, "status", "join_group")

    await query.message.reply_text(
        f"""📌 LANGKAH 1 - JOIN BROKER

Silahkan masuk ke grup berikut:
🔗 {GROUPS[broker]}

📢 Di dalam grup sudah tersedia panduan lengkap.

📸 Setelah selesai, kirim screenshot profil akun (MT5 / broker) yang terlihat saldo & ID."""
    )


# ================= PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if update.message is None:
        return

    file_id = update.message.photo[-1].file_id

    update_user(user_id, "photo", file_id)
    update_user(user_id, "status", "send_form")

    await update.message.reply_text(
        """📋 LANGKAH 2 - DATA AKHIR

Silahkan isi format berikut:

ID WALLET BROKER:
USER ID TELEGRAM:
USERNAME TELEGRAM:
BROKER YANG DIGUNAKAN:"""
    )


# ================= TEXT FORM =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    update_user(user_id, "form", update.message.text)
    update_user(user_id, "status", "confirm")

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ SAYA SUDAH REGISTRASI",
                callback_data=f"confirm_{user_id}"
            )
        ]
    ]

    await update.message.reply_text(
        "📌 KONFIRMASI REGISTRASI\n\nJika data sudah benar, klik tombol di bawah:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CONFIRM =================
async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = int(query.data.split("_")[1])

    update_user(uid, "status", "pending")

    cursor.execute("SELECT * FROM members WHERE user_id=?", (uid,))
    data = cursor.fetchone()

    await context.bot.send_message(
        chat_id=uid,
        text="⏳ MOHON DITUNGGU SEBENTAR, kami sedang verifikasi data kamu..."
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"""
📥 MEMBER BARU (CRM DATA)

USER ID: {data[0]}
USERNAME: {data[1]}
BROKER: {data[2]}
STATUS: {data[7]}
"""
    )


# ================= ADMIN APPROVE/REJECT =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("_")
    uid = int(uid)

    if action == "approve":
        update_user(uid, "status", "approved")

        await context.bot.send_message(
            chat_id=uid,
            text="🎉 APPROVED - Selamat bergabung di ONE PERCENT FX"
        )

    else:
        update_user(uid, "status", "rejected")

        await context.bot.send_message(
            chat_id=uid,
            text="❌ Registrasi ditolak. Hubungi admin."
        )


# ================= /MEMBER COMMAND =================
async def member_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = get_all_members()

    if not members:
        await update.message.reply_text("Belum ada member.")
        return

    text = "📊 DAFTAR MEMBER:\n\n"

    for m in members:
        text += (
            f"ID: {m[0]}\n"
            f"Username: {m[1]}\n"
            f"Broker: {m[2]}\n"
            f"Status: {m[7]}\n"
            "-----------------\n"
        )

    await update.message.reply_text(text)


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "menu_join":
        return await menu_join(update, context)

    if data.startswith("broker_"):
        return await broker_select(update, context)

    if data.startswith("confirm_"):
        return await confirm_registration(update, context)

    if data.startswith("approve") or data.startswith("reject"):
        return await admin_action(update, context)


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("member", member_list))

    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("BOT RUNNING - PERSISTENT CRM MODE")
    app.run_polling()


if __name__ == "__main__":
    main()
