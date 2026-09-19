import os
import time
import json
import logging
import threading
from datetime import datetime, timezone

import pandas as pd
import requests
import yfinance as yf
from flask import Flask, jsonify
from groq import Groq

# ---------------- SOZLAMALAR ----------------
def env(nom):
    """Environment o'zgaruvchisini o'qiydi, bo'sh joylarni olib tashlaydi."""
    return (os.environ.get(nom) or "").strip()


GROQ_API_KEY = env("GROQ_API_KEY")
TELEGRAM_TOKEN = env("TELEGRAM_TOKEN")
CHAT_ID = env("CHAT_ID")

SYMBOL = "GC=F"          # oltin fyucherslari (XAUUSD ga yaqin narx)
INTERVAL_SEC = 900       # 15 daqiqa
MODEL = "llama-3.3-70b-versatile"
MIN_ISHONCH = 6          # shundan past ishonchli signal yuborilmaydi (1-10)
SL_ATR = 1.5             # stop-loss = 1.5 * ATR
TP_ATR = 3.0             # take-profit = 3 * ATR (risk:foyda = 1:2)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
log = logging.getLogger("goldbot")

app = Flask(__name__)
groq_client = None

holat = {"oxirgi_signal": None, "oxirgi_vaqt": None, "oxirgi_xato": None}


def yetishmayotganlar():
    return [n for n, v in [("GROQ_API_KEY", GROQ_API_KEY),
                           ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
                           ("CHAT_ID", CHAT_ID)] if not v]


# ---------------- VEB-SERVER (Render + UptimeRobot) ----------------
@app.route("/")
def home():
    return "Gold 15M AI Bot is running!"


@app.route("/status")
def status():
    return jsonify({**holat, "yetishmayotgan_kalitlar": yetishmayotganlar()})


def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ---------------- MA'LUMOT VA INDIKATORLAR ----------------
def malumot_ol():
    """15 daqiqalik shamlarni oladi va indikatorlarni hisoblaydi.
    Bozor yopiq bo'lsa None qaytaradi."""
    df = yf.download(SYMBOL, period="7d", interval="15m",
                     progress=False, auto_adjust=False)
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    if df.empty:
        return None

    # Bozor yopiqligini tekshirish (oxirgi sham 45 daqiqadan eski bo'lsa)
    oxirgi = df.index[-1]
    oxirgi = oxirgi.tz_localize("UTC") if oxirgi.tzinfo is None else oxirgi.tz_convert("UTC")
    if pd.Timestamp.now(tz="UTC") - oxirgi > pd.Timedelta(minutes=45):
        return None

    # Hozir shakllanayotgan (yopilmagan) shamni tashlab yuboramiz
    df = df.iloc[:-1]
    if len(df) < 60:
        return None

    close, high, low = df["Close"], df["High"], df["Low"]

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    # RSI (Wilder usuli)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss)

    # MACD
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    macd_hist = macd - macd_signal

    # ATR (haqiqiy diapazon, Wilder)
    pc = close.shift(1)
    tr = pd.concat([high - low, (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()

    return {
        "narx": round(float(close.iloc[-1]), 2),
        "ema20": round(float(ema20.iloc[-1]), 2),
        "ema50": round(float(ema50.iloc[-1]), 2),
        "rsi": round(float(rsi.iloc[-1]), 1),
        "macd_hist": round(float(macd_hist.iloc[-1]), 3),
        "macd_hist_oldingi": round(float(macd_hist.iloc[-2]), 3),
        "atr": round(float(atr.iloc[-1]), 2),
        "oxirgi_5_yopilish": [round(float(x), 2) for x in close.iloc[-5:]],
        "1_soat_ozgarish": round(float(close.iloc[-1] - close.iloc[-5]), 2),
    }


# ---------------- SUN'IY INTELLEKT ----------------
def ai_tahlil_qil(m):
    """AI faqat yo'nalish va izoh beradi. Raqamlarni (SL/TP) kod hisoblaydi."""
    global groq_client
    if groq_client is None:
        groq_client = Groq(api_key=GROQ_API_KEY)

    prompt = (
        "Oltin (XAUUSD) 15 daqiqalik grafik ma'lumoti:\n"
        f"{json.dumps(m, ensure_ascii=False)}\n\n"
        "Trend (EMA20/EMA50), momentum (RSI, MACD gistogrammasi) va "
        "volatillikni hisobga olib yo'nalishni aniqla.\n"
        "Faqat JSON qaytar:\n"
        '{"signal": "BUY" | "SELL" | "KUTISH", '
        '"ishonch": 1-10 oralig\'ida butun son, '
        '"sabab": "2-3 gaplik qisqa izoh o\'zbek tilida"}\n'
        "Belgilar bir-biriga zid bo'lsa yoki aniq bo'lmasa KUTISH de."
    )
    r = groq_client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system",
             "content": "Siz ehtiyotkor texnik tahlilchisiz. Faqat JSON javob bering."},
            {"role": "user", "content": prompt},
        ],
    )
    data = json.loads(r.choices[0].message.content)

    signal = str(data.get("signal", "KUTISH")).upper().strip()
    if signal not in ("BUY", "SELL", "KUTISH"):
        signal = "KUTISH"
    try:
        ishonch = max(1, min(10, int(data.get("ishonch", 1))))
    except (TypeError, ValueError):
        ishonch = 1
    return {"signal": signal, "ishonch": ishonch, "sabab": str(data.get("sabab", ""))[:400]}


def daraja_hisobla(signal, narx, atr):
    """SL va TP ni ATR asosida kod hisoblaydi."""
    if signal == "BUY":
        return round(narx - SL_ATR * atr, 2), round(narx + TP_ATR * atr, 2)
    return round(narx + SL_ATR * atr, 2), round(narx - TP_ATR * atr, 2)


# ---------------- TELEGRAM ----------------
def telegramga_yubor(matn):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for _ in range(3):
        try:
            r = requests.post(url, data={"chat_id": CHAT_ID, "text": matn}, timeout=20)
            if r.ok:
                return True
            log.warning(f"Telegram xatosi: {r.status_code} {r.text}")
        except requests.RequestException as e:
            log.warning(f"Telegram ulanish xatosi: {e}")
        time.sleep(3)
    return False


# ---------------- ASOSIY MANTIQ ----------------
def signal_yubor():
    m = malumot_ol()
    if m is None:
        log.info("Bozor yopiq yoki ma'lumot yetarli emas, o'tkazib yuborildi")
        return

    ai = ai_tahlil_qil(m)
    signal, ishonch = ai["signal"], ai["ishonch"]
    log.info(f"AI: {signal} (ishonch {ishonch}) | narx {m['narx']}")

    holat["oxirgi_vaqt"] = datetime.now(timezone.utc).isoformat()

    if signal == "KUTISH" or ishonch < MIN_ISHONCH:
        holat["oxirgi_signal"] = "KUTISH"
        return
    if signal == holat["oxirgi_signal"]:
        log.info("Signal o'zgarmadi, qayta yuborilmadi")
        return

    sl, tp = daraja_hisobla(signal, m["narx"], m["atr"])
    belgi = "🟢" if signal == "BUY" else "🔴"
    matn = (
        f"{belgi} XAUUSD 15M — {signal}\n"
        f"Kirish: {m['narx']}\n"
        f"Stop-loss: {sl}\n"
        f"Take-profit: {tp}\n"
        f"Ishonch: {ishonch}/10 | RSI: {m['rsi']} | ATR: {m['atr']}\n\n"
        f"{ai['sabab']}\n\n"
        "⚠️ Bu moliyaviy maslahat emas. Risk: depozitning 1-2% dan oshmasin. "
        "Kirishdan oldin MT5 narxini tekshiring."
    )
    if telegramga_yubor(matn):
        holat["oxirgi_signal"] = signal
        log.info("✅ Signal yuborildi")


def keyingi_shamgacha_kut():
    """Keyingi 15 daqiqalik sham yopilishini kutadi (+15 soniya zaxira)."""
    time.sleep(INTERVAL_SEC - (time.time() % INTERVAL_SEC) + 15)


def background_bot_loop():
    log.info(">>> 15M GOLD AI BOT STARTED <<<")
    birinchi = True
    while True:
        try:
            yetmaydi = yetishmayotganlar()
            if yetmaydi:
                # Kalitlar Render Environment'ga qo'shilguncha signal yuborilmaydi
                log.error(f"Yetishmayapti: {', '.join(yetmaydi)}")
                time.sleep(60)
                continue

            if birinchi:
                telegramga_yubor("✅ Oltin AI bot ishga tushdi. Signal yangi sham yopilganda keladi.")
                birinchi = False

            signal_yubor()
            holat["oxirgi_xato"] = None
        except Exception as e:
            holat["oxirgi_xato"] = str(e)
            log.exception(f"Xatolik: {e}")
        keyingi_shamgacha_kut()


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    background_bot_loop()
