import asyncio
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests
import pandas as pd

sys.stdout.reconfigure(line_buffering=True)

# --- 0. RENDER PORT SERVERI ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Trend-Filtered 15M Bot Active")

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


# --- 2. 15-DAQIQALIK TAHLIL VA TREND FILTRI ---
def analyze_market_15m():
    # 15 daqiqalik (15m) taymfreym kotirovkasi
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=5d&interval=15m"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        quote = data['chart']['result'][0]['indicators']['quote'][0]
        
        df = pd.DataFrame({
            'close': quote['close'],
            'high': quote['high'],
            'low': quote['low']
        }).dropna()

        if len(df) < 100:
            return None

        # 1. Global Trend Filtri (EMA 200)
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # 2. Impuls Indicator (MACD)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # 3. RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        last_price = round(curr['close'], 2)
        rsi_val = round(curr['rsi'], 1)

        # STRICT TREND FILTERING (Trendga qarshi signal YUQ):
        
        # BUY Shartlari:
        # - Narx EMA 200 dan ALBATTA yuqorida bo'lishi shart (Up-trend)
        # - MACD signal liniyasini pastdan yuqoriga kesib o'tgan bo'lishi shart
        # - RSI 35 va 60 orasida (Haddan tashqari sotib olinmagan)
        buy_signal = (
            (curr['close'] > curr['ema_200']) and
            (prev['macd'] <= prev['macd_signal']) and (curr['macd'] > curr['macd_signal']) and
            (35 < curr['rsi'] < 60)
        )

        # SELL Shartlari:
        # - Narx EMA 200 dan ALBATTA pastda bo'lishi shart (Down-trend)
        # - MACD signal liniyasini yuqoridan pastga kesib o'tgan bo'lishi shart
        # - RSI 40 va 65 orasida
        sell_signal = (
            (curr['close'] < curr['ema_200']) and
            (prev['macd'] >= prev['macd_signal']) and (curr['macd'] < curr['macd_signal']) and
            (40 < curr['rsi'] < 65)
        )

        # Oltin uchun realizmga mos TP (4$) va SL (3$) masofasi
        if buy_signal:
            tp = round(last_price + 4.0, 2)
            sl = round(last_price - 3.0, 2)
            return "BUY", last_price, tp, sl, rsi_val

        elif sell_signal:
            tp = round(last_price - 4.0, 2)
            sl = round(last_price + 3.0, 2)
            return "SELL", last_price, tp, sl, rsi_val

        return "HOLD", last_price, 0, 0, rsi_val

    except Exception as e:
        print(f"Tahlil xatosi: {e}", flush=True)
        return None


# --- 3. ASOSIY SIKL ---
async def main():
    print(">>> 15M TREND-FILTERED GOLD BOT ISHGA TUSHDI <<<", flush=True)

    while True:
        try:
            weekday = datetime.utcnow().weekday()

            if weekday in [5, 6]:
                print("🛑 Bugun dam olish kuni (bozor yopiq).", flush=True)
            else:
                res = analyze_market_15m()
                if res is not None:
                    signal_type, price, tp, sl, rsi_val = res

                    if signal_type == "BUY":
                        msg = (
                            f"🟢 **KUCHLI BUY SIGNAL (15M)**\n\n"
                            f"📊 Kirish narxi: {price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📈 Trend: Ko'tarilish (EMA200 yuqorida)\n"
                            f"📐 RSI: {rsi_val}"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        print(f"✅ BUY SIGNAL YUBORILDI! Narx: {price}", flush=True)

                    elif signal_type == "SELL":
                        msg = (
                            f"🔴 **KUCHLI SELL SIGNAL (15M)**\n\n"
                            f"📊 Kirish narxi: {price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📉 Trend: Tushish (EMA200 pastda)\n"
                            f"📐 RSI: {rsi_val}"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        print(f"✅ SELL SIGNAL YUBORILDI! Narx: {price}", flush=True)

                    else:
                        print(f"ℹ️ Neytral holat (Narx: {price}, RSI: {rsi_val}). Shartlar mos kelmadi.", flush=True)

        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}", flush=True)

        # Har 15 daqiqada (900 soniya) tekshiradi va signal beradi
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
