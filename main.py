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


# ================= DB =================
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


# ================= PARSER =================
def parse_form(text):
    data = {
        "wallet": "-",
        "telegram_id": "-",
        "username": "-",
        "broker": "-"
    }

    for line in text.split("\n"):
        line = line.strip()

        if "ID WALLET" in line:
            data["wallet"] = line.split(":")[-1].strip()
        elif "USER ID TELEGRAM" in line:
            data["telegram_id"] = line.split(":")[-1].strip()
        elif "USERNAME" in line:
            data["username"] = line.split(":")[-1].strip()
        elif "BROKER" in line:
            data["broker"] = line.split(":")[-1].strip()

    return data


# ================= START (UPDATED) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.username)

    keyboard = [
        [InlineKeyboardButton("🤝 PINDAH MITRA", callback_data="menu_join")],
        [InlineKeyboardButton("📌 SUDAH DAFTAR DI LINK BIO", callback_data="menu_bio")]
    ]

    await update.message.reply_text(
        "🚀 ONE PERCENT FX BOT",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= MENU JOIN (LAMA TETAP) =================
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


# ================= MENU BIO (BARU) =================
async def menu_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    keyboard = [
        [InlineKeyboardButton("HFM", callback_data="bio_HFM")],
        [InlineKeyboardButton("EXNESS", callback_data="bio_EXNESS")],
        [InlineKeyboardButton("VALETAX", callback_data="bio_VALETAX")],
    ]

    await q.message.reply_text(
        "Pilih broker:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ================= BROKER (JOIN MITRA LAMA) =================
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

📸 Kirim screenshot MT5 (saldo + ID akun)
""")


# ================= BIO FLOW (BARU) =================
async def bio_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    br = q.data.split("_")[1]

    update_user(uid, "broker", br)
    update_user(uid, "step", "waiting_deposit")

    await q.message.reply_text("""
BAIK SETELAH MELAKUKAN PENDAFTARAN BROKER,
SEKARANG KAMU DEPOSIT TERLEBIH DAHULU YA
DENGAN MINIMAL 250 RIBU.

JIKA SUDAH DEPOSIT,
SILAHKAN SCREENSHOT PROFIL BROKER / MT5
YANG TERLIHAT SALDO NYA.
""")


# ================= PHOTO HANDLER =================
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    file_id = update.message.photo[-1].file_id

    user = get_user(uid)
    if not user:
        return

    step = user[5]

    # FLOW LAMA
    if step == "waiting_photo":
        update_user(uid, "photo", file_id)
        update_user(uid, "step", "waiting_form")

        await update.message.reply_text("""
📋 LANGKAH 2 - DATA AKHIR

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER:

────────────────────
KIRIM SESUAI FORMAT 👇
""")

    # FLOW BARU BIO
    elif step == "waiting_deposit":
        update_user(uid, "photo", file_id)
        update_user(uid, "step", "waiting_form")

        await update.message.reply_text("""
📋 LANGKAH 2 - DATA AKHIR

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER:

────────────────────
KIRIM SESUAI FORMAT 👇
""")


# ================= TEXT =================
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user = get_user(uid)

    if not user:
        await update.message.reply_text("KLIK /start")
        return

    if user[5] != "waiting_form":
        await update.message.reply_text("SAYA TIDAK MENGERTI, SILAHKAN KLIK /start")
        return

    parsed = parse_form(update.message.text)

    update_user(uid, "form", update.message.text)
    update_user(uid, "status", "confirm")
    update_user(uid, "broker", parsed["broker"])

    keyboard = [
        [InlineKeyboardButton("SAYA SUDAH REGISTRASI", callback_data=f"confirm_{uid}")]
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
            InlineKeyboardButton("APPROVE", callback_data=f"approve_{uid}"),
            InlineKeyboardButton("REJECT", callback_data=f"reject_{uid}")
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        photo=data[3],
        caption=data[4],
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await context.bot.send_message(uid, "WAITING APPROVAL...")


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

        parsed = parse_form(get_user(uid)[4])

        await context.bot.send_message(
            uid,
            f"""
APPROVED

👉 {invite.invite_link}

WALLET: {parsed['wallet']}
ID: {parsed['telegram_id']}
"""
        )

        if context.job_queue:
            context.job_queue.run_once(
                lambda ctx: context.bot.revoke_chat_invite_link(
                    MAIN_GROUP, invite.invite_link
                ),
                when=600
            )

    else:
        update_user(uid, "status", "rejected")
        await context.bot.send_message(uid, "REJECTED")


    try:
        q.message.edit_text("COMPLETED")
    except:
        pass


# ================= FALLBACK =================
async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("SAYA TIDAK MENGERTI, SILAHKAN KLIK /start")


# ================= MEMBER =================
async def member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = get_all()

    text = "LIST MEMBER\n\n"

    for d in data:
        parsed = parse_form(d[4] or "")
        text += f"{d[0]} | {d[1]} | {parsed['broker']} | {d[6]}\n"

    await update.message.reply_text(text)


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = update.callback_query.data

    if d == "menu_join":
        return await menu_join(update, context)

    if d == "menu_bio":
        return await menu_bio(update, context)

    if d.startswith("broker_"):
        return await broker(update, context)

    if d.startswith("bio_"):
        return await bio_flow(update, context)

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
    app.add_handler(MessageHandler(filters.TEXT, fallback))

    app.run_polling()


if __name__ == "__main__":
    main()
