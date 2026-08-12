import asyncio
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier

# --- 0. RENDER UCHUN KICHIK VEB-PORT (Port binding xatosini yo'qotadi) ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# Veb serverni alohida oqimda ishga tushirish
threading.Thread(target=run_web_server, daemon=True).start()


# --- 1. TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8839970219:AAGnkSAV1kVCPWXZY0aZZ9qf7PRDo" # Tokeningiz
CHAT_ID = "301467534"                                     # Chat ID

bot = Bot(token=TELEGRAM_TOKEN)


# --- 2. INTERNETDAN REAL NARXLARNI OLISH ---
def get_real_market_data(ticker="GC=F", interval="15m", period="5d"):
    """yfinance orqali Oltin (GC=F) ning real vaqt narxlarini yuklash"""
    try:
        data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
        if data.empty:
            return None

        df = pd.DataFrame()
        df['close'] = data['Close'].values.flatten()
        df['high'] = data['High'].values.flatten()
        df['low'] = data['Low'].values.flatten()
        return df.dropna()
    except Exception as e:
        print(f"Ma'lumot olishda xatolik: {e}")
        return None


# --- 3. CHRISMOODY MACD INDIKATORI ---
def add_custom_macd(df, fast=12, slow=26, signal=9):
    fast_ema = df['close'].ewm(span=fast, adjust=False).mean()
    slow_ema = df['close'].ewm(span=slow, adjust=False).mean()

    df['macd'] = fast_ema - slow_ema
    df['macd_signal'] = df['macd'].rolling(window=signal).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    df['macd_above'] = df['macd'] >= df['macd_signal']
    return df


# --- 4. SUN'IY INTELLEKT (AI) MODELINI TAYYORLASH ---
def train_ai_model(df):
    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    features = df[['macd', 'macd_signal', 'macd_hist']].dropna()
    target = df['target'].iloc[:len(features)]

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(features, target)
    return model


# --- 5. ASOSIY BOOT/ISHLASH SIKLI ---
async def main():
    print("Bot ishga tushdi...")
    last_signal = None

    while True:
        try:
            df = get_real_market_data()
            if df is not None and len(df) > 30:
                df = add_custom_macd(df)
                model = train_ai_model(df)

                latest_features = df[['macd', 'macd_signal', 'macd_hist']].iloc[-1:].dropna()
                if not latest_features.empty:
                    prediction = model.predict(latest_features)[0]
                    macd_above = df['macd_above'].iloc[-1]

                    current_price = df['close'].iloc[-1]

                    # BUY Signal
                    if macd_above and prediction == 1 and last_signal != "BUY":
                        msg = f"🟢 **BUY SIGNAL (OLTIN)**\nNarx: {current_price}\nMACD va AI mos keldi!"
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        last_signal = "BUY"

                    # SELL Signal
                    elif not macd_above and prediction == 0 and last_signal != "SELL":
                        msg = f"🔴 **SELL SIGNAL (OLTIN)**\nNarx: {current_price}\nMACD va AI mos keldi!"
                        await bot.send_message(chat_id=CHAT_ID, text=msg)
                        last_signal = "SELL"

        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

        # Yahoo Finance bloklamasligi va cheklovga tushmaslik uchun 60 soniya kutish
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
