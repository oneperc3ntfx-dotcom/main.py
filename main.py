import os
import logging
import sqlite3
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

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
    invite_used INTEGER DEFAULT 0,
    mode TEXT DEFAULT 'mitra',
    form_sent INTEGER DEFAULT 0
)
""")
conn.commit()

# ================= DB =================
def save_user(uid, username):

    cursor.execute("""
    INSERT OR IGNORE INTO members (
        user_id,
        username,
        step,
        status
    )
    VALUES (?, ?, 'start', 'pending')
    """, (uid, username))

    conn.commit()

def update_user(uid, field, value):

    cursor.execute(
        f"UPDATE members SET {field}=? WHERE user_id=?",
        (value, uid)
    )

    conn.commit()

def get_user(uid):

    cursor.execute(
        "SELECT * FROM members WHERE user_id=?",
        (uid,)
    )

    return cursor.fetchone()

def get_all():

    cursor.execute("SELECT * FROM members")

    return cursor.fetchall()

# ================= PARSE FORM =================
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

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    save_user(user.id, user.username)

    update_user(user.id, "step", "start")
    update_user(user.id, "form_sent", 0)

    keyboard = [
        [
            InlineKeyboardButton(
                "🤝 Pindah Mitra",
                callback_data="menu_join"
            )
        ],
        [
            InlineKeyboardButton(
                "🔥 Sudah Daftar di Link Bio",
                callback_data="menu_bio"
            )
        ]
    ]

    await update.message.reply_text(
        "🚀 ONE PERCENT FX BOT",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= MENU JOIN =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    update_user(uid, "mode", "mitra")

    keyboard = [
        [InlineKeyboardButton("HFM", callback_data="broker_HFM")],
        [InlineKeyboardButton("EXNESS", callback_data="broker_EXNESS")],
        [InlineKeyboardButton("VALETAX", callback_data="broker_VALETAX")],
    ]

    await q.message.reply_text(
        "Pilih broker:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= MENU BIO =================
async def menu_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id

    update_user(uid, "mode", "bio")

    keyboard = [
        [InlineKeyboardButton("HFM", callback_data="bio_HFM")],
        [InlineKeyboardButton("EXNESS", callback_data="bio_EXNESS")],
        [InlineKeyboardButton("VALETAX", callback_data="bio_VALETAX")],
    ]

    await q.message.reply_text(
        "Pilih broker:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BROKER MITRA =================
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

# ================= BROKER BIO =================
async def broker_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    uid = q.from_user.id
    br = q.data.split("_")[1]

    update_user(uid, "broker", br)
    update_user(uid, "step", "waiting_photo")

    await q.message.reply_text("""
Baik setelah melakukan pendaftaran broker,
sekarang kamu deposit terlebih dahulu ya dengan minimal 250 rb.

Jika sudah deposit,
silahkan screenshot profil broker kamu / MT5 yang terlihat saldo nya 📸
""")

# ================= PHOTO =================
async def photo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    user = get_user(uid)

    if not user:

        await update.message.reply_text(
            "❌ Silahkan klik /start terlebih dahulu"
        )

        return

    if user[5] != "waiting_photo":

        await update.message.reply_text(
            "❌ Saya tidak mengerti.\nSilahkan klik /start"
        )

        return

    file_id = update.message.photo[-1].file_id

    update_user(uid, "photo", file_id)
    update_user(uid, "step", "waiting_form")

    await update.message.reply_text("""
📋 LANGKAH 2 - DATA AKHIR

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER:

────────────────────

📌 Cara lihat ID telegram Silahkan Klik Link Di Bawah
https://t.me/caralihatidtele

Kirim sesuai format 👇
""")

# ================= FORM =================
async def form_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    uid = update.effective_user.id

    user = get_user(uid)

    if not user:
        return

    if user[5] != "waiting_form":
        return

    if user[9] == 1:

        await update.message.reply_text(
            "❌ Form sudah dikirim.\nSilahkan klik /start untuk mengulang percakapan"
        )

        return

    text = update.message.text

    valid_form = (
        "ID WALLET" in text
        and "USER ID TELEGRAM" in text
        and "USERNAME" in text
        and "BROKER" in text
    )

    if not valid_form:
        return

    parsed = parse_form(text)

    update_user(uid, "form", text)
    update_user(uid, "broker", parsed["broker"])
    update_user(uid, "status", "confirm")
    update_user(uid, "step", "done")
    update_user(uid, "form_sent", 1)

    context.user_data["skip_invalid"] = True

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ SAYA SUDAH REGISTRASI",
                callback_data=f"confirm_{uid}"
            )
        ]
    ]

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

    if data[6] == "pending_admin":
        return

    update_user(uid, "status", "pending_admin")

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve_{uid}"
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject_{uid}"
            )
        ]
    ]

    await context.bot.send_photo(
        ADMIN_ID,
        photo=data[3],
        caption=f"📥 NEW MEMBER\n\n{data[4]}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await context.bot.send_message(
        uid,
        "⏳ WAITING APPROVAL..."
    )

# ================= AUTO REVOKE =================
async def revoke_later(context: ContextTypes.DEFAULT_TYPE):

    try:

        link = context.job.data["link"]

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

    data = get_user(uid)

    if data[6] in ["approved", "rejected"]:
        return

    if action == "approve":

        expire = datetime.utcnow() + timedelta(minutes=10)

        invite = await context.bot.create_chat_invite_link(
            chat_id=MAIN_GROUP,
            member_limit=1,
            expire_date=expire
        )

        update_user(uid, "status", "approved")
        update_user(uid, "invite_used", 1)

        parsed = parse_form(data[4])

        await context.bot.send_message(
            uid,
            f"""
🎉 APPROVED 🚀

💎 1 USER = 1 PRIVATE LINK
⏳ EXPIRE 10 MENIT

👉 {invite.invite_link}

💰 WALLET: {parsed['wallet']}
🆔 ID: {parsed['telegram_id']}

🔥 Selamat bergabung
"""
        )

    else:

        update_user(uid, "status", "rejected")

        # ✅ HANYA INI YANG DIUBAH
        await context.bot.send_message(
            uid,
            "❌ Mohon maaf, registrasi kamu gagal atau ada kesalahan pada data yang dikirim.\n\nSilahkan hubungi admin untuk masalah ini ya @ADMOnePercentsFX"
        )

        await q.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "✅ COMPLETED",
                        callback_data="done"
                    )
                ]
            ])
        )

# ================= MEMBER =================
async def member(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = get_all()

    text = "📊 LIST MEMBER ONE PERCENT FX\n\n"

    for d in data:

        if d[6] != "approved":
            continue

        parsed = parse_form(d[4] or "")

        text += f"""
💰 ID WALLET: {parsed['wallet']}
🆔 USER ID: {d[0]}
👤 USERNAME: {d[1]}
🏦 BROKER: {parsed['broker']}
📌 STATUS: {d[6]}

────────────────────
"""

    await update.message.reply_text(text)

# ================= INVALID CHAT =================
async def invalid_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if context.user_data.get("skip_invalid"):

        context.user_data["skip_invalid"] = False
        return

    uid = update.effective_user.id

    user = get_user(uid)

    if not user:

        await update.message.reply_text(
            "❌ Saya tidak mengerti.\nSilahkan klik /start untuk memulai"
        )

        return

    if user[5] == "done":

        await update.message.reply_text(
            "❌ Saya tidak mengerti.\nSilahkan klik /start untuk memulai"
        )

        return

    if user[5] == "waiting_photo":

        await update.message.reply_text(
            "📸 Silahkan kirim screenshot profil broker / MT5 yang terlihat saldo nya"
        )

        return

    if user[5] == "waiting_form":

        text = update.message.text

        valid_form = (
            "ID WALLET" in text
            and "USER ID TELEGRAM" in text
            and "USERNAME" in text
            and "BROKER" in text
        )

        if valid_form:
            return

        await update.message.reply_text("""
📋 LANGKAH 2 - DATA AKHIR

💰 ID WALLET BROKER:
🆔 USER ID TELEGRAM:
👤 USERNAME TELEGRAM:
🏦 BROKER:

────────────────────

📌 Cara lihat ID telegram Silahkan Klik Link Di Bawah
https://t.me/caralihatidtele

Kirim sesuai format 👇
""")

        return

    await update.message.reply_text(
        "❌ Saya tidak mengerti.\nSilahkan klik /start untuk memulai"
    )

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
        return await broker_bio(update, context)

    if d.startswith("confirm_"):
        return await confirm(update, context)

    if d.startswith("approve_") or d.startswith("reject_"):
        return await admin(update, context)

# ================= MAIN =================
def main():

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("member", member))

    app.add_handler(CallbackQueryHandler(router))

    app.add_handler(
        MessageHandler(filters.PHOTO, photo)
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            form_text
        ),
        group=1
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            invalid_message
        ),
        group=99
    )

    logger.info("BOT FINAL STABLE RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()
