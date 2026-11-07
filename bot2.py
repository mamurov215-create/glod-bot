from flask import Flask, request
import requests
import os
import threading
import time

app = Flask(__name__)

# TELEGRAM BOT SOZLAMALARI
TELEGRAM_BOT_TOKEN = "8839970219:AAHtbNDmsahAOr1Mw86EA7DF-AYFyr2Bh98"
TELEGRAM_CHAT_ID = "SIZNING_CHAT_IDINGIZ"  301467534

def telegramga_xabar_yuborish(matn):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": matn,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, json=data)
    except Exception as e:
        print(f"Telegramga xabar yuborishda xatolik: {e}")

# TradingView Webhook yo'li (Signal kelganda ishlaydi)
@app.route('/webhook', methods=['POST'])
def webhook():
    signal_data = request.data.decode('utf-8')
    if signal_data:
        xabar = f"🚨 **Yangi Signal Keldi!**\n\n{signal_data}"
        print(xabar)
        telegramga_xabar_yuborish(xabar)
        return "OK", 200
    return "Bad Request", 400

# Render porti ochiq turishi uchun asosiy sahifa
@app.route('/')
def home():
    return "Glod Bot Webhook Server Ishlamoqda!", 200

# Fon rejimidagi tsikl (Bot ishga tushishi bilan 1-signalni tekshirish uchun)
def background_bot_loop():
    print(">>> 15M INTERVAL BOT WITH AI & CHARTS STARTED <<<")
    try:
        telegramga_xabar_yuborish("🚀 Bot Render'da muvaffaqiyatli ishga tushdi va TradingView signallarini kutmoqda!")
    except Exception as e:
        print(f"Boshlang'ich xabarda xatolik: {e}")

    while True:
        time.sleep(900)  # Har 15 daqiqada kutish
        print("✅ 15 daqiqalik tsikl bajarilyapti...")

# Botni alohida thread'da ishga tushirish
threading.Thread(target=background_bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
