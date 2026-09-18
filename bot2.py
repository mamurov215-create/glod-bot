import os
from groq import Groq

# Kalitni shaxsan o'zi kiritmaymiz, u maxfiy joydan o'qiladi
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def ai_tahlil_qil(yangilik):
    try:
        chat_completion = client.chat.completions.create(
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
        return f"Tahlil qilishda xatolik: {e}"
