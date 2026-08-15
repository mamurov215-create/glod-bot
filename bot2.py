import asyncio
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests
import pandas as pd
import numpy as np

sys.stdout.reconfigure(line_buffering=True)

# --- 0. RENDER PORT SERVERI ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Strategy Bot Active")

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


# --- 2. MULTI-INDIKATOR TAHLIL MOTOR ---
def analyze_market():
    url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=7d&interval=15m"
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

        # 1. TREND INDIKATORI: EMA (50 va 200)
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()

        # 2. IMPULS: MACD (12, 26, 9)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        # 3. OSMON/TUB FILTERI: RSI (14)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # 4. VOLATILLIK VA RISK: ATR (14)
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift())
        df['tr2'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()

        # So'nggi qiymatlar
        curr = df.iloc[-1]
        prev = df.iloc[-2]

        last_price = round(curr['close'], 2)
        atr_val = round(curr['atr'], 2)
        rsi_val = round(curr['rsi'], 1)

        # MANTIQIY SHARTLAR (Confluence strategy)
        
        # BUY Shartlari:
        # - Narx 200 EMA dan yuqorida (Global trend ko'tarilishda)
        # - MACD pastdan yuqoriga kessin
        # - RSI 65 dan kichik (Xaddan tashqari qimmat emas)
        buy_signal = (
            (curr['close'] > curr['ema_200']) and
            (prev['macd'] <= prev['macd_signal']) and (curr['macd'] > curr['macd_signal']) and
            (curr['rsi'] < 65)
        )

        # SELL Shartlari:
        # - Narx 200 EMA dan pastda (Global trend tushishda)
        # - MACD yuqoridan pastga kessin
        # - RSI 35 dan baland (Xaddan tashqari arzon emas)
        sell_signal = (
            (curr['close'] < curr['ema_200']) and
            (prev['macd'] >= prev['macd_signal']) and (curr['macd'] < curr['macd_signal']) and
            (curr['rsi'] > 35)
        )

        if buy_signal:
            tp = round(last_price + (atr_val * 2.0), 2)  # Risk:Reward = 1:2
            sl = round(last_price - (atr_val * 1.0), 2)
            return "BUY", last_price, tp, sl, rsi_val, atr_val

        elif sell_signal:
            tp = round(last_price - (atr_val * 2.0), 2)
            sl = round(last_price + (atr_val * 1.0), 2)
            return "SELL", last_price, tp, sl, rsi_val, atr_val

        return "HOLD", last_price, 0, 0, rsi_val, atr_val

    except Exception as e:
        print(f"Tahlil xatosi: {e}", flush=True)
        return None


# --- 3. ASOSIY SIKL ---
async def main():
    print(">>> STRATEGIK BOTA ISHGA TUSHDI <<<", flush=True)

    while True:
        try:
            weekday = datetime.utcnow().weekday()

            if weekday in [5, 6]:
                print("🛑 Bugun dam olish kuni (bozor yopiq).", flush=True)
            else:
                res = analyze_market()
                if res is not None:
                    signal_type, price, tp, sl, rsi_val, atr_val = res

                    if signal_type == "BUY":
                        msg = (
                            f"🟢 **KUCHLI BUY SIGNAL**\n\n"
                            f"📊 Kirish narxi: {price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📐 Risk/Reward: 1:2 (ATR: {atr_val})\n"
                            f"📈 Indikatorlar: EMA200 + MACD Cross + RSI ({rsi_val})"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        print(f"✅ BUY SIGNAL YUBORILDI! Narx: {price}", flush=True)

                    elif signal_type == "SELL":
                        msg = (
                            f"🔴 **KUCHLI SELL SIGNAL**\n\n"
                            f"📊 Kirish narxi: {price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📐 Risk/Reward: 1:2 (ATR: {atr_val})\n"
                            f"📉 Indikatorlar: EMA200 + MACD Cross + RSI ({rsi_val})"
                        )
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        print(f"✅ SELL SIGNAL YUBORILDI! Narx: {price}", flush=True)

                    else:
                        print(f"ℹ️ Neytral holat (Narx: {price}, RSI: {rsi_val}). Shartlar bajarilmadi.", flush=True)

        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}", flush=True)

        # Har 15 daqiqada tekshiradi
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
