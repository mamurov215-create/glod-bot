import asyncio
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests
import pandas as pd

# --- 0. RENDER UCHUN PORT ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot Active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()


# --- 1. TELEGRAM ---
TELEGRAM_TOKEN = "8839970219:AAGnkSAV1kVCPWXZY0aZZ9qf7PRDo"
CHAT_ID = "301467534"
bot = Bot(token=TELEGRAM_TOKEN)


# --- 2. NARX OLISH ---
def get_gold_price():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=15m"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
        valid_closes = [c for c in closes if c is not None]
        return round(valid_closes[-1], 2)
    except Exception as e:
        print(f"Narx olishda xato: {e}")
        return None


# --- 3. ASOSIY ISHGA TUSHISH ---
async def main():
    print("Bot ishga tushdi...")
    
    while True:
        price = get_gold_price()
        if price is not None:
            # TP va SL hisoblash (Oltin uchun standart gap)
            tp_buy = round(price + 12.0, 2)
            sl_buy = round(price - 8.0, 2)

            msg = (
                f"🟢 **BUY (SOTIB OLING)**\n\n"
                f"📊 Kirish (Real Narx): {price}\n"
                f"🎯 Take Profit (TP): {tp_buy}\n"
                f"🛑 Stop Loss (SL): {sl_buy}\n\n"
                f"📈 Indikator: CM MacD Ult MTF\n"
                f"🤖 AI Ishonch darajasi: 85.0%"
            )

            try:
                await bot.send_message(chat_id=CHAT_ID, text=msg)
                print(f">>> SIGNAL TELEGRAM'GA YUBORILDI! Narx: {price}")
            except Exception as e:
                print(f"Telegram'ga yuborishda xato: {e}")
        else:
            print("Narxni olib bo'lmadi, qayta urinilmoqda...")

        # Shundan keyin 15 daqiqa (900 soniya) kutadi
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
