
import asyncio
from telegram import Bot
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.ensemble import RandomForestClassifier

# --- 1. TELEGRAM SOZLAMALARI ---
TELEGRAM_TOKEN = "8839970219:AAGnkSAVlkVCPWXZY0aZZ9qf7PRDoJUsGvU"
CHAT_ID = "301467534"

bot = Bot(token=TELEGRAM_TOKEN)

# --- 2. INTERNETDAN REAL NARXLARNI OLISH ---
def get_real_market_data(ticker="GC=F", interval="15m", period="5d"):
    """yfinance orqali Oltin (GC=F) ning real vaqt narxlarini yuklash"""
    data = yf.download(tickers=ticker, period=period, interval=interval, progress=False)
    
    if data.empty:
        return None
        
    df = pd.DataFrame()
    df['close'] = data['Close'].values.flatten()
    df['high'] = data['High'].values.flatten()
    df['low'] = data['Low'].values.flatten()
    return df.dropna()

# --- 3. CHRISMOODY MACD INDIKATORI ---
def add_custom_macd(df, fast=12, slow=26, signal=9):
    fast_ema = df['close'].ewm(span=fast, adjust=False).mean()
    slow_ema = df['close'].ewm(span=slow, adjust=False).mean()
    
    df['macd'] = fast_ema - slow_ema
    df['macd_signal'] = df['macd'].rolling(window=signal).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    df['macd_above'] = df['macd'] >= df['macd_signal']
    df['macd_cross'] = 0
    df.loc[(df['macd_above']) & (~df['macd_above'].shift(1).fillna(False)), 'macd_cross'] = 1
    df.loc[(~df['macd_above']) & (df['macd_above'].shift(1).fillna(True)), 'macd_cross'] = -1

    hist = df['macd_hist']
    hist_prev = df['macd_hist'].shift(1)
    
    df['hist_state'] = 0
    df.loc[(hist > 0) & (hist > hist_prev), 'hist_state'] = 2   # Aqua
    df.loc[(hist > 0) & (hist < hist_prev), 'hist_state'] = 1   # Blue
    df.loc[(hist <= 0) & (hist < hist_prev), 'hist_state'] = -2 # Red
    df.loc[(hist <= 0) & (hist > hist_prev), 'hist_state'] = -1 # Maroon
    
    return df

def prepare_data(df):
    df['Returns'] = df['close'].pct_change()
    df = add_custom_macd(df)
    
    # ATR Volatillik (SL/TP uchun)
    df['High-Low'] = df['high'] - df['low']
    df['ATR'] = df['High-Low'].rolling(14).mean()
    
    df['Target'] = np.where(df['close'].shift(-1) > df['close'], 1, 0)
    return df.dropna()

# --- 4. AI MODELI ---
def train_ai_model(df):
    features = ['Returns', 'macd', 'macd_signal', 'macd_hist', 'macd_cross', 'hist_state']
    X = df[features]
    y = df['Target']
    
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model, features

# --- 5. TELEGRAM XABARI ---
async def send_signal(message):
    await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

# --- 6. ASOSIY BOSHQARUV SIKLI ---
async def run_trading_bot():
    print("AI Trading Bot ishlamoqda, har 15 minutda avto-signal yuboriladi...")
    
    while True:
        try:
            print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] Narxlar tekshirilmoqda...")
            df_raw = get_real_market_data(ticker="GC=F", interval="15m", period="5d")
            
            if df_raw is not None and len(df_raw) >= 50:
                df_prepared = prepare_data(df_raw)
                model, features = train_ai_model(df_prepared)
                
                last_row = df_prepared.iloc[-1]
                last_features = df_prepared[features].iloc[-1:].values
                
                current_price = round(float(last_row['close']), 2)
                atr = float(last_row['ATR']) if not np.isnan(last_row['ATR']) else 5.0
                
                prediction = model.predict(last_features)[0]
                probability = model.predict_proba(last_features)[0].max()
                
                # SL va TP hisoblash
                sl_pips = round(atr * 1.5, 2)
                tp_pips = round(atr * 3.0, 2)
                
                if prediction == 1:
                    entry_type = "🟢 **BUY (SOTIB OLING)**"
                    sl = round(current_price - sl_pips, 2)
                    tp = round(current_price + tp_pips, 2)
                else:
                    entry_type = "🔴 **SELL (SOTING)**"
                    sl = round(current_price + sl_pips, 2)
                    tp = round(current_price - tp_pips, 2)
                    
                msg = (
                    f"{entry_type}\n\n"
                    f"📊 **Kirish (Real Narx):** `{current_price}`\n"
                    f"🎯 **Take Profit (TP):** `{tp}`\n"
                    f"🛑 **Stop Loss (SL):** `{sl}`\n\n"
                    f"📈 **Indikator:** `CM MacD Ult MTF`\n"
                    f"🤖 **AI Ishonch darajasi:** `{probability*100:.1f}%`"
                )
                
                await send_signal(msg)
                print(f"[{pd.Timestamp.now().strftime('%H:%M:%S')}] Signal Telegram'ga yuborildi!")
            else:
                print("Bozor ma'lumotlari olinmadi, qayta urinib ko'riladi.")
            
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")
            
        print("Keyingi signalgacha 15 minut kutilmoqda...\n")
        await asyncio.sleep(900)

if __name__ == "__main__":
    asyncio.run(run_trading_bot())
