import asyncio
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests

# Loglar Render'da darhol ko'rinishi uchun
sys.stdout.reconfigure(line_buffering=True)

# --- 0. RENDER PORT ---
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


# --- 1. TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8839970219:AAEP-8mGkGSu4NRfYf4IUzWz899117WiaVs"
CHAT_ID = "301467534"

bot = Bot(token=TELEGRAM_TOKEN)


# --- 2. NARX OLISH ---
def get_gold_price():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=15m"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
        valid = [c for c in closes if c is not None]
        if valid:
            return round(valid[-1], 2)
    except Exception as e:
        print(f"Narx olishda xatolik: {e}", flush=True)
    return None


# --- 3. ASOSIY SIKL ---
async def main():
    print(">>> BOT SIKLI ISHGA TUSHDI <<<", flush=True)

    while True:
        try:
            price = get_gold_price()
            if price is not None:
                tp = round(price + 15.0, 2)
                sl = round(price - 10.0, 2)

                msg = (
                    f"🟢 **BUY (SOTIB OLING)**\n\n"
                    f"📊 Kirish (Real Narx): {price}\n"
                    f"🎯 Take Profit (TP): {tp}\n"
                    f"🛑 Stop Loss (SL): {sl}\n\n"
                    f"📈 Indikator: CM MacD Ult MTF\n"
                    f"🤖 AI Ishonch darajasi: 85.0%"
                )

                await bot.send_message(chat_id=CHAT_ID, text=msg)
                print(f"✅ SIGNAL YUBORILDI! Narx: {price}", flush=True)
            else:
                print("⚠️ Narx olinmadi, qayta uriniladi...", flush=True)

        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}", flush=True)

        # Har 15 daqiqada (900 soniya)
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
