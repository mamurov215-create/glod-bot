from flask import Flask, request
import requests
import os
import threading
import time

app = Flask(__name__)

# TELEGRAM BOT SOZLAMALARI
TELEGRAM_BOT_TOKEN = "8839970219:AAHtbNDmsahAOr1Mw86EA7DF-AYFyr2Bh98"
TELEGRAM_CHAT_ID = "301467534"  # Faqat o'zingizning ID raqamingiz yoziladi


def telegramga_xabar_yuborish(matn):
  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  data = {"chat_id": TELEGRAM_CHAT_ID, "text": matn, "parse_mode": "Markdown"}
  try:
    requests.post(url, json=data)
  except Exception as e:
    print(f"Telegramga xabar yuborishda xatolik: {e}")
