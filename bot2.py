import os
import time
from groq import Groq
import requests

# Groq mijozini sozlash (Render'dagi GROQ_API_KEY dan o'qiydi)
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def ai_tahlil_qil(yangilik):
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "Siz oltin (XAUUSD) bo'yicha professional tahlilchisiz. Qisqa va tushunarli fundamental tahlil qilib berasiz.",
                },
                {
                    "role": "user",
                    "content": f"Mana bu ma'lumotni oltin narxiga ta'sirini tahlil qilib ber: {yangilik}",
                },
            ],
            model="llama-3.3-70b-versatile",
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Tahlil xatosi: {e}"

print(">>> BOT TOZA HOLATDA ISHGA TUSHDI <<<")

# Bu yerda sizning asosiy bot kodlaringiz (15 daqiqalik sikl va boshqalar) ishlaydi
while True:
    time.sleep(900)  # 15 daqiqa kutish
