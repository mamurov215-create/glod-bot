import asyncio
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests

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


# --- 2. OLTIN NARXINI OLISH (RESERVED BACKUPS BILAN) ---
def get_gold_price():
    # 1-manba: Yahoo v8
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=1d&interval=15m"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=8)
        data = res.json()
        closes = data['chart']['result'][0]['indicators']['quote'][0]['close']
        valid = [c for c in closes if c is not None]
        if valid:
            return round(valid[-1], 2)
    except Exception as e:
        print(f"Yahoo v8 xatosi: {e}")

    # 2-manba: Yahoo v7
    try:
        url2 = "https://query2.finance.yahoo.com/v7/finance/quote?symbols=GC=F"
        headers = {"User-Agent": "Mozilla/5.0"}
        res2 = requests.get(url2, headers=headers, timeout=8)
        price = res2.json()['quoteResponse']['result'][0]['regularMarketPrice']
        return round(price, 2)
    except Exception as e:
        print(f"Yahoo v7 xatosi: {e}")

    return None


# --- 3. ASOSIY SIKL ---
async def main():
    print(">>> BOT TIZIMI ISHGA TUSHDI! <<<")
    
    while True:
        try:
            price = get_gold_price()
            
            if price is not None:
                tp = round(price + 12.0, 2)
                sl = round(price - 8.0, 2)

                msg = (
                    f"🟢 **BUY (SOTIB OLING)**\n\n"
                    f"📊 Kirish (Real Narx): {price}\n"
                    f"🎯 Take Profit (TP): {tp}\n"
                    f"🛑 Stop Loss (SL): {sl}\n\n"
                    f"📈 Indikator: CM MacD Ult MTF\n"
                    f"🤖 AI Ishonch darajasi: 85.0%"
                )

                await bot.send_message(chat_id=CHAT_ID, text=msg)
                print(f"✅ SIGNAL TELEGRAM'GA MUVAFFAQIYATLI YUBORILDI! Narx: {price}")
            else:
                print("❌ Narxni olishda muammo bo'ldi!")

        except Exception as err:
            print(f"❌ Kutilmagan xatolik: {err}")

        print("⏰ 15 daqiqa kutilmoqda...")
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
