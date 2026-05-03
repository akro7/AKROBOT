import telebot
import random
import json
import os
import re
import time

# ========================================
#   AKRO BOT v2.0 - by Ahmed (AKRO)
# ========================================

TOKEN = os.getenv('BOT_TOKEN') or '7721384317:AAHaTZ-iM3RhBmjBgxdaN84ah3DjKUU_LT0'
bot = telebot.TeleBot(TOKEN)
DATA_FILE = 'memory.json'

# ─────────────────────────────────────────
#  إدارة الذاكرة
# ─────────────────────────────────────────
DEFAULT_RESPONSES = {
    "السلام": "وعليكم السلام يا برنس الليالي! منور الجروب والله ⚡️",
    "يا بوت": "قلب البوت من جوه، أؤمرني يا زميلي 🫡",
    "عامل ايه": "زي الفل طول ما إنتو منورين كدا، إنت إيه دنيتك؟ 😉",
    "بتحبني": "بموت فيك يا كبييير، بس خلينا إخوات أحسن 😂❤️",
    "صباح الخير": "يا صباح القشطة والجمال على أحلى شلة ☕️✨",
    "مساء الخير": "مساء النور والسرور يا أحلى ناس 🌙✨",
    "تعبان": "خد راحتك يا قلبي، إحنا هنا 💪❤️",
    "زهقت": "تعالى نتكلم يا باشا، إيه اللي في بالك؟ 😄",
    "بخير": "الحمد لله، ربنا يديم النعمة 🙏✨",
    "شكرا": "على الرحب والسعة يا روح! 🤝",
    "اوك": "تمام تمام، كل حاجة تمام 👌",
    "تمام": "يسلم اللسان اللي قال تمام 😂👍",
    "نوم": "تصبح على خير يا حبيب، أحلام وردية 🌙😴",
    "تعال": "أنا هنا يا سيدي خطوة وسط 😂⚡",
    "كلام": "كلام كلام كلام! يلا جيب الكلام المفيد 😂",
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # دمج الافتراضي مع المحفوظ (المحفوظ له الأولوية)
                merged = {**DEFAULT_RESPONSES, **data}
                return merged
        except:
            return DEFAULT_RESPONSES.copy()
    return DEFAULT_RESPONSES.copy()

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"خطأ في الحفظ: {e}")
        return False

responses = load_data()

# ─────────────────────────────────────────
#  ردود الفكاهة والعشوائيات
# ─────────────────────────────────────────
LAUGH_RESPONSES = [
    "ههههههه يموت يا جدع 😂💀",
    "ايه يا عم العسل ده! 🍯😂",
    "والله إنت فايق ورايق 😂",
    "😂 حكايتك حكاية والله",
    "يا عيني على الضحكة دي 😭😂",
    "الله الله يا كبير 😂🔥",
    "متكسرش من الضحك 😂😂",
    "والنبي ده كلام ولا جاي يضحك علينا؟ 😂",
    "يامضحكني أنا دا جبت جبت 😂",
    "سم كمان خلي الناس تتريح 😂💀",
]

RANDOM_JOKES = [
    "أنا سامعكم على فكرة بس مطنش 😂",
    "يا جماعة حد يسكّت الواد ده بدل ما أطلعه برا الجروب 🏃‍♂️",
    "كلام كبار أوي أنا مليش فيه 🚶‍♂️😂",
    "ركزوا في المهم يا شباب وبلاش رغي كتير 😤",
    "أنا سامعكم بس بفك شفرة 🕵️‍♂️",
    "يا رغيكم اللي مبيخلصش! 😂",
    "في حاجة مهمة حد يقولها 😂 ولا كلنا هنا عبث؟",
    "لو اللي بتقولوه ده فيلم كان هيتمسح من السينما 😂",
    "حلو الكلام ده بس ما فيش فايدة منه 😂",
    "الجروب ده خزنة من الكلام اللي مش محتاجينه 😂",
    "أنا شايف كل حاجة ومش قولكم 👀😂",
    "يا عيني على اللي بيحاول يكون جدي هنا 😂",
    "النهارده الجروب أكتر من الأيام اللي فاتت 😂",
    "الله ينور على الفاضي اللي عنده وقت للكلام ده 😂",
]

INSULT_COMEBACKS = [
    "ماشي يا عم أنا معاك 😂",
    "ربنا يهديك ويهدي اللي بعتك 😂",
    "يا راجل سيبني من الكلام ده 😂",
    "أنا بوت بس كلامك وجعني 😂",
    "أمال إيه؟ 😂",
]

GREET_EXTRAS = [
    "إنت الأحلى والأغلى 🌟",
    "نورت المكان والله 🔥",
    "يا هلا هلا هلا 🎉",
    "البطل وصل 👑",
    "الكبير بيطل 😎",
]

# ─────────────────────────────────────────
#  أمر /start و /help
# ─────────────────────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "صاحبي"
    bot.reply_to(message, 
        f"أهلاً يا {name}! 👋\n"
        "أنا البوت المدمج جاهز للهزار والخدمة 🤖⚡\n\n"
        "📌 *الأوامر المتاحة:*\n"
        "• `أضف: كلمة = رد` — علمني رد جديد\n"
        "• `قول محمد` أو `قول أي كلام` — البوت يقوله مباشرة\n"
        "• `/list` — شوف الردود المحفوظة\n"
        "• `/del كلمة` — احذف رد محفوظ\n"
        "• `/help` — قائمة الأوامر",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message,
        "🤖 *أوامر البوت:*\n\n"
        "📝 *التعليم:*\n"
        "`أضف: كلمة = الرد` — تعليم رد جديد\n\n"
        "🗣️ *قول أي كلام:*\n"
        "`قول محمد` أو `قول أي جملة` — البوت يقولها مباشرة\n\n"
        "📋 *عرض الردود:*\n"
        "`/list` — شوف كل الردود\n\n"
        "🗑️ *حذف رد:*\n"
        "`/del كلمة` — احذف رد بالكلمة بتاعته\n\n"
        "ℹ️ *حالة البوت:*\n"
        "`/stats` — إحصائيات البوت",
        parse_mode='Markdown'
    )

# ─────────────────────────────────────────
#  عرض الردود المحفوظة /list
# ─────────────────────────────────────────
@bot.message_handler(commands=['list'])
def list_responses(message):
    if not responses:
        bot.reply_to(message, "📭 مفيش ردود محفوظة لحد دلوقتي!")
        return
    
    # تقسيم لو الردود كتير
    items = list(responses.items())
    chunk_size = 20
    
    if len(items) <= chunk_size:
        text = "📋 *الردود المحفوظة:*\n\n"
        for i, (k, v) in enumerate(items, 1):
            short_v = v[:40] + "..." if len(v) > 40 else v
            text += f"{i}. `{k}` ← {short_v}\n"
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        # أرسل في أكتر من رسالة
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i+chunk_size]
            text = f"📋 *الردود ({i+1}-{min(i+chunk_size, len(items))}):*\n\n"
            for j, (k, v) in enumerate(chunk, i+1):
                short_v = v[:35] + "..." if len(v) > 35 else v
                text += f"{j}. `{k}` ← {short_v}\n"
            bot.send_message(message.chat.id, text, parse_mode='Markdown')
            time.sleep(0.3)

# ─────────────────────────────────────────
#  حذف رد /del
# ─────────────────────────────────────────
@bot.message_handler(commands=['del'])
def delete_response(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ اكتب: `/del الكلمة`", parse_mode='Markdown')
        return
    
    key = parts[1].strip().lower()
    if key in responses:
        del responses[key]
        save_data(responses)
        bot.reply_to(message, f"🗑️ تم حذف رد `{key}` بنجاح!", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش رد باسم `{key}`", parse_mode='Markdown')

# ─────────────────────────────────────────
#  إحصائيات /stats
# ─────────────────────────────────────────
@bot.message_handler(commands=['stats'])
def stats(message):
    custom = len(responses) - len(DEFAULT_RESPONSES)
    bot.reply_to(message,
        f"📊 *إحصائيات البوت:*\n\n"
        f"🧠 إجمالي الردود: `{len(responses)}`\n"
        f"📦 ردود افتراضية: `{len(DEFAULT_RESPONSES)}`\n"
        f"✏️ ردود مضافة: `{max(0, custom)}`\n"
        f"😂 نكات عشوائية: `{len(RANDOM_JOKES)}`\n"
        f"😂 ردود ضحك: `{len(LAUGH_RESPONSES)}`\n\n"
        f"⚡ البوت شغال تمام!",
        parse_mode='Markdown'
    )

# ─────────────────────────────────────────
#  ميزة التلقين: أضف: كلمة = رد
# ─────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text and re.search(r'أضف\s*:', m.text))
def teach_bot(message):
    try:
        content = re.split(r'أضف\s*:', message.text, maxsplit=1)[1].strip()
        if "=" not in content:
            bot.reply_to(message, "⚠️ اكتبها كدا:\n`أضف: الكلمة = الرد`", parse_mode='Markdown')
            return

        key, value = content.split("=", 1)
        key = key.strip().lower()
        value = value.strip()

        if not key or not value:
            bot.reply_to(message, "⚠️ الكلمة والرد ما ينفعوش يكونوا فاضيين!")
            return

        is_update = key in responses
        responses[key] = value
        
        if save_data(responses):
            action = "✏️ تم التحديث" if is_update else "✅ علم وينفذ"
            bot.reply_to(message, 
                f"{action}!\n"
                f"🔑 الكلمة: `{key}`\n"
                f"💬 الرد: {value}",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(message, "❌ حصل مشكلة في الحفظ، جرب تاني!")
    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ─────────────────────────────────────────
#  ميزة "قول [أي كلام]" - مباشر بدون فورمات
# ─────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text and re.match(r'^قول\s+.+', m.text.strip()))
def say_direct(message):
    try:
        # استخراج الكلام بعد كلمة "قول"
        text = re.sub(r'^قول\s+', '', message.text.strip(), count=1).strip()

        if not text:
            bot.reply_to(message, "⚠️ اكتب بعد قول الكلام اللي تقوله!")
            return

        # البوت يقول الكلام مباشرة
        bot.send_message(message.chat.id, text)

        # احذف رسالة الأمر الأصلية لو البوت أدمن
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ─────────────────────────────────────────
#  المعالج الرئيسي
# ─────────────────────────────────────────
@bot.message_handler(func=lambda message: True)
def reply_main(message):
    if not message.text:
        return

    text = message.text.lower().strip()
    name = message.from_user.first_name or ""

    # ── 1. الضحك ──
    if any(x in text for x in ["ههه", "هههه", "wkwk", "lol", "😂", "😹"]):
        bot.reply_to(message, random.choice(LAUGH_RESPONSES))
        return

    # ── 2. تحية شخصية بالاسم ──
    greet_words = ["يا بوت", "بوت", "هاي", "هلو", "أهلا", "أهلو", "سلام عليكم"]
    if any(g in text for g in greet_words):
        extra = random.choice(GREET_EXTRAS)
        bot.reply_to(message, f"أهلاً يا {name}! {extra} ⚡")
        return

    # ── 3. البحث في القاموس ──
    for key, value in responses.items():
        if key.lower() in text:
            bot.reply_to(message, value)
            return

    # ── 4. كشف الشتيمة/الإزعاج ──
    bad_words = ["احا", "عيل", "غبي", "بوت وسخ", "مش بيشتغل", "خربان"]
    if any(b in text for b in bad_words):
        bot.reply_to(message, random.choice(INSULT_COMEBACKS))
        return

    # ── 5. سؤال عن البوت ──
    if any(x in text for x in ["إيه", "ايه", "مين إنت", "مين انت", "بتعمل إيه", "تعمل ايه"]):
        bot.reply_to(message, 
            "أنا البوت المدمج AKRO v2 ⚡\n"
            "بتعلم، بحفظ، وبهزر معاكم 😂\n"
            "اكتب /help تعرف الأوامر 🤖"
        )
        return

    # ── 6. نكات عشوائية (7%) ──
    if random.random() < 0.07:
        bot.send_message(message.chat.id, random.choice(RANDOM_JOKES))

# ─────────────────────────────────────────
#  تشغيل البوت
# ─────────────────────────────────────────
print("🚀 AKRO BOT v2.0 شغال وجاهز للهزار...")
print(f"📦 ردود محملة: {len(responses)}")

bot.infinity_polling(timeout=60, long_polling_timeout=60)
