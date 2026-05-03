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
DATA_FILE   = 'memory.json'
PEOPLE_FILE = 'people.json'

# ══════════════════════════════════════════
#  ① قاعدة الأشخاص  (people.json)
# ══════════════════════════════════════════
def load_people():
    if os.path.exists(PEOPLE_FILE):
        try:
            with open(PEOPLE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_people(data):
    try:
        with open(PEOPLE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False

people_db = load_people()

# ══════════════════════════════════════════
#  ② قاموس الردود  (memory.json)
# ══════════════════════════════════════════
DEFAULT_RESPONSES = {
    "السلام":      "وعليكم السلام يا برنس الليالي! منور الجروب والله ⚡️",
    "يا بوت":      "قلب البوت من جوه، أؤمرني يا زميلي 🫡",
    "عامل ايه":    "زي الفل طول ما إنتو منورين كدا، إنت إيه دنيتك؟ 😉",
    "بتحبني":      "بموت فيك يا كبييير، بس خلينا إخوات أحسن 😂❤️",
    "صباح الخير":  "يا صباح القشطة والجمال على أحلى شلة ☕️✨",
    "مساء الخير":  "مساء النور والسرور يا أحلى ناس 🌙✨",
    "تعبان":       "خد راحتك يا قلبي، إحنا هنا 💪❤️",
    "زهقت":        "تعالى نتكلم يا باشا، إيه اللي في بالك؟ 😄",
    "بخير":        "الحمد لله، ربنا يديم النعمة 🙏✨",
    "شكرا":        "على الرحب والسعة يا روح! 🤝",
    "اوك":         "تمام تمام، كل حاجة تمام 👌",
    "تمام":        "يسلم اللسان اللي قال تمام 😂👍",
    "نوم":         "تصبح على خير يا حبيب، أحلام وردية 🌙😴",
    "تعال":        "أنا هنا يا سيدي خطوة وسط 😂⚡",
    "كلام":        "كلام كلام كلام! يلا جيب الكلام المفيد 😂",
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {**DEFAULT_RESPONSES, **data}
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

# ══════════════════════════════════════════
#  ③ ردود الفكاهة
# ══════════════════════════════════════════
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

# ══════════════════════════════════════════
#  ④ تعليقات فكاهية قبل الاقتباس (QuotLy)
# ══════════════════════════════════════════
QUOTE_COMMENTS = [
    "⚠️ تحذير: الكلام ده هيتحفظ في سجلات الجروب للأبد 😂",
    "🏆 جملة اليوم جت من هنا! اقتباس تاريخي 😂",
    "📜 خليني أخلد الكلام الجميل ده 😂",
    "👀 أنا شايفك وشايف كلامك كمان 😂",
    "💎 كلام زي الفل، لازم يتحفظ 😂",
    "🎤 مايك دروب من هنا! 😂🎤",
    "🔥 ده كلام أو جاي يحرق الجروب؟ 😂",
    "📸 تصوير! الكلام ده فات علينا سريع 😂",
    "🤣 الناس دي مش طبيعية، خليني أسجل 😂",
    "🌟 نجمة الجروب تكلمت! اقتباس واجب 😂",
    "😱 أنا مصدق كلامك ده؟ هنحتاجه دليل بعدين 😂",
    "🎬 كاميرا! اكشن! رسالة تاريخية 😂",
    "💬 الكلام ده يستاهل لوحة شرف 😂",
    "🗿 خالد الكلام ده للأجيال الجاية 😂",
    "⚡ فلاش نيوز: شخص قال حاجة مهمة جداً هنا 😂",
]

# ألوان عشوائية لـ QuotLy
QUOTE_COLORS = ["red", "blue", "green", "purple", "orange", "pink", "white", "random", "#cbafff", "#ff6b6b", "#4ecdc4"]

# ══════════════════════════════════════════
#  دالة مساعدة: اعمل اقتباس QuotLy
# ══════════════════════════════════════════
def make_quote(message, color=None, extra_flags=""):
    """بتبعت أمر /q لـ QuotLy على رسالة معينة"""
    if not color:
        color = random.choice(QUOTE_COLORS)
    cmd = f"/q {color} {extra_flags}".strip()
    bot.send_message(message.chat.id, cmd, reply_to_message_id=message.message_id)

# ══════════════════════════════════════════
#  /start  و  /help
# ══════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "صاحبي"
    bot.reply_to(message,
        f"أهلاً يا {name}! 👋\n"
        "أنا البوت المدمج جاهز للهزار والخدمة 🤖⚡\n\n"
        "📌 *الأوامر المتاحة:*\n"
        "• `أضف: كلمة = رد` — علمني رد جديد\n"
        "• `قول أي كلام` — البوت يقوله مباشرة\n"
        "• `عرف اسم: معلوماته` — حفظ شخص\n"
        "• `مين اسم` — السؤال عن أي شخص\n"
        "• `اقتبس` — اقتباس فكاهي عشوائي\n"
        "• `/help` — قائمة كل الأوامر",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message,
        "🤖 *أوامر البوت:*\n\n"
        "📝 *ردود مخصصة:*\n"
        "`أضف: كلمة = الرد`\n\n"
        "🗣️ *قول:*\n"
        "`قول أي كلام` — البوت يقوله مباشرة\n\n"
        "👤 *الأشخاص:*\n"
        "`عرف عماد: هو صاحبي من القاهرة`\n"
        "`مين عماد` — السؤال عن أي شخص\n"
        "`/people` — كل الأشخاص المحفوظين\n"
        "`/delperson اسم` — احذف شخص\n\n"
        "🎨 *اقتباسات QuotLy (رد على رسالة):*\n"
        "`اقتبس` — اقتباس فكاهي بلون عشوائي\n"
        "`اقتبس احمر` / `اقتبس ازرق` — بلون محدد\n"
        "`اقتبس صورة` — اقتباس على شكل صورة\n"
        "`اقتبس مع رد` — يحتفظ بالرد الأصلي\n\n"
        "📋 *الردود:*\n"
        "`/list` — شوف كل الردود\n"
        "`/del كلمة` — احذف رد\n\n"
        "📊 `/stats` — إحصائيات البوت",
        parse_mode='Markdown'
    )

# ══════════════════════════════════════════
#  /list  /del  /stats
# ══════════════════════════════════════════
@bot.message_handler(commands=['list'])
def list_responses(message):
    if not responses:
        bot.reply_to(message, "📭 مفيش ردود محفوظة!")
        return
    items = list(responses.items())
    for i in range(0, len(items), 20):
        chunk = items[i:i+20]
        text = f"📋 *الردود ({i+1}–{i+len(chunk)}):*\n\n"
        for j, (k, v) in enumerate(chunk, i+1):
            sv = v[:38] + "..." if len(v) > 38 else v
            text += f"{j}. `{k}` ← {sv}\n"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
        time.sleep(0.3)

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
        bot.reply_to(message, f"🗑️ تم حذف `{key}` بنجاح!", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش رد باسم `{key}`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats(message):
    custom = max(0, len(responses) - len(DEFAULT_RESPONSES))
    bot.reply_to(message,
        f"📊 *إحصائيات البوت:*\n\n"
        f"🧠 إجمالي الردود: `{len(responses)}`\n"
        f"📦 ردود افتراضية: `{len(DEFAULT_RESPONSES)}`\n"
        f"✏️ ردود مضافة: `{custom}`\n"
        f"👥 أشخاص محفوظين: `{len(people_db)}`\n"
        f"😂 نكات عشوائية: `{len(RANDOM_JOKES)}`\n\n"
        f"⚡ البوت شغال تمام!",
        parse_mode='Markdown'
    )

# ══════════════════════════════════════════
#  /people  /delperson
# ══════════════════════════════════════════
@bot.message_handler(commands=['people'])
def list_people(message):
    if not people_db:
        bot.reply_to(message,
            "📭 مفيش أشخاص محفوظين!\n"
            "استخدم: `عرف اسم: معلومات`", parse_mode='Markdown')
        return
    text = f"👥 *الأشخاص المحفوظين ({len(people_db)}):*\n\n"
    for i, (_, p) in enumerate(people_db.items(), 1):
        short = p['info'][:50] + "..." if len(p['info']) > 50 else p['info']
        text += f"{i}. *{p['name']}* — {short}\n"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(commands=['delperson'])
def delete_person(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ اكتب: `/delperson الاسم`", parse_mode='Markdown')
        return
    key = parts[1].strip().lower()
    if key in people_db:
        name = people_db[key]['name']
        del people_db[key]
        save_people(people_db)
        bot.reply_to(message, f"🗑️ تم حذف *{name}* من القاعدة", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش *{key}*", parse_mode='Markdown')

# ══════════════════════════════════════════
#  أضف: كلمة = رد
# ══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.search(r'أضف\s*:', m.text))
def teach_bot(message):
    try:
        content = re.split(r'أضف\s*:', message.text, maxsplit=1)[1].strip()
        if "=" not in content:
            bot.reply_to(message, "⚠️ اكتبها كدا:\n`أضف: الكلمة = الرد`", parse_mode='Markdown')
            return
        key, value = content.split("=", 1)
        key, value = key.strip().lower(), value.strip()
        if not key or not value:
            bot.reply_to(message, "⚠️ الكلمة والرد ما ينفعوش يكونوا فاضيين!")
            return
        is_update = key in responses
        responses[key] = value
        if save_data(responses):
            action = "✏️ تم التحديث" if is_update else "✅ علم وينفذ"
            bot.reply_to(message,
                f"{action}!\n🔑 الكلمة: `{key}`\n💬 الرد: {value}",
                parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ حصل مشكلة في الحفظ، جرب تاني!")
    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ══════════════════════════════════════════
#  قول [أي كلام]  — رد مباشر
# ══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^قول\s+.+', m.text.strip()))
def say_direct(message):
    try:
        text = re.sub(r'^قول\s+', '', message.text.strip(), count=1).strip()
        if not text:
            bot.reply_to(message, "⚠️ اكتب بعد قول الكلام اللي تقوله!")
            return
        bot.reply_to(message, text)
    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ══════════════════════════════════════════
#  عرف [اسم]: [معلومات]
# ══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^عرف\s+.+\s*:', m.text.strip()))
def add_person(message):
    try:
        match = re.match(r'^عرف\s+(.+?)\s*:\s*(.+)$', message.text.strip(), re.DOTALL)
        if not match:
            bot.reply_to(message, "⚠️ اكتبها كدا: `عرف عماد: هو صاحبي من القاهرة`", parse_mode='Markdown')
            return
        name  = match.group(1).strip()
        info  = match.group(2).strip()
        key   = name.lower()
        is_update = key in people_db
        people_db[key] = {"name": name, "info": info}
        save_people(people_db)
        action = "✏️ تم تحديث معلومات" if is_update else "✅ تم حفظ معلومات"
        bot.reply_to(message, f"{action} *{name}* 👤\n💬 {info}", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ══════════════════════════════════════════
#  مين [اسم]
# ══════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^مين\s+\S+', m.text.strip()))
def who_is(message):
    try:
        query = re.sub(r'^مين\s+', '', message.text.strip(), count=1).strip().lower()
        p = people_db.get(query) or next(
            (v for k, v in people_db.items() if query in k), None
        )
        if p:
            bot.reply_to(message, f"👤 *{p['name']}*\n\n{p['info']}", parse_mode='Markdown')
        else:
            bot.reply_to(message,
                f"🤷 معرفش مين *{query}*\n"
                f"علمني بـ: `عرف {query}: معلومات`",
                parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ══════════════════════════════════════════
#  🎨 أوامر الاقتباس (QuotLy) — "اقتبس"
#  لازم يكون رد على رسالة
# ══════════════════════════════════════════

# خريطة الألوان العربية → إنجليزي
COLOR_MAP = {
    "احمر": "red", "أحمر": "red",
    "ازرق": "blue", "أزرق": "blue",
    "اخضر": "green", "أخضر": "green",
    "بنفسجي": "purple",
    "برتقالي": "orange",
    "وردي": "pink",
    "ابيض": "white", "أبيض": "white",
    "اسود": "black", "أسود": "black",
    "عشوائي": "random",
}

@bot.message_handler(func=lambda m: m.text and re.match(r'^اقتبس', m.text.strip()))
def quote_handler(message):
    # لازم يكون رد على رسالة
    if not message.reply_to_message:
        bot.reply_to(message,
            "⚠️ رد على الرسالة اللي عاوز تقتبسها الأول!\n"
            "مثال: رد على رسالة واكتب `اقتبس` 😄",
            parse_mode='Markdown')
        return

    try:
        target = message.reply_to_message
        parts  = message.text.strip().split()
        # parts[0] = "اقتبس"، parts[1..] = خيارات اختيارية

        color      = "random"
        extra_flag = ""
        is_image   = False
        keep_reply = False

        for part in parts[1:]:
            p = part.strip()
            if p in COLOR_MAP:
                color = COLOR_MAP[p]
            elif p in ["صورة", "img", "png"]:
                is_image = True
            elif p in ["مع رد", "رد"]:
                keep_reply = True
            elif p.startswith("#"):
                color = p  # hex color مباشر

        # بناء الأمر
        flags = []
        if is_image:
            flags.append("i")
        if keep_reply:
            flags.append("r")
        flags_str = " ".join(flags)

        q_cmd = f"/q {color} {flags_str}".strip()

        # تعليق فكاهي أولاً
        comment = random.choice(QUOTE_COMMENTS)
        sender_name = target.from_user.first_name or "حد"
        funny_intro = random.choice([
            f"😂 {sender_name} قال إيه؟! لازم يتحفظ ده!",
            f"👀 يا جماعة شوفوا {sender_name} قال إيه 😂",
            f"📜 تاريخ يُسجَّل بس مش بالذهب 😂",
            f"🔥 {sender_name} جاب كلام تاريخي 😂",
            f"💀 {sender_name} قالها وراح 😂",
            f"⚡ فلاش نيوز من {sender_name}! 😂",
            comment,
        ])

        # ابعت التعليق الفكاهي
        bot.reply_to(message, funny_intro)
        time.sleep(0.5)

        # ابعت أمر QuotLy على الرسالة الأصلية
        bot.send_message(
            message.chat.id,
            q_cmd,
            reply_to_message_id=target.message_id
        )

    except Exception as e:
        bot.reply_to(message, f"❌ حصل خطأ: {str(e)}")

# ══════════════════════════════════════════
#  المعالج الرئيسي
# ══════════════════════════════════════════
@bot.message_handler(func=lambda message: True)
def reply_main(message):
    if not message.text:
        return

    text = message.text.lower().strip()
    name = message.from_user.first_name or ""

    # 1. الضحك
    if any(x in text for x in ["ههه", "هههه", "wkwk", "lol", "😂", "😹"]):
        # أحياناً يضحك + يقتبس الرسالة (20% احتمال)
        bot.reply_to(message, random.choice(LAUGH_RESPONSES))
        if random.random() < 0.20 and message.text:
            time.sleep(0.8)
            color = random.choice(QUOTE_COLORS)
            bot.send_message(
                message.chat.id,
                f"/q {color}",
                reply_to_message_id=message.message_id
            )
        return

    # 2. تحية بالاسم
    if any(g in text for g in ["يا بوت", "بوت", "هاي", "هلو", "أهلا", "أهلو", "سلام عليكم"]):
        bot.reply_to(message, f"أهلاً يا {name}! {random.choice(GREET_EXTRAS)} ⚡")
        return

    # 3. البحث في القاموس
    for key, value in responses.items():
        if key.lower() in text:
            bot.reply_to(message, value)
            return

    # 4. شتيمة / إزعاج — يرد ويقتبس كمان 😂
    if any(b in text for b in ["احا", "عيل", "غبي", "بوت وسخ", "مش بيشتغل", "خربان"]):
        bot.reply_to(message, random.choice(INSULT_COMEBACKS))
        time.sleep(0.5)
        bot.send_message(
            message.chat.id,
            f"😂 وعشان متنكرش، هنحفظ الكلام ده!\n/q red",
            reply_to_message_id=message.message_id
        )
        return

    # 5. سؤال عن البوت
    if any(x in text for x in ["مين إنت", "مين انت", "بتعمل إيه", "تعمل ايه"]):
        bot.reply_to(message,
            "أنا البوت المدمج AKRO v2 ⚡\n"
            "بتعلم، بحفظ، وبهزر معاكم 😂\n"
            "اكتب /help تعرف الأوامر 🤖")
        return

    # 6. نكتة عشوائية (7%) — أحياناً مع اقتباس
    if random.random() < 0.07:
        joke = random.choice(RANDOM_JOKES)
        bot.send_message(message.chat.id, joke)

        # 30% من النكات بتيجي مع اقتباس للرسالة اللي أثارت النكتة
        if random.random() < 0.30:
            time.sleep(0.6)
            color = random.choice(QUOTE_COLORS)
            bot.send_message(
                message.chat.id,
                f"📜 وعشان الكلام ده يتسجل في التاريخ 😂\n/q {color}",
                reply_to_message_id=message.message_id
            )

# ══════════════════════════════════════════
#  تشغيل
# ══════════════════════════════════════════
print("🚀 AKRO BOT v2.0 شغال وجاهز للهزار...")
print(f"📦 ردود: {len(responses)} | 👥 أشخاص: {len(people_db)}")

bot.infinity_polling(timeout=60, long_polling_timeout=60)
