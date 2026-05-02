import os
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

# GROUP BROKER
GROUPS = {
    "HFM": os.getenv("HFM_GROUP_LINK"),
    "EXNESS": os.getenv("EXNESS_GROUP_LINK"),
    "VALETAX": os.getenv("VALETAX_GROUP_LINK"),
}

# GROUP UTAMA (VIP COMMUNITY)
MAIN_GROUP = os.getenv("MAIN_GROUP_LINK")

# TEMP STORAGE (simple memory)
user_data = {}


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🤝 Join Gratis / Mitra", callback_data="menu_join")]
    ]

    await update.message.reply_text(
        "👋 Selamat datang di ONE PERCENT FX\n\nPilih menu di bawah:",
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

    broker = query.data.split("_")[1]
    user_id = query.from_user.id

    user_data[user_id] = {
        "broker": broker
    }

    await query.message.reply_text(
        f"""📌 SILAHKAN PINDAH MITRA TERLEBIH DAHULU

🔗 Link:
{GROUPS[broker]}

📸 Setelah selesai, kirim screenshot profil (yang terlihat saldo)."""
    )


# ================= HANDLE PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data:
        return

    user_data[user_id]["photo"] = update.message.photo[-1].file_id

    await update.message.reply_text(
        """✍️ Sekarang kirim format berikut:

ID WALLET:
USER ID TELEGRAM:
BROKER YANG DI PAKAI:"""
    )


# ================= HANDLE TEXT FORM =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_data:
        return

    user_data[user_id]["form"] = update.message.text

    data = user_data[user_id]

    keyboard = [
        [
            InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user_id}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{user_id}")
        ]
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=data["photo"],
        caption=f"""
📥 REGISTRASI MEMBER BARU

{data['form']}

BROKER: {data['broker']}
USER ID: {user_id}
""",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📨 Data kamu sudah dikirim ke admin.")


# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, uid = query.data.split("_")
    uid = int(uid)

    if uid not in user_data:
        await query.message.edit_text("❌ Data user tidak ditemukan")
        return

    data = user_data[uid]

    # ================= APPROVE =================
    if action == "approve":

        broker = data["broker"]

        # kirim link broker
        await context.bot.send_message(
            chat_id=uid,
            text=f"""🎉 REGISTRASI DISETUJUI

📌 Join mitra kamu:
{GROUPS[broker]}

🚀 Lanjutkan ke langkah berikutnya..."""
        )

        # create invite group utama
        try:
            invite = await context.bot.create_chat_invite_link(
                chat_id=MAIN_GROUP,
                member_limit=1,
                creates_join_request=False
            )

            await context.bot.send_message(
                chat_id=uid,
                text=f"""🔥 GRUP UTAMA ONE PERCENT FX

👉 {invite.invite_link}

⚡ Selamat bergabung, semoga bisa grow bersama!"""
            )

        except Exception:
            await context.bot.send_message(
                chat_id=uid,
                text=f"""⚠️ Link otomatis gagal.

Silahkan join manual:
{MAIN_GROUP}"""
            )

        await query.message.edit_text("✅ APPROVED + MAIN GROUP SENT")


    # ================= REJECT =================
    else:

        await context.bot.send_message(
            chat_id=uid,
            text="""❌ Mohon maaf, registrasi kamu belum berhasil.

Silahkan hubungi admin:
@ADMOnePercentsFX"""
        )

        await query.message.edit_text("❌ REJECTED")


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data

    if data == "menu_join":
        return await menu_join(update, context)

    if data.startswith("broker_"):
        return await broker_select(update, context)

    if data.startswith("approve") or data.startswith("reject"):
        return await admin_action(update, context)


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("BOT RUNNING...")
    app.run_polling()


if __name__ == "__main__":
    main()
