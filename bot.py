import telebot
import random
import json
import os

# --- 1. إعداد التوكن (أمان عالي) ---
# الكود بيبحث أولاً عن التوكن في "بيئة النظام" (عشان GitHub Actions)
# ولو ملقاهوش بيستخدم التوكن اللي إنت وضعته (للتشغيل في Termux)
TOKEN = os.getenv('BOT_TOKEN') or '7721384317:AAHaTZ-iM3RhBmjBgxdaN84ah3DjKUU_LT0'

bot = telebot.TeleBot(TOKEN)
DATA_FILE = 'memory.json'

# --- 2. إدارة الذاكرة (memory.json) ---
def load_data():
    """تحميل الردود من الملف أو إنشاء الردود الأساسية"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    # الردود الافتراضية لو الملف لسه متشفتش
    return {
        "السلام": "وعليكم السلام يا برنس الليالي! منور الجروب والله ⚡️",
        "يا بوت": "قلب البوت من جوه، أؤمرني يا زميلي 🫡",
        "عامل ايه": "زي الفل طول ما إنتو منورين كدا، إنت إيه دنيتك؟ 😉",
        "بتحبني": "بموت فيك يا كبييير، بس خلينا إخوات أحسن 😂❤️",
        "صباح الخير": "يا صباح القشطة والجمال على أحلى شلة ☕️✨"
    }

def save_data(data):
    """حفظ الردود الجديدة في الملف"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# تحميل البيانات في الرام عند التشغيل
responses = load_data()

# --- 3. ميزة التلقين (أضف: الكلمة = الرد) ---
@bot.message_handler(func=lambda message: message.text and "أضف:" in message.text)
def teach_bot(message):
    try:
        # فصل النص لاستخراج الكلمة والرد
        content = message.text.split("أضف:")[1].strip()
        if "=" in content:
            key, value = content.split("=")
            # حفظ الكلمة بحروف صغيرة عشان البوت يلقطها في أي وقت
            responses[key.strip().lower()] = value.strip()
            save_data(responses)
            bot.reply_to(message, f"✅ علم وينفذ! لو حد قال '{key.strip()}' هرد بـ '{value.strip()}'")
        else:
            bot.reply_to(message, "⚠️ يا زميلي اكتبها كدا: أضف: الكلمة = الرد")
    except:
        bot.reply_to(message, "❌ حصل مشكلة في الحفظ، جرب تاني.")

# --- 4. المعالج الرئيسي (الردود + الضحك + الإفيهات) ---
@bot.message_handler(func=lambda message: True)
def reply_matsry(message):
    if not message.text: return
    text = message.text.lower()

    # أ- التعامل مع الضحك
    if "ههه" in text:
        laughs = [
            "ههههههه يموت يا جدع 😂", 
            "ايه يا عم العسل ده! 🍯😂", 
            "والله إنت فايق ورايق 😂",
            "😂 حكايتك حكاية والله"
        ]
        bot.reply_to(message, random.choice(laughs))
        return

    # ب- البحث في القاموس (التلقين والأساسي)
    for key, value in responses.items():
        if key in text:
            bot.reply_to(message, value)
            return

    # ج- إفيهات عشوائية (احتمالية 5% ينطق لوحده)
    if random.random() < 0.05:
        jokes = [
            "أنا سامعكم على فكرة بس مطنش 😂",
            "يا جماعة حد يسكّت الواد ده بدل ما أطلعه برا الجروب 🏃‍♂️",
            "كلام كبار أوي أنا مليش فيه 🚶‍♂️😂",
            "ركزوا في المهم يا شباب وبلاش رغي كتير",
            "أنا سامعكم بس بفك شفرة 🏃‍♂️",
            "يا رغيكم اللي مبيخلصش!"
        ]
        bot.send_message(message.chat.id, random.choice(jokes))

# تشغيل البوت
print("🚀 البوت المدمج شغال وجاهز للهزار...")
bot.infinity_polling()
