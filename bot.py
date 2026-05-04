import telebot
import random
import json
import os
import re
import time
from collections import Counter
import requests

# ========================================
#   AKRO BOT v5.0 - AI GROK EDITION
#   by Ahmed (AKRO)
# ========================================

TOKEN = os.getenv('BOT_TOKEN') or '7721384317:AAHaTZ-iM3RhBmjBgxdaN84ah3DjKUU_LT0'
GROK_API_KEY = os.getenv('GROK_API_KEY') or 'xai-ضع_مفتاح_جروك_هنا'
GROK_MODEL   = os.getenv('GROK_MODEL')   or 'grok-2-latest'
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

bot = telebot.TeleBot(TOKEN)

DATA_FILE   = 'memory.json'
PEOPLE_FILE = 'people.json'
LEARN_FILE  = 'learned.json'
CONTEXT_DIR = 'contexts.json'

# ══════════════════════════════════════════
#  تحميل وحفظ JSON
# ══════════════════════════════════════════
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

people_db      = load_json(PEOPLE_FILE, {})
learned_styles = load_json(LEARN_FILE,  {})
user_contexts  = load_json(CONTEXT_DIR, {})
# ══════════════════════════════════════════
#  نظام السياق الذكي (Context Window)
# ══════════════════════════════════════════
def update_context(uid, role, text):
    uid = str(uid)
    if uid not in user_contexts:
        user_contexts[uid] = []
    user_contexts[uid].append({"role": role, "content": text})
    # نحفظ آخر 6 رسائل فقط للحفاظ على التوكنات والسرعة
    if len(user_contexts[uid]) > 6:
        user_contexts[uid] = user_contexts[uid][-6:]
    save_json(CONTEXT_DIR, user_contexts)

# ══════════════════════════════════════════
#  قاموس الردود السريع (Fast Path)
# ══════════════════════════════════════════
DEFAULT_RESPONSES = {
    "السلام":       ["وعليكم السلام 👋", "أهلاً أهلاً ⚡", "وعليكم ✨"],
    "صباح الخير":  ["صباح النور ☀️", "صبحك الله بالخير ☕", "يا صباح الفل 🌸"],
    "مساء الخير":  ["مساء النور 🌙", "مساؤك ورد وفل ✨", "أحلى مساء 🌟"],
    "بخير":        ["الحمد لله 🙏", "ربنا يديم النعمة ✨", "تمام زي الفل 💪"],
    "شكرا":        ["على الرحب 🤝", "أي خدمة 😄", "بكل حب ❤️"],
    "تعبان":       ["ربنا يشفيك ❤️", "خد راحتك 💙", "الله يعافيك 🤲"],
    "زهقت":        ["إيه اللي في بالك؟ 😄", "الجروب هنا 😂", "روح نام 😴😂"],
    "تمام":        ["تمام تمام 👌", "يسلم 😄", "ماشي كده 👍"],
    "اوك":         ["👌", "ماشي 😄", "تمام 👍"],
    "بتحبني":      ["بموت فيك 😂❤️", "أكيد يا كبير 😄", "طبعاً 🫡"],
    "نوم":         ["تصبح على خير 🌙", "أحلام حلوة 😴✨", "نامت العين 😂"],
    "كويس":        ["الحمد لله ✨", "ربنا يكملها 🙏", "تمام 👍"],
    "ايه الاخبار": ["كله تمام 😄", "أخبار حلوة ✨", "الحمد لله 😊"],
    "عامل ايه":    ["تمام والله 😄", "زي الفل 💪", "كويس وانت؟ 😊"],
    "مشكلة":       ["قولي إيه المشكلة 🛠️", "أنا هنا 😄", "اتفضل 👂"],
    "يا بوت":      ["أيوه 😄", "تأمر يا باشا 🫡", "أنا هنا ⚡"],
    "والله":       ["والله الله 😂", "صح 👍", "😄"],
    "ليه":         ["سؤال كبير 🤔", "ليه؟ 😂", "والله ما أعرف 😅"],
    "حلو":         ["ومنك للبنين 😂", "إنت الأحلى ❤️", "😄✨"],
    "جميل":        ["ومنك 😄", "الله يجمّلك ✨", "إنت الأجمل 😂"],
    "بكره":        ["إن شاء الله 🌟", "بكره حلو 😄", "ربنا يوفق ✨"],
    "صح":          ["صح 💯", "بالظبط 👍", "أيوه 😄"],
    "غلط":         ["مش صح 😅", "لأ يا عم 😂", "راجع كلامك 😄"],
    "عاوز":        ["قول اللي عاوزه 😄", "تأمر 🫡", "أيوه؟ 👂"],
    "محتاج":       ["أنا هنا يا صاحبي 😄", "قول اللي محتاجه 👂", "تفضل 🛠️"],
    "احسن":        ["أيوه أحسن 👍", "صح كلامك 💯", "بالظبط 😄"],
    "ياريت":       ["إن شاء الله 🙏", "ربنا يكرم 🌟", "آمين 🤲"],
    "حياتي":       ["والله وحياتي كمان 😂❤️", "إنت الأحلى 😄", "يا سلام ❤️"],
    "بيحصل":       ["إيه اللي بيحصل؟ 👀", "قولي أكتر 😄", "حصل إيه؟ 🤔"],
}

def load_data():
    saved = load_json(DATA_FILE, {})    result = {k: list(v) for k, v in DEFAULT_RESPONSES.items()}
    for k, v in saved.items():
        result[k] = v if isinstance(v, list) else [v]
    return result

def save_data(data):
    custom = {k: v for k, v in data.items() if k not in DEFAULT_RESPONSES}
    save_json(DATA_FILE, custom)

responses = load_data()

# ══════════════════════════════════════════
#  نظام التعلم من أسلوب الأشخاص
# ══════════════════════════════════════════
def learn_from_message(message):
    if not message.text or len(message.text) < 4:
        return
    uid  = str(message.from_user.id)
    name = message.from_user.first_name or "مجهول"
    text = message.text.strip()
    if text.startswith('/') or text.startswith('أضف') or text.startswith('قول'):
        return
    if uid not in learned_styles:
        learned_styles[uid] = {"name": name, "phrases": [], "words": [], "count": 0}
    learned_styles[uid]["name"]  = name
    learned_styles[uid]["count"] = learned_styles[uid].get("count", 0) + 1
    phrases = learned_styles[uid]["phrases"]
    phrases.append(text)
    if len(phrases) > 40:
        phrases.pop(0)
    words = [w for w in text.split() if len(w) > 3]
    learned_styles[uid]["words"].extend(words)
    if len(learned_styles[uid]["words"]) > 200:
        top = [w for w, _ in Counter(learned_styles[uid]["words"]).most_common(80)]
        learned_styles[uid]["words"] = top
    save_json(LEARN_FILE, learned_styles)

def mimic_user(uid):
    uid = str(uid)
    if uid not in learned_styles or not learned_styles[uid]["phrases"]:
        return None
    d      = learned_styles[uid]
    name   = d["name"]
    phrase = random.choice(d["phrases"])
    return random.choice([
        f"😂 {name} كان بيقول: \"{phrase}\"",
        f"👀 فاكر لما {name} قال: \"{phrase}\" ؟",
        f"📜 ده كلام {name}: \"{phrase}\" 😂",
        f"🎤 {name} قالها: \"{phrase}\" 😂",
    ])
# ══════════════════════════════════════════
#  ريأكت إيموجي ذكي وصامت
# ══════════════════════════════════════════
REACT_RULES = [
    (["ههه","هههه","😂","😹","🤣","خخخ","wkwk","lol","مضحك","نكتة"],   0.65, ["😂","🤣","💀","😭"]),
    (["حلو","جميل","رائع","عظيم","ممتاز","برافو","ولا أجمل"],            0.55, ["❤️","🔥","👏","✨","💯"]),
    (["تعبان","زهقت","مللت","تعبت","صعب","حزين","زعلان"],               0.55, ["❤️","🤗","💙","😔","🫂"]),
    (["والله","الحمد لله","ان شاء الله","بسم الله","ربنا"],              0.45, ["🙏","❤️","🤲","✨"]),
    (["صح","بالظبط","معاك حق","أيوه"],                                  0.50, ["👍","✅","💯","🫡"]),
    (["شكرا","مشكور","يسلمو"],                                           0.50, ["🤝","❤️","🙏"]),
    (["اكل","هنتكل","عزومة","فطار","عشا"],                              0.50, ["😋","🍽️","🤤","👀"]),
    (["نوم","بنام","تصبح على خير"],                                      0.45, ["😴","🌙","💤"]),
    (["بحبك","بحبكم","بحبو"],                                            0.55, ["❤️","🥰","😍","🫶"]),
    (["مبروك","يسعدك","الله يهنيك"],                                    0.60, ["🎉","🥳","❤️","✨"]),
]

def try_react(message):
    if not message.text:
        return
    text = message.text.lower()
    for keywords, chance, emojis in REACT_RULES:
        if any(k in text for k in keywords):
            if random.random() < chance:
                try:
                    bot.set_message_reaction(
                        message.chat.id,
                        message.message_id,
                        [telebot.types.ReactionTypeEmoji(random.choice(emojis))]
                    )
                except:
                    pass
                return

# ══════════════════════════════════════════
#  تحليل المزاج الذكي (Mood Detection)
# ══════════════════════════════════════════
MOOD_MAP = {
    "joy":      ["ههه", "😂", "فرح", "سعيد", "مبسوط", "ضحك", "جميل", "حلو", "هههه", "خخخ", "lol", "مضحك", "يا راجل", "عظيم"],
    "sadness":  ["حزين", "زعلان", "تعبان", "اكتئاب", "هم", "حزن", "😢", "💔", "مكتئب", "وحيد", "ملل", "مخنوق", "مضغوط", "أحتاج"],
    "love":     ["بحبك", "حب", "رومانسي", "حبيبي", "عمري", "❤️", "🥰", "اشتقت", "حبيبتي", "رومانسية", "غزل", "قلبي", "نور عيني", "عشقي"],
    "anger":    ["غاضب", "مضايق", "😡", "غصب", "زهق", "كفاية", "مقرف", "حرام", "غبي", "مش فاهم"],
    "wisdom":   ["نصيحة", "حكمة", "رأيك", "فكر", "تحفيز", "طموح", "مستقبل", "نجاح", "هدف", "تجربة", "عبرة"],
}

def detect_mood(text):
    text = text.lower()
    scores = {mood: sum(1 for k in keywords if k in text) for mood, keywords in MOOD_MAP.items()}
    best_mood = max(scores, key=scores.get)
    return best_mood if scores[best_mood] > 0 else "neutral"
# ══════════════════════════════════════════
#  نظام الذكاء الاصطناعي (Grok API)
# ══════════════════════════════════════════
SYSTEM_BASE = (
    "أنت AKRO Bot، ذكي جداً، اجتماعي، وتفهم المشاعر البشرية بعمق. "
    "ترد دائماً بجمل عربية طويلة، غنية بالمعاني، ومناسبة تماماً لسياق الحديث. "
    "لا ترد بجمل قصيرة أو سطحية أبداً. استخدم اللغة المصرية العامية أو الفصحى بسلاسة حسب أسلوب المستخدم. "
    "كن ذكياً في الرد، أضف لمسات من الحكمة أو الفكاهة أو الدعم العاطفي حسب الحالة. "
    "تجنب الروبوتية، تحدث كأنك صديق مقرب أو مستشار حكيم."
)

MOOD_PROMPTS = {
    "joy":      "\nالمستخدم في حالة فرح أو ضحك. رد برد مرح، خفيف، مليء بالطاقة الإيجابية، واجعل الجمل طويلة ومفعمة بالحماس.",
    "sadness":  "\nالمستخدم حزين أو مكتئب أو متعب. رد برد دافئ، متفهم، مطمئن، واجعل الجمل طويلة وتحتوي على دعم نفسي حقيقي وكلام يبعث الأمل.",
    "love":     "\nالمستخدم يتحدث عن الحب أو الرومانسية. رد برد شاعري، رقيق، عميق المشاعر، واجعل الجمل طويلة وجميلة تناسب الغزل والحب الراقي.",
    "anger":    "\nالمستخدم غاضب أو متضايق. رد برد هادئ، متزن، حكيم، واجعل الجمل طويلة وتفكك التوتر بلطف دون تجريح أو استفزاز.",
    "wisdom":   "\nالمستخدم يبحث عن نصيحة أو حكمة أو تحفيز. رد برد فلسفي، عميق، مدعوم بأمثلة أو تشبيهات، واجعل الجمل طويلة ومحفزة.",
    "neutral":  "\nالمستخدم يتحدث بشكل عادي. رد برد ذكي، منطقي، وجذاب، واجعل الجمل طويلة وغنية بالمعلومات أو الملاحظات الذكية."
}

def ask_grok(user_text, mood, history):
    system_prompt = SYSTEM_BASE + MOOD_PROMPTS.get(mood, "")
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})

    payload = {
        "model": GROK_MODEL,
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 400
    }
    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.post(GROK_API_URL, json=payload, headers=headers, timeout=15)
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# ══════════════════════════════════════════
#  ردود قصيرة وذكية (Fallback)
# ══════════════════════════════════════════
LAUGH_REPLIES = ["😂💀", "يموت 😂", "ده إيه 😂", "جاب جاب 💀", "خلاص 😂", "متكسرش 😂", "مش قادر 😂", "يا عيني 😭😂", "جمدت 😂"]
RANDOM_REMARKS = ["😂 ركزوا", "👀 شايف كل حاجة", "يا رغيكم 😂", "تحفة الجروب ده 😂", "بلاش رغي 😤", "وبعدين؟ 😂", "أيوه أيوه 😂", "😂 كمّلوا", "بسمعكم 🕵️"]INSULT_REPLIES = ["ربنا يهديك 😂", "ماشي يا عم 😂", "أنا بوت مش حاسس 😂", "تمام يا فندم 😅", "معلش 😂"]
GREET_EXTRAS = ["نورت ⚡", "أهلاً أهلاً 🎉", "البطل وصل 👑", "يا هلا 😄", "شرفتنا 🫡", "الكبير بيطل 😎", "يا فرحتي 🥳", "وصل الأسطى 😄", "نورتنا 🌟"]

# ══════════════════════════════════════════
#  ألوان QuotLy & أوامر أخرى (محتفظ بها كما هي)
# ══════════════════════════════════════════
QUOTE_COLORS = ["red","blue","green","purple","orange","pink","white","random","#cbafff","#ff6b6b","#4ecdc4","#ffd700","#00bcd4","#e91e63"]
COLOR_MAP = {"احمر":"red","أحمر":"red","ازرق":"blue","أزرق":"blue","اخضر":"green","أخضر":"green","بنفسجي":"purple","برتقالي":"orange","وردي":"pink","ابيض":"white","أبيض":"white","اسود":"black","أسود":"black","عشوائي":"random","ذهبي":"#ffd700","سماوي":"#00bcd4","زهري":"#e91e63"}
QUOTE_INTROS = ["لازم يتحفظ ده 😂", "تاريخ بيُكتب 😂", "شايفك وشايف كلامك 👀", "اقتباس واجب 😂", "للأجيال الجاية 😂", "هيتحفظ للأبد 📜", "فلاش نيوز ⚡😂"]

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "صاحبي"
    bot.reply_to(message, f"أهلاً يا {name}! 👋\nأنا AKRO Bot v5.0 ⚡\nمتصل بذكاء Grok AI، بأفهم مزاجك وأرد عليك بجمل طويلة وذكية.\n/help للأوامر")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message,
        "🤖 *أوامر البوت:*\n\n"
        "📝 `أضف: كلمة = الرد`\n"
        "🗣️ `قول أي كلام`\n"
        "👤 `عرف عماد: هو صاحبي`\n"
        "🔍 `مين عماد`\n"
        "🎨 `اقتبس` — رد على رسالة\n"
        "🎨 `اقتبس احمر/ازرق/وردي/ذهبي`\n"
        "🧠 `/mimic اسم` — يقلد شخص\n"
        "📋 `/list` · `/del كلمة` · `/stats`\n"
        "👥 `/people` · `/delperson اسم`\n"
        "💡 *تحدث طبيعي وسأرد بذكاء حسب مزاجك!*",
        parse_mode='Markdown')

@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not responses: return bot.reply_to(message, "📭 مفيش ردود!")
    items = list(responses.items())
    for i in range(0, len(items), 20):
        chunk = items[i:i+20]
        txt = f"📋 *الردود ({i+1}–{i+len(chunk)}):*\n\n"
        for j, (k, v) in enumerate(chunk, i+1):
            sample = v[0] if isinstance(v, list) else v
            sv = sample[:35] + "..." if len(sample) > 35 else sample
            txt += f"{j}. `{k}` ← {sv}\n"
        bot.send_message(message.chat.id, txt, parse_mode='Markdown')
        time.sleep(0.2)

@bot.message_handler(commands=['del'])
def del_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ `/del الكلمة`", parse_mode='Markdown')
    key = parts[1].strip().lower()    if key in responses:
        del responses[key]; save_data(responses)
        bot.reply_to(message, f"🗑️ حُذف `{key}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش `{key}`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    custom = sum(1 for k in responses if k not in DEFAULT_RESPONSES)
    bot.reply_to(message, f"📊 *إحصائيات:*\nردود: `{len(responses)}` (مضاف: `{custom}`)\nأشخاص: `{len(people_db)}`\nمتعلم من: `{len(learned_styles)}` شخص\n⚡ شغال تمام!", parse_mode='Markdown')

@bot.message_handler(commands=['people'])
def people_cmd(message):
    if not people_db: return bot.reply_to(message, "📭 مفيش أشخاص! `عرف اسم: معلومات`", parse_mode='Markdown')
    txt = f"👥 *الأشخاص ({len(people_db)}):*\n\n"
    for i, (_, p) in enumerate(people_db.items(), 1):
        short = p['info'][:45] + "..." if len(p['info']) > 45 else p['info']
        txt += f"{i}. *{p['name']}* — {short}\n"
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(commands=['delperson'])
def delperson_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ `/delperson الاسم`", parse_mode='Markdown')
    key = parts[1].strip().lower()
    if key in people_db:
        name = people_db[key]['name']
        del people_db[key]; save_json(PEOPLE_FILE, people_db)
        bot.reply_to(message, f"🗑️ حُذف *{name}*", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش *{key}*", parse_mode='Markdown')

@bot.message_handler(commands=['mimic'])
def mimic_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ `/mimic اسم`", parse_mode='Markdown')
    q = parts[1].strip().lower()
    found = next(((uid, d) for uid, d in learned_styles.items() if q in d["name"].lower()), None)
    if not found: return bot.reply_to(message, f"🤷 معرفش أسلوب *{q}* لسه!", parse_mode='Markdown')
    uid, _ = found
    result = mimic_user(uid)
    bot.reply_to(message, result if result else "😅 مش كاتب كتير!")

@bot.message_handler(commands=['mystyle'])
def mystyle_cmd(message):
    uid = str(message.from_user.id)
    name = message.from_user.first_name or "أنت"
    d = learned_styles.get(uid)
    if not d or d.get("count", 0) < 5: return bot.reply_to(message, "😅 اكتب أكتر في الجروب الأول!")
    top    = [w for w, _ in Counter(d["words"]).most_common(4)] if d["words"] else []    sample = random.choice(d["phrases"]) if d["phrases"] else "—"
    bot.reply_to(message, f"🧠 *أسلوب {name}:*\nرسائل: `{d['count']}`\nكلماتك: {', '.join(top) or '—'}\nمثال: _{sample}_", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and re.search(r'أضف\s*:', m.text))
def teach_bot(message):
    try:
        content = re.split(r'أضف\s*:', message.text, maxsplit=1)[1].strip()
        if "=" not in content: return bot.reply_to(message, "⚠️ `أضف: الكلمة = الرد`", parse_mode='Markdown')
        key, value = content.split("=", 1); key, value = key.strip().lower(), value.strip()
        if not key or not value: return
        existed = key in responses
        if existed and isinstance(responses[key], list):
            if value not in responses[key]: responses[key].append(value)
        else: responses[key] = [value]
        save_data(responses)
        bot.reply_to(message, f"{'✏️ محدّث' if existed else '✅ محفوظ'}: `{key}` ← {value}", parse_mode='Markdown')
    except Exception as e: bot.reply_to(message, f"❌ {e}")

@bot.message_handler(func=lambda m: m.text and re.match(r'^قول\s+.+', m.text.strip()))
def say_direct(message):
    txt = re.sub(r'^قول\s+', '', message.text.strip(), count=1).strip()
    if txt: bot.reply_to(message, txt)

@bot.message_handler(func=lambda m: m.text and re.match(r'^عرف\s+.+\s*:', m.text.strip()))
def add_person(message):
    match = re.match(r'^عرف\s+(.+?)\s*:\s*(.+)$', message.text.strip(), re.DOTALL)
    if not match: return bot.reply_to(message, "⚠️ `عرف الاسم: المعلومات`", parse_mode='Markdown')
    name, info = match.group(1).strip(), match.group(2).strip()
    people_db[name.lower()] = {"name": name, "info": info}; save_json(PEOPLE_FILE, people_db)
    bot.reply_to(message, f"{'✏️ محدّث' if name.lower() in people_db else '✅ محفوظ'} *{name}* 👤", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and re.match(r'^مين\s+\S+', m.text.strip()))
def who_is(message):
    query = re.sub(r'^مين\s+', '', message.text.strip(), count=1).strip().lower()
    p = people_db.get(query) or next((v for k, v in people_db.items() if query in k), None)
    if p: bot.reply_to(message, f"👤 *{p['name']}*\n{p['info']}", parse_mode='Markdown')
    else: bot.reply_to(message, f"🤷 ما عرفش مين *{query}*\n`عرف {query}: معلومات`", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and re.match(r'^اقتبس', m.text.strip()))
def quote_handler(message):
    if not message.reply_to_message:
        return bot.reply_to(message, "⚠️ رد على الرسالة اللي عايز تقتبسها\nثم اكتب `اقتبس` أو `اقتبس احمر` أو `اقتبس ذهبي` 😄", parse_mode='Markdown')
    try:
        target = message.reply_to_message
        parts  = message.text.strip().split()
        color  = random.choice(QUOTE_COLORS); is_img = False; keep_r = False
        for p in parts[1:]:
            if p in COLOR_MAP: color = COLOR_MAP[p]
            elif p.startswith("#"): color = p
            elif p in ["صورة","img","png"]: is_img = True            elif p in ["مع","رد"]: keep_r = True
        flags = " ".join(filter(None, ["i" if is_img else "", "r" if keep_r else ""])).strip()
        q_cmd = f"/q {color} {flags}".strip()
        sender = target.from_user.first_name or "حد"
        intro = random.choice([f"😂 {sender} قالها!", f"👀 {sender} قال إيه؟ 😂", f"📜 {sender}: {random.choice(QUOTE_INTROS)}", f"💀 {sender} قالها وراح 😂", f"⚡ {sender} جاب كلام تاريخي 😂"])
        bot.reply_to(message, intro); time.sleep(0.4)
        bot.send_message(message.chat.id, q_cmd, reply_to_message_id=target.message_id)
    except Exception as e: bot.reply_to(message, f"❌ {e}")

# ══════════════════════════════════════════
#  المعالج الرئيسي — ذكي ومندمج مع Grok AI
# ══════════════════════════════════════════
@bot.message_handler(func=lambda message: True)
def reply_main(message):
    if not message.text: return

    learn_from_message(message)
    try_react(message)

    text = message.text.lower().strip()
    uid  = str(message.from_user.id)
    name = message.from_user.first_name or ""

    # ① ضحك سريع
    if any(x in text for x in ["ههه","هههه","wkwk","lol","😂","😹","🤣","خخخ","خخ"]):
        bot.reply_to(message, random.choice(LAUGH_REPLIES))
        if random.random() < 0.15:
            time.sleep(0.7); bot.send_message(message.chat.id, f"/q {random.choice(QUOTE_COLORS)}", reply_to_message_id=message.message_id)
        return

    # ② تحية
    if any(g in text for g in ["يا بوت","هاي","هلو","أهلا","سلام عليكم","هلا"]):
        bot.reply_to(message, f"{name}! {random.choice(GREET_EXTRAS)}")
        return

    # ③ سؤال عن البوت
    if any(x in text for x in ["مين إنت","مين انت","انت مين","إنت مين","ايه وظيفتك","بتعمل ايه"]):
        bot.reply_to(message, "أنا AKRO Bot v5.0 ⚡ متصل بذكاء Grok AI، بأفهمك وأرد عليك بجمل طويلة وذكية حسب حالتك. /help")
        return

    # ④ قاموس سريع
    for key, value in responses.items():
        if key.lower() in text:
            reply = random.choice(value) if isinstance(value, list) else value
            bot.reply_to(message, reply)
            return

    # ⑤ شتايم
    if any(b in text for b in ["احا","عيل","غبي","بوت وسخ","مش بيشتغل","خربان","بايظ","زباله"]):
        bot.reply_to(message, random.choice(INSULT_REPLIES))        return

    # ⑥ محاكاة عشوائية (2%)
    if random.random() < 0.02 and learned_styles:
        uid_rand = random.choice(list(learned_styles.keys()))
        msg = mimic_user(uid_rand)
        if msg: bot.send_message(message.chat.id, msg); return

    # ⑦ تعليق عشوائي (1%)
    if random.random() < 0.01:
        bot.send_message(message.chat.id, random.choice(RANDOM_REMARKS))
        return

    # 🌟 ⑧ الذكاء الاصطناعي (Grok)
    mood = detect_mood(text)
    update_context(uid, "user", message.text)
    history = user_contexts.get(uid, [])

    bot.send_chat_action(message.chat.id, "typing")
    ai_reply = ask_grok(message.text, mood, history)

    if ai_reply:
        bot.reply_to(message, ai_reply)
        update_context(uid, "assistant", ai_reply)
    else:
        # Fallback ذكي إذا فشل الاتصال
        fallbacks = [
            f"يا {name}، الموضوع ده محتاج تركيز أكتر، بس أنا هنا معاك في أي وقت 😄",
            "كلامك جميل وواضح، خليني أفكر فيه شوية وأرد عليك أحسن رد ممكن 😉",
            "أنا بسمعك كويس، وردّي هيجي مفصل ومناسب للكلام ده بالظبط 🌟",
            "ده موضوع مهم، وأنا دايماً بحاول أرد بذكاء وعمق زي ما تستاهل 💡"
        ]
        bot.reply_to(message, random.choice(fallbacks))

# ══════════════════════════════════════════
#  تشغيل
# ══════════════════════════════════════════
print("🚀 AKRO BOT v5.0 — Grok AI Edition is Online!")
print(f"📦 ردود: {len(responses)} | 👥 أشخاص: {len(people_db)} | 🧠 متعلم: {len(learned_styles)}")
print("💡 تأكد من وضع GROK_API_KEY في المتغيرات البيئية أو في أعلى الكود")

bot.infinity_polling(timeout=60, long_polling_timeout=60)
