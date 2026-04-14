#!/usr/bin/env python3
import os
import asyncio
import random
import logging
from datetime import datetime
import pytz
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==========================
# CONFIG
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
AUTHORIZED_USER_ID = int(os.getenv("AUTHORIZED_USER_ID", "0"))

# 2 CHANNEL (SUDAH DITAMBAHKAN)
CHANNELS = [
    "-1002605110502",
    "-1003056662193"
]

JKT = pytz.timezone("Asia/Jakarta")

# API harga GOLD (lebih stabil)
GOLD_API = "https://api.gold-api.com/price/XAUUSD"

# ==========================
# LOGGING
# ==========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("SIGNAL-BOT")

# ==========================
# AMBIL HARGA (ANTI ERROR)
# ==========================

def get_price():
    try:
        res = requests.get(GOLD_API, timeout=10)
        data = res.json()
        return float(data["price"])
    except Exception as e:
        logger.warning(f"Gagal ambil harga: {e}")
        return None

# ==========================
# GENERATE SIGNAL
# ==========================

def generate_signal(price):

    now = datetime.now(JKT).strftime("%Y-%m-%d %H:%M:%S")

    if not price:
        return f"""
🤖 AI MARKET SIGNAL

Time : {now} WIB

⚠️ Harga tidak tersedia saat ini
Silakan tunggu update berikutnya
"""

    direction = random.choice(["BUY", "SELL"])
    pip = 0.1

    if direction == "BUY":
        tp1 = round(price + 70*pip,2)
        tp2 = round(price + 100*pip,2)
        sl = round(price - 45*pip,2)
    else:
        tp1 = round(price - 70*pip,2)
        tp2 = round(price - 100*pip,2)
        sl = round(price + 45*pip,2)

    return f"""
🤖 AI MARKET SIGNAL

Instrument : XAU/USD (GOLD)
Time : {now} WIB

Direction : {direction}

Entry Price : {price}

Take Profit
TP1 : {tp1}
TP2 : {tp2}

Stop Loss
SL : {sl}

━━━━━━━━━━━━━━━
⚠️ Gunakan money management yang baik
"""

# ==========================
# KIRIM SIGNAL
# ==========================

async def send_signal(app):

    price = get_price()
    msg = generate_signal(price)

    for ch in CHANNELS:
        try:
            await app.bot.send_message(chat_id=ch, text=msg)
            logger.info(f"Signal terkirim ke {ch}")
        except Exception as e:
            logger.error(f"Gagal kirim ke {ch}: {e}")

# ==========================
# SCHEDULER FIX (ANTI MISS)
# ==========================

async def scheduler(app):

    logger.info("Scheduler aktif")

    last_sent_hour = -1

    while True:

        now = datetime.now(JKT)

        # Senin - Jumat
        if now.weekday() < 5:

            # Jam trading
            if 8 <= now.hour <= 21:

                # Kirim sekali per jam
                if now.minute == 0 and now.hour != last_sent_hour:

                    logger.info(f"Kirim signal jam {now.hour}:00")

                    await send_signal(app)

                    last_sent_hour = now.hour

        await asyncio.sleep(15)

# ==========================
# COMMAND
# ==========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT SIGNAL AKTIF\n\n"
        "/harga → cek harga\n"
        "/signal → kirim manual (admin)"
    )

async def harga(update: Update, context: ContextTypes.DEFAULT_TYPE):

    price = get_price()

    if not price:
        return await update.message.reply_text("Harga tidak tersedia")

    await update.message.reply_text(f"XAUUSD : {price}")

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != AUTHORIZED_USER_ID:
        return await update.message.reply_text("Tidak diizinkan")

    await send_signal(context.application)
    await update.message.reply_text("Signal berhasil dikirim")

# ==========================
# MAIN
# ==========================

def main():

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("harga", harga))
    app.add_handler(CommandHandler("signal", signal))

    async def post_init(application):
        application.create_task(scheduler(application))
        logger.info("Scheduler berjalan")

    app.post_init = post_init

    logger.info("BOT START RUNNING")

    app.run_polling()

if __name__ == "__main__":
    main()
