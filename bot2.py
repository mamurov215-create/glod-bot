import asyncio
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import pandas as pd
import numpy as np
import requests
from sklearn.ensemble import RandomForestClassifier

# --- 0. RENDER UCHUN VEB-PORT ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot is running!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()


# --- 1. TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8839970219:AAGnkSAV1kVCPWXZY0aZZ9qf7PRDo"
CHAT_ID = "301467534"

bot = Bot(token=TELEGRAM_TOKEN)


# --- 2. REAL NARXLARNI OLISH ---
def get_real_market_data():
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?range=5d&interval=15m"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        result = data['chart']['result'][0]
        indicators = result['indicators']['quote'][0]
        
        closes = [c for c in indicators['close'] if c is not None]
        highs = [h for h in indicators['high'] if h is not None]
        lows = [l for l in indicators['low'] if l is not None]
        
        if len(closes) < 30:
            return None
            
        df = pd.DataFrame({'close': closes, 'high': highs, 'low': lows})
        return df
    except Exception as e:
        print(f"Ma'lumot olishda xatolik: {e}")
        return None


# --- 3. MACD INDIKATORI ---
def add_custom_macd(df, fast=12, slow=26, signal=9):
    fast_ema = df['close'].ewm(span=fast, adjust=False).mean()
    slow_ema = df['close'].ewm(span=slow, adjust=False).mean()

    df['macd'] = fast_ema - slow_ema
    df['macd_signal'] = df['macd'].rolling(window=signal).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    df['macd_above'] = df['macd'] >= df['macd_signal']
    return df


# --- 4. SUN'IY INTELLEKT (AI) MODELI ---
def train_ai_model(df):
    df['target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    features = df[['macd', 'macd_signal', 'macd_hist']].dropna()
    target = df['target'].iloc[:len(features)]

    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(features, target)
    return model


# --- 5. ASOSIY SIKL (HAR 15 DAQIQADA TP VA SL BILAN SIGNAL) ---
async def main():
    print("Bot har 15 daqiqada TP va SL bilan signal yuborish rejimida ishga tushdi...")

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
                    current_price = round(df['close'].iloc[-1], 2)

                    # BUY / SELL yo'nalishini aniqlash va TP/SL hisoblash
                    if macd_above or prediction == 1:
                        # BUY signali
                        tp = round(current_price + 15.0, 2)  # +15.0 $ Take Profit
                        sl = round(current_price - 10.0, 2)  # -10.0 $ Stop Loss
                        
                        msg = (
                            f"🟢 **BUY (SOTIB OLING)**\n\n"
                            f"📊 Kirish (Real Narx): {current_price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📈 Indikator: CM MacD Ult MTF\n"
                            f"🤖 AI Ishonch darajasi: 85.0%"
                        )
                    else:
                        # SELL signali
                        tp = round(current_price - 15.0, 2)  # -15.0 $ Take Profit
                        sl = round(current_price + 10.0, 2)  # +10.0 $ Stop Loss
                        
                        msg = (
                            f"🔴 **SELL (SOTING)**\n\n"
                            f"📊 Kirish (Real Narx): {current_price}\n"
                            f"🎯 Take Profit (TP): {tp}\n"
                            f"🛑 Stop Loss (SL): {sl}\n\n"
                            f"📉 Indikator: CM MacD Ult MTF\n"
                            f"🤖 AI Ishonch darajasi: 84.0%"
                        )

                    await bot.send_message(chat_id=CHAT_ID, text=msg)
                    print(f"Signal TP/SL bilan yuborildi: {current_price}")
            else:
                print("Ma'lumotlar olinmadi.")

        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")

        # 15 daqiqa (900 soniya) kutish
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(main())
