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

# ================= DB =================
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
        "👋 Selamat datang di ONE PERCENT FX",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= MENU =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🏦 HFM", callback_data="broker_HFM")],
        [InlineKeyboardButton("🏦 EXNESS", callback_data="broker_EXNESS")],
        [InlineKeyboardButton("🏦 VALETAX", callback_data="broker_VALETAX")]
    ]

    await query.message.reply_text(
        "💡 Pilih broker:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= BROKER =================
async def broker_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    broker = query.data.split("_")[1]

    update_user(user_id, "broker", broker)
    update_user(user_id, "status", "step_group")

    await query.message.reply_text(
        f"""📌 PINDAH MITRA

🔗 {GROUPS[broker]}

📸 Setelah selesai kirim screenshot akun (MT5 / broker)
yang terlihat SALDO & ID AKUN."""
    )


# ================= PHOTO (FIXED SEND TO ADMIN) =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    file_id = update.message.photo[-1].file_id

    update_user(user.id, "photo", file_id)
    update_user(user.id, "status", "step_form")

    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user.id}")
        ]
    ]

    cursor.execute("SELECT * FROM members WHERE user_id=?", (user.id,))
    data = cursor.fetchone()

    # 🔥 SEND PHOTO TO ADMIN + BUTTON
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=file_id,
        caption=f"""
📥 MEMBER SUBMISSION

🆔 USER ID: {data[0]}
👤 USERNAME: {data[1]}
🏦 BROKER: {data[2]}
📊 STATUS: {data[7]}

📌 WAITING VERIFICATION...
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text(
        """📋 LANGKAH 2 - DATA AKHIR

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER YANG DIGUNAKAN:

📌 Kirim data dengan benar ya."""
    )


# ================= TEXT =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    update_user(user.id, "form", update.message.text)
    update_user(user.id, "status", "pending")

    keyboard = [
        [
            InlineKeyboardButton("✅ SAYA SUDAH REGISTRASI", callback_data=f"confirm_{user.id}")
        ]
    ]

    await update.message.reply_text(
        "📌 KONFIRMASI DATA",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================= CONFIRM =================
async def confirm_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = int(query.data.split("_")[1])

    update_user(uid, "status", "waiting_review")

    await context.bot.send_message(
        chat_id=uid,
        text="⏳ MOHON TUNGGU, kami sedang cek data kamu..."
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"""
📥 NEW MEMBER CONFIRM

USER ID: {uid}
STATUS: WAITING APPROVAL
"""
    )


# ================= ADMIN ACTION (FIXED) =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("_")
    uid = int(uid)

    cursor.execute("SELECT broker FROM members WHERE user_id=?", (uid,))
    broker = cursor.fetchone()[0]

    if action == "approve":

        invite = await context.bot.create_chat_invite_link(
            chat_id=MAIN_GROUP,
            member_limit=1
        )

        await context.bot.send_message(
            chat_id=uid,
            text=f"""🎉 APPROVED!

Selamat bergabung 🚀

👉 {invite.invite_link}

🔥 Welcome to ONE PERCENT FX"""
        )

    else:

        await context.bot.send_message(
            chat_id=uid,
            text="❌ MOHON MAAF\n\nRegistrasi kamu ada kesalahan.\nSilahkan hubungi admin: @ADMOnePercentsFX"
        )

    await query.message.edit_text(f"Processed: {action.upper()}")


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


# ================= MEMBER LIST =================
async def member_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    members = get_all_members()

    text = "📊 MEMBER LIST\n\n"

    for m in members:
        text += f"{m[0]} | {m[1]} | {m[2]} | {m[7]}\n"

    await update.message.reply_text(text)


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("member", member_list))

    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("BOT RUNNING - FIXED PRODUCTION MODE")
    app.run_polling()


if __name__ == "__main__":
    main()
