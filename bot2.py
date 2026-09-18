import os
import threading
import time
from flask import Flask
from groq import Groq
import requests

# Groq mijozini sozlash
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Render port talabini qondirish uchun Flask veb-serveri
app = Flask(__name__)


@app.route("/")
def home():
  return "Gold 15M AI Bot is running!"


def run_web():
  port = int(os.environ.get("PORT", 10000))
  app.run(host="0.0.0.0", port=port)


def ai_tahlil_qil(yangilik):
  try:
    chat_completion = groq_client.chat.completions.create(
      messages=[
          {
              "role": "system",
              "content": (
                  "Siz oltin (XAUUSD) bo'yicha professional"
                  " tahlilchisiz. Qisqa va tushunarli fundamental tahlil"
                  " qilib berasiz."
              ),
          },
          {
              "role": "user",
              "content": (
                  "Mana bu ma'lumotni oltin narxiga ta'sirini tahlil qilib"
                  f" ber: {yangilik}"
              ),
          },
      ],
      model="llama-3.3-70b-versatile",
    )
    return chat_completion.choices[0].message.content
  except Exception as e:
    return f"Tahlil xatosi: {e}"


def background_bot_loop():
  print(">>> 15M INTERVAL BOT WITH AI & CHARTS STARTED <<<")
  while True:
    try:
      # Bu yerda o'zingizning narx olish va tahlil yuborish mantiqlaringiz ishlaydi
      # Masalan, sinov tariqasida har 15 daqiqada ishlaydigan sikl:
      print("✅ 15 daqiqalik tsikl bajarildi!")

    except Exception as e:
      print(f"Xatolik yuz berdi: {e}")

    time.sleep(900)  # 15 daqiqa (900 soniya) kutish


if __name__ == "__main__":
  # Veb-serverni alohida oqimda (thread) ishga tushiramiz (Render port talabi uchun)
  t = threading.Thread(target=run_web)
  t.daemon = True
  t.start()

  # Botning asosiy siklini ishga tushiramiz
  background_bot_loop()
import time


def background_bot_loop():
  print(">>> 15M INTERVAL BOT WITH AI & CHARTS STARTED <<<")

  # 1. Bot ishga tushishi bilan DARXOL 1-chi signalni yuborish:
  try:
    print("✅ Birinchi signal yuborilmoqda...")
    # Bu yerga narxni olib, tahlil qilib, Telegramga yuboradigan funksiyangizni yozasiz
    # Masalan: tahlil_va_signalni_yuborish()
  except Exception as e:
    print(f"Birinchi signalni yuborishda xatolik: {e}")

  # 2. Keyin 15 daqiqalik cheksiz sikl boshlanadi
  while True:
    try:
      time.sleep(900)  # 15 daqiqa (900 soniya) kutish
      print("✅ Har 15 daqiqalik tahlil yuborildi!")
      # Keyingi 15 daqiqalik signal kodi shu yerda ishlaydi

    except Exception as e:
      print(f"Xatolik yuz berdi: {e}")
