import asyncio
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Bot
import requests
import pandas as pd
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.stdout.reconfigure(line_buffering=True)

# --- 0. OPENAI CLIENT ---
# Render Environment'dan kalitni xavfsiz o'qiydi
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def get_ai_gold_analysis(signal_type, price, rsi):
    try:
        prompt = f"Oltin (XAUUSD) bozorining 15 daqiqalik holati: Status - {signal_type}, Narx: {price}, RSI: {rsi}. Shu holat bo'yicha o'zbek tilida qisqacha professional tahlil va bashorat yozib ber."
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Siz tajribali oltin (XAUUSD) tahlilchisisiz. Har 15 daqiqalik holat bo'yicha o'zbek tilida qisqa va aniq maslahat berasiz."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI tahlil xatosi: {e}"

# --- Rasm chizish funksiyasi ---
def draw_chart(df, signal_type, price):
    plt.figure(figsize=(10, 5))
    plt.plot(df['close'].values[-50:], label='Narx (Close)', color='blue', linewidth=2)
    plt.plot(df['ema_200'].values[-50:], label='EMA 200', color='orange', linestyle='--')
    plt.title(f"Gold (XAUUSD) 15M - Status: {signal_type} | Narx: {price}")
    plt.xlabel("So'nggi 15m свечалар")
    plt.ylabel("Narx ($)")
    plt.legend()
    plt.grid(True)
    
    chart_path = "gold_chart.png"
    plt.savefig(chart_path)
    plt.close()
    return chart_path

# --- 1. RENDER PORT SERVERI ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Gold Bot Every 15M Active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()


# --- 2. TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8839970219:AAEP-8mGkGSu4NRfYf4IUzWz899117WiaVs"
CHAT_ID = "301467534"
bot = Bot(token=TELEGRAM_TOKEN)


# --- 3. 15-DAQIQALIK TAHLIL ---
def analyze_market_15m():
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
            return None, None, None, None

        df['ema_200'] = df['close'].ewm(span=200, adjust=False).mean()
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()

        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        last_price = round(curr['close'], 2)
        rsi_val = round(curr['rsi'], 1)

        buy_signal = (
            (curr['close'] > curr['ema_200']) and
            (prev['macd'] <= prev['macd_signal']) and (curr['macd'] > curr['macd_signal']) and
            (35 < curr['rsi'] < 60)
        )

        sell_signal = (
            (curr['close'] < curr['ema_200']) and
            (prev['macd'] >= prev['macd_signal']) and (curr['macd'] < curr['macd_signal']) and
            (40 < curr['rsi'] < 65)
        )

        if buy_signal:
            return "BUY", last_price, rsi_val, df
        elif sell_signal:
            return "SELL", last_price, rsi_val, df
        else:
            return "HOLD", last_price, rsi_val, df

    except Exception as e:
        print(f"Tahlil xatosi: {e}", flush=True)
        return None, None, None, None


# --- 4. ASOSIY SIKL ---
async def main():
    print(">>> 15M INTERVAL BOT WITH AI & CHARTS STARTED <<<", flush=True)

    while: # <--- OOPS, while True bo'lishi kerak, quyida to'g'irlandi:
