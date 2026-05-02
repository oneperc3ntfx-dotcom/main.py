import os
import logging
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

# ================= TEMP DATA =================
user_data = {}


# ================= SAFE USER =================
def get_user_id(update: Update):
    if not update or not update.effective_user:
        return None
    return update.effective_user.id


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = get_user_id(update)
        if not user_id:
            return

        keyboard = [
            [InlineKeyboardButton("🤝 Join Gratis / Mitra", callback_data="menu_join")]
        ]

        await update.message.reply_text(
            "👋 Selamat datang di ONE PERCENT FX\n\nSilahkan pilih menu di bawah untuk melanjutkan:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Start error: {e}")


# ================= MENU JOIN =================
async def menu_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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

    except Exception as e:
        logger.error(f"Menu join error: {e}")


# ================= BROKER SELECT =================
async def broker_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        broker = query.data.split("_")[1]

        user_data[user_id] = {"broker": broker}

        await query.message.reply_text(
            f"""📌 UNTUK PINDAH MITRA

Silahkan klik link grup di bawah ini:
🔗 {GROUPS[broker]}

📢 Di dalam grup tersebut sudah tersedia panduan lengkap yang wajib kamu ikuti step-by-step.

⚠️ Pastikan kamu membaca semua instruksi dengan benar sebelum lanjut ke tahap berikutnya.

📸 Setelah selesai, kirim screenshot profil akun broker atau MT5 kamu, pastikan terlihat saldo dan ID akun dengan jelas."""
        )

    except Exception as e:
        logger.error(f"Broker error: {e}")


# ================= PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = get_user_id(update)
        if not user_id or not update.message:
            return

        if user_id not in user_data:
            return

        user_data[user_id]["photo"] = update.message.photo[-1].file_id

        await update.message.reply_text(
            """✍️ Langkah terakhir, silahkan kirim data berikut:

ID WALLET:
USER ID TELEGRAM:
BROKER YANG DIGUNAKAN:"""
        )

    except Exception as e:
        logger.error(f"Photo error: {e}")


# ================= TEXT FORM =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = get_user_id(update)
        if not user_id or not update.message:
            return

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

        await update.message.reply_text("📨 Data kamu sudah dikirim ke tim verifikasi.")

    except Exception as e:
        logger.error(f"Text error: {e}")


# ================= ADMIN ACTION =================
async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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

            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text=f"""🎉 REGISTRASI BERHASIL DISETUJUI

📌 Silahkan lanjutkan ke broker kamu:
{GROUPS[broker]}

🚀 Pastikan mengikuti semua instruksi yang diberikan."""
                )

                invite = await context.bot.create_chat_invite_link(
                    chat_id=MAIN_GROUP,
                    member_limit=1
                )

                await context.bot.send_message(
                    chat_id=uid,
                    text=f"""🔥 SELAMAT DATANG DI ONE PERCENT FX

👉 GRUP UTAMA:
{invite.invite_link}

⚡ Selamat bergabung, semoga bisa grow bersama kami!"""
                )

            except Exception as e:
                logger.error(f"Approve error: {e}")

            await query.message.edit_text("✅ USER APPROVED")


        # ================= REJECT =================
        else:

            try:
                await context.bot.send_message(
                    chat_id=uid,
                    text="""❌ Mohon maaf, registrasi kamu belum berhasil.

Silahkan hubungi admin:
@ADMOnePercentsFX"""
                )
            except:
                pass

            await query.message.edit_text("❌ USER REJECTED")

    except Exception as e:
        logger.error(f"Admin error: {e}")


# ================= ROUTER =================
async def router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = update.callback_query.data

        if data == "menu_join":
            return await menu_join(update, context)

        if data.startswith("broker_"):
            return await broker_select(update, context)

        if data.startswith("approve") or data.startswith("reject"):
            return await admin_action(update, context)

    except Exception as e:
        logger.error(f"Router error: {e}")


# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(router))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("BOT RUNNING - PREMIUM MODE")
    app.run_polling()


if __name__ == "__main__":
    main()
