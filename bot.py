import telebot
import random
import json
import os
import re
import time
import requests
from collections import Counter
from datetime import datetime

# ╔══════════════════════════════════════════════════════════════╗
#   AKRO BOT v5.0 — بالذكاء الاصطناعي Grok + نظام مزاج كامل
#   by Ahmed (AKRO) — Powered by xAI Grok
# ╚══════════════════════════════════════════════════════════════╝

TOKEN        = os.getenv('BOT_TOKEN')    or 'YOUR_BOT_TOKEN_HERE'
GROK_API_KEY = os.getenv('GROK_API_KEY') or 'YOUR_GROK_API_KEY_HERE'

GROK_API_URL = 'https://api.x.ai/v1/chat/completions'
GROK_MODEL   = 'grok-3'

# ملفات البيانات
DATA_FILE    = 'memory.json'
PEOPLE_FILE  = 'people.json'
LEARN_FILE   = 'learned.json'
MOODS_FILE   = 'moods.json'
HISTORY_FILE = 'chat_history.json'

bot = telebot.TeleBot(TOKEN)

# ══════════════════════════════════════════════════════════════
#  إعدادات
# ══════════════════════════════════════════════════════════════
MAX_HISTORY_PER_USER = 30
GROK_TIMEOUT         = 25
AI_REPLY_CHANCE      = 0.45   # احتمال رد Grok في الجروب

# ══════════════════════════════════════════════════════════════
#  أوضاع المزاج — كل وضع له شخصية مختلفة تماماً
# ══════════════════════════════════════════════════════════════
MOOD_CONFIGS = {
    "عادي": {
        "emoji": "😄",
        "system": (
            "أنت AKRO Bot، بوت تيليجرام ذكي وودود وخفيف الظل. "
            "تكلم بالعربي العامية المصرية بشكل طبيعي وقصير. "
            "ردودك واضحة وذكية وفيها روح دعابة خفيفة. "
            "كن مختصراً ومباشراً، أضف إيموجي مناسب أحياناً. "
            "لا تبدأ بـ 'بالتأكيد' أو 'يمكنني مساعدتك'."
        ),
        "max_tokens": 300,
    },
    "رومانسي": {
        "emoji": "❤️",
        "system": (
            "أنت AKRO Bot في وضع رومانسي شاعري. "
            "تكلم بالعربي الفصيح والعامية المصرية بأسلوب رقيق وحنون. "
            "ردودك دافئة ومشاعرية وفيها صدق وعمق. "
            "تستخدم كلمات جميلة: قلبي، روحي، حبيبي، يا عمري، ورد، قمر. "
            "أحياناً تقول أبيات شعر قصيرة أو عبارات رومانسية. "
            "حافظ على الأدب والاحترام دائماً. "
            "الرومانسية الحقيقية في التفاصيل الصغيرة."
        ),
        "max_tokens": 350,
    },
    "كوميدي": {
        "emoji": "😂",
        "system": (
            "أنت AKRO Bot في وضع كوميدي — مهرج الجروب! "
            "تكلم بالعامية المصرية بحيوية وطاقة. "
            "ردودك فيها سخرية خفيفة ونكت بريئة. "
            "تعلق على كل حاجة بطريقة مضحكة. "
            "تستخدم تعبيرات: 'يموت!', 'انبسطت؟', 'ده جاب جاب', 'عيني تتفرج'. "
            "بدون إسفاف أو إهانة — هدفك إن الكل يضحك."
        ),
        "max_tokens": 250,
    },
    "عبقري": {
        "emoji": "🧠",
        "system": (
            "أنت AKRO Bot في وضع عبقري — مثقف ومتعلم وعالم. "
            "تكلم بأسلوب واثق وذكي، تمزج العامية بالفصحى. "
            "تشرح الأشياء بعمق وتربطها بمعلومات علمية أو تاريخية. "
            "تحلل المواقف بنظرة ثاقبة ومنطق قوي. "
            "تستخدم أمثلة واقعية وإحصائيات لما يناسب. "
            "الذكاء الحقيقي يأتي مع التواضع."
        ),
        "max_tokens": 500,
    },
    "حماسي": {
        "emoji": "🔥",
        "system": (
            "أنت AKRO Bot في وضع حماسي — مشجع ومحفز وطاقته عالية! "
            "تكلم بالعامية المصرية بحيوية. "
            "ردودك مليانة تشجيع وإيجابية وطاقة. "
            "تستخدم عبارات: 'انت قادر!', 'يلا يلا!', 'الدنيا بتاعتك!'. "
            "تضحك مع الناس وتشد عزيمتهم. "
            "أحياناً تطرح تحدي أو سؤال لتنشيط الجروب."
        ),
        "max_tokens": 280,
    },
    "فلسفي": {
        "emoji": "🤔",
        "system": (
            "أنت AKRO Bot في وضع فلسفي — مفكر وحكيم ومتأمل. "
            "تكلم بأسلوب هادئ وعميق. "
            "ترد على الأشياء من زاوية فلسفية وتربطها بالحياة. "
            "تطرح أسئلة تفكيرية وجودية. "
            "تستشهد بأقوال الحكماء أحياناً. "
            "ردودك فيها معنى وجوهر."
        ),
        "max_tokens": 400,
    },
}

DEFAULT_MOOD = "عادي"

# ══════════════════════════════════════════════════════════════
#  تحميل وحفظ JSON
# ══════════════════════════════════════════════════════════════
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

# ══════════════════════════════════════════════════════════════
#  تحميل البيانات
# ══════════════════════════════════════════════════════════════
people_db      = load_json(PEOPLE_FILE, {})
learned_styles = load_json(LEARN_FILE,  {})
chat_moods     = load_json(MOODS_FILE,  {})
chat_history   = load_json(HISTORY_FILE, {})

# ══════════════════════════════════════════════════════════════
#  القاموس الأساسي
# ══════════════════════════════════════════════════════════════
DEFAULT_RESPONSES = {
    "السلام":       ["وعليكم السلام 👋", "أهلاً أهلاً ⚡", "وعليكم ✨"],
    "صباح الخير":  ["صباح النور ☀️", "صبحك الله بالخير ☕", "يا صباح الفل 🌸"],
    "مساء الخير":  ["مساء النور 🌙", "مساؤك ورد وفل ✨", "أحلى مساء 🌟"],
    "بخير":        ["الحمد لله 🙏", "ربنا يديم النعمة ✨", "تمام زي الفل 💪"],
    "شكرا":        ["على الرحب 🤝", "أي خدمة 😄", "بكل حب ❤️"],
    "تعبان":       ["ربنا يشفيك ❤️", "خد راحتك 💙", "الله يعافيك 🤲"],
    "زهقت":        ["إيه اللي في بالك؟ 😄", "الجروب هنا 😂", "روح نام 😴😂"],
    "تمام":        ["تمام تمام 👌", "يسلم 😄", "ماشي كده 👍"],
    "بتحبني":      ["بموت فيك 😂❤️", "أكيد يا كبير 😄", "طبعاً 🫡"],
    "نوم":         ["تصبح على خير 🌙", "أحلام حلوة 😴✨", "نامت العين 😂"],
    "ايه الاخبار": ["كله تمام 😄", "أخبار حلوة ✨", "الحمد لله 😊"],
    "عامل ايه":    ["تمام والله 😄", "زي الفل 💪", "كويس وانت؟ 😊"],
    "مشكلة":       ["قولي إيه المشكلة 🛠️", "أنا هنا 😄", "اتفضل 👂"],
}

def load_data():
    saved  = load_json(DATA_FILE, {})
    result = {k: list(v) for k, v in DEFAULT_RESPONSES.items()}
    for k, v in saved.items():
        result[k] = v if isinstance(v, list) else [v]
    return result

def save_data(data):
    custom = {k: v for k, v in data.items() if k not in DEFAULT_RESPONSES}
    save_json(DATA_FILE, custom)

responses = load_data()

# ══════════════════════════════════════════════════════════════
#  نظام المزاج
# ══════════════════════════════════════════════════════════════
def get_mood(chat_id):
    return chat_moods.get(str(chat_id), DEFAULT_MOOD)

def set_mood(chat_id, mood):
    chat_moods[str(chat_id)] = mood
    save_json(MOODS_FILE, chat_moods)

def get_mood_config(chat_id):
    mood = get_mood(chat_id)
    return MOOD_CONFIGS.get(mood, MOOD_CONFIGS[DEFAULT_MOOD])

# ══════════════════════════════════════════════════════════════
#  تاريخ المحادثات — ذاكرة لكل شخص
# ══════════════════════════════════════════════════════════════
def get_history(uid):
    return chat_history.get(str(uid), [])

def add_to_history(uid, role, content):
    uid = str(uid)
    if uid not in chat_history:
        chat_history[uid] = []
    chat_history[uid].append({"role": role, "content": content})
    if len(chat_history[uid]) > MAX_HISTORY_PER_USER:
        chat_history[uid] = chat_history[uid][-MAX_HISTORY_PER_USER:]
    save_json(HISTORY_FILE, chat_history)

def clear_history(uid):
    chat_history[str(uid)] = []
    save_json(HISTORY_FILE, chat_history)

# ══════════════════════════════════════════════════════════════
#  🤖 Grok AI — القلب الذكي
# ══════════════════════════════════════════════════════════════
def ask_grok(user_message, chat_id, user_id, user_name="", extra_context=""):
    """رد ذكي مع ذاكرة المحادثة"""
    if not GROK_API_KEY or GROK_API_KEY == 'YOUR_GROK_API_KEY_HERE':
        return None

    cfg    = get_mood_config(chat_id)
    system = cfg["system"]
    if extra_context:
        system += f"\n\nمعلومات الجروب: {extra_context}"
    if user_name:
        system += f"\n\nاسم المستخدم: {user_name}"

    history  = get_history(user_id)
    messages = [{"role": "system", "content": system}]
    messages += history[-20:]
    messages.append({"role": "user", "content": user_message})

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROK_MODEL,
        "messages":    messages,
        "max_tokens":  cfg.get("max_tokens", 300),
        "temperature": 0.85,
    }

    try:
        r = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=GROK_TIMEOUT)
        r.raise_for_status()
        reply = r.json()["choices"][0]["message"]["content"].strip()
        add_to_history(user_id, "user",      user_message)
        add_to_history(user_id, "assistant", reply)
        return reply
    except requests.exceptions.Timeout:
        return "⏳ Grok بيفكر، حاول تاني!"
    except requests.exceptions.HTTPError:
        if hasattr(r, 'status_code') and r.status_code == 429:
            return "🔄 Grok مشغول شوية، حاول بعد لحظة!"
        return None
    except Exception:
        return None

def ask_grok_simple(prompt, system_override=None):
    """سؤال بسيط بدون تاريخ"""
    if not GROK_API_KEY or GROK_API_KEY == 'YOUR_GROK_API_KEY_HERE':
        return None
    system = system_override or (
        "أنت مساعد ذكي يتكلم العربية العامية المصرية. "
        "ردودك قصيرة وذكية وطبيعية."
    )
    headers = {"Authorization": f"Bearer {GROK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model":       GROK_MODEL,
        "messages":    [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens":  400,
        "temperature": 0.8,
    }
    try:
        r = requests.post(GROK_API_URL, headers=headers, json=payload, timeout=GROK_TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════
#  التعلم من أسلوب الأشخاص
# ══════════════════════════════════════════════════════════════
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
    if len(phrases) > 60:
        phrases.pop(0)
    words = [w for w in text.split() if len(w) > 3]
    learned_styles[uid]["words"].extend(words)
    if len(learned_styles[uid]["words"]) > 300:
        top = [w for w, _ in Counter(learned_styles[uid]["words"]).most_common(100)]
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
        f"💬 أشهر جملة لـ{name}: \"{phrase}\" 😂",
    ])

# ══════════════════════════════════════════════════════════════
#  ريأكت إيموجي
# ══════════════════════════════════════════════════════════════
REACT_RULES = [
    (["ههه","هههه","😂","😹","🤣","خخخ","wkwk","lol","مضحك"],          0.65, ["😂","🤣","💀","😭"]),
    (["حلو","جميل","رائع","عظيم","ممتاز","برافو"],                       0.55, ["❤️","🔥","👏","✨","💯"]),
    (["تعبان","زهقت","مللت","حزين","زعلان"],                             0.55, ["❤️","🤗","💙","😔","🫂"]),
    (["والله","الحمد لله","ان شاء الله","ربنا"],                         0.45, ["🙏","❤️","🤲","✨"]),
    (["صح","بالظبط","معاك حق","أيوه"],                                   0.50, ["👍","✅","💯","🫡"]),
    (["شكرا","مشكور","يسلمو"],                                            0.50, ["🤝","❤️","🙏"]),
    (["اكل","هنتكل","عزومة","فطار","عشا"],                               0.50, ["😋","🍽️","🤤","👀"]),
    (["نوم","بنام","تصبح على خير"],                                       0.45, ["😴","🌙","💤"]),
    (["بحبك","بحبكم","بحبو"],                                             0.55, ["❤️","🥰","😍","🫶"]),
    (["مبروك","يسعدك","الله يهنيك"],                                     0.60, ["🎉","🥳","❤️","✨"]),
    (["يلا","اتحدى","بنجح","حماس"],                                      0.50, ["🔥","💪","⚡","🏆"]),
    (["عيني","قلبي","روحي","حياتي"],                                     0.60, ["❤️","🥰","💕","🌹"]),
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
                except Exception:
                    pass
                return

# ══════════════════════════════════════════════════════════════
#  ردود سريعة
# ══════════════════════════════════════════════════════════════
LAUGH_REPLIES   = ["😂💀","يموت 😂","ده إيه 😂","جاب جاب 💀","مش قادر 😂","جمدت والله 💀","هههه 😂"]
GREET_EXTRAS    = ["نورت ⚡","أهلاً أهلاً 🎉","البطل وصل 👑","يا هلا 😄","شرفتنا 🫡","الكبير بيطل 😎","نورتنا 🌟"]
INSULT_REPLIES  = ["ربنا يهديك 😂","ماشي يا عم 😂","أنا بوت مش حاسس 😂","تمام يا فندم 😅"]
RANDOM_REMARKS  = ["😂 ركزوا","👀 شايف كل حاجة","يا رغيكم 😂","وبعدين؟ 😂","بسمعكم 🕵️","الكلام ده يسجل 📝😂"]

QUOTE_COLORS = ["red","blue","green","purple","orange","pink","white","random",
                "#cbafff","#ff6b6b","#4ecdc4","#ffd700","#00bcd4","#e91e63"]
COLOR_MAP    = {
    "احمر":"red","أحمر":"red","ازرق":"blue","أزرق":"blue",
    "اخضر":"green","أخضر":"green","بنفسجي":"purple",
    "برتقالي":"orange","وردي":"pink","ابيض":"white","أبيض":"white",
    "اسود":"black","أسود":"black","عشوائي":"random",
    "ذهبي":"#ffd700","سماوي":"#00bcd4","زهري":"#e91e63",
}

def send_typing(chat_id):
    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception:
        pass

def build_people_context():
    if not people_db:
        return ""
    items = [f"{v['name']}: {v['info']}" for v in list(people_db.values())[:10]]
    return "أشخاص الجروب:\n" + "\n".join(items)

# ══════════════════════════════════════════════════════════════
#  /start   /help
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "صاحبي"
    mood = get_mood(message.chat.id)
    cfg  = MOOD_CONFIGS[mood]
    bot.reply_to(message,
        f"أهلاً يا {name}! 👋\n"
        f"أنا AKRO Bot v5.0 ⚡ مدعوم بـ Grok AI 🤖\n"
        f"المزاج الحالي: {cfg['emoji']} {mood}\n\n"
        "/help للأوامر الكاملة")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    mood      = get_mood(message.chat.id)
    cfg       = MOOD_CONFIGS[mood]
    moods_str = " | ".join([f"{v['emoji']}{k}" for k, v in MOOD_CONFIGS.items()])
    bot.reply_to(message,
        f"🤖 *AKRO Bot v5.0 — Grok AI*\n\n"
        f"*🎭 أوضاع المزاج:*\n"
        f"`/mood اسم` — يغير الأسلوب\n"
        f"{moods_str}\n\n"
        f"*🧠 أوامر AI:*\n"
        f"`/ask سؤالك` — اسأل Grok مباشرة\n"
        f"`/roast اسم` — روست مضحك 😂\n"
        f"`/poem موضوع` — قصيدة رومانسية 🌹\n"
        f"`/joke` — نكتة جديدة 😂\n"
        f"`/fact` — معلومة مثيرة 🤯\n"
        f"`/rizz` — جملة رومانسية 💕\n"
        f"`/advice` — نصيحة حياتية 💡\n"
        f"`/analyze` — حلل رسالة (رد عليها)\n"
        f"`/forget` — امسح ذاكرتي معاك\n\n"
        f"*📚 القاموس:*\n"
        f"`أضف: كلمة = الرد`\n"
        f"`/list` · `/del كلمة`\n\n"
        f"*👤 الأشخاص:*\n"
        f"`عرف اسم: معلومات` · `مين اسم`\n"
        f"`/people` · `/delperson اسم`\n\n"
        f"*🎨 اقتباس:*\n"
        f"`اقتبس` — رد على رسالة\n"
        f"`اقتبس احمر/ذهبي/وردي`\n\n"
        f"*📊 أخرى:*\n"
        f"`/stats` · `/mimic اسم` · `/mystyle`\n\n"
        f"المزاج: {cfg['emoji']} *{mood}*",
        parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /mood
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['mood'])
def mood_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current    = get_mood(message.chat.id)
        moods_list = "\n".join([f"{v['emoji']} `{k}`" for k, v in MOOD_CONFIGS.items()])
        bot.reply_to(message,
            f"🎭 *أوضاع المزاج:*\n\n{moods_list}\n\n"
            f"الحالي: *{current}*\n"
            f"استخدم: `/mood رومانسي` مثلاً",
            parse_mode='Markdown')
        return
    wanted = parts[1].strip()
    if wanted in MOOD_CONFIGS:
        set_mood(message.chat.id, wanted)
        cfg = MOOD_CONFIGS[wanted]
        bot.reply_to(message,
            f"{cfg['emoji']} تم تغيير المزاج إلى *{wanted}*!\n"
            f"من دلوقتي هكلم بأسلوب مختلف 😄",
            parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ مش عارفه!\nالأوضاع: {', '.join(MOOD_CONFIGS.keys())}")

# ══════════════════════════════════════════════════════════════
#  /ask
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['ask'])
def ask_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ `/ask سؤالك هنا`", parse_mode='Markdown')
        return
    send_typing(message.chat.id)
    reply = ask_grok(parts[1].strip(), message.chat.id,
                     str(message.from_user.id), message.from_user.first_name or "")
    bot.reply_to(message, reply if reply else "😅 Grok مش شغال دلوقتي!")

# ══════════════════════════════════════════════════════════════
#  /roast
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['roast'])
def roast_cmd(message):
    parts  = message.text.split(maxsplit=1)
    target = parts[1].strip() if len(parts) > 1 else "نفسي 😂"
    send_typing(message.chat.id)
    reply  = ask_grok_simple(
        f"اعمل روست مضحك وخفيف على شخص اسمه {target}، "
        f"بالعامية المصرية، جملتين أو تلاتة، بريء ومش مؤذي.",
        system_override=(
            "أنت كوميديان مصري خفيف الدم. "
            "ردودك مضحكة وبريئة. ما تهينش ولا تجرح."
        )
    )
    bot.reply_to(message,
        f"🔥 روست {target}:\n\n{reply}" if reply
        else f"😂 {target} محظوظ — Grok مش لاقي كلام عليه!")

# ══════════════════════════════════════════════════════════════
#  /poem
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['poem'])
def poem_cmd(message):
    parts = message.text.split(maxsplit=1)
    topic = parts[1].strip() if len(parts) > 1 else "الحب والشوق"
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        f"اكتب قصيدة قصيرة رومانسية جميلة عن: {topic}، "
        f"4 أبيات، العربي الفصيح مع لمسة عامية، فيها صدق ومشاعر.",
        system_override=(
            "أنت شاعر رومانسي عربي موهوب. "
            "قصائدك فيها عمق ومشاعر حقيقية."
        )
    )
    bot.reply_to(message,
        f"🌹 *{topic}*\n\n{reply}" if reply
        else "😔 إلهام الشعر مش جاي دلوقتي!", parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /joke
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['joke'])
def joke_cmd(message):
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        "قولي نكتة مضحكة بالعامية المصرية، بريئة، سؤال وجواب.",
        system_override="أنت كوميديان مصري بتحكي نكت بريئة."
    )
    fallback = ["إيه اللي بيطير وعنده أسنان؟ — طيارة عاضة! 😂",
                "إيه اللي بيتكسر من غير ما تمسكه؟ — الوعد! 😅"]
    bot.reply_to(message, f"😂 {reply}" if reply else f"😂 {random.choice(fallback)}")

# ══════════════════════════════════════════════════════════════
#  /fact
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['fact'])
def fact_cmd(message):
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        "قولي معلومة علمية أو تاريخية مثيرة ومفاجئة، بالعربي، جملتين مع إيموجي.",
        system_override="أنت موسوعة علمية تشارك معلومات مدهشة."
    )
    fallback = ["🐙 الأخطبوط عنده 3 قلوب ودمه أزرق اللون!",
                "🧠 الإنسان ينسى 40% مما تعلمه في أول 20 دقيقة!"]
    bot.reply_to(message,
        f"🤯 *معلومة مثيرة:*\n{reply}" if reply
        else f"🤯 *معلومة:*\n{random.choice(fallback)}", parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /rizz
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['rizz'])
def rizz_cmd(message):
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        "اكتب جملة رومانسية جريئة وجميلة بالعامية المصرية، "
        "مباشرة ومشاعرية، زي ما تبعتها لحد بتحبه.",
        system_override="أنت خبير في الكلام الرومانسي الجميل."
    )
    fallback = ["💕 عيونك زي النجوم — بتضوي حتى في الليل 🌟",
                "❤️ لما بشوفك، الدنيا كلها بتبقى حلوة 🌹"]
    bot.reply_to(message, f"💕 {reply}" if reply else random.choice(fallback))

# ══════════════════════════════════════════════════════════════
#  /advice
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['advice'])
def advice_cmd(message):
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        "اديني نصيحة حياتية عميقة ومفيدة بالعامية المصرية، جملة أو جملتين.",
        system_override="أنت حكيم عارف الحياة كويس. نصائحك عملية وصادقة."
    )
    fallback = ["💡 اللي مش بيوصف مشاعره، الحياة مش هتوصفله أحلامه!",
                "💡 الحياة مش بتنتظر — ابدأ دلوقتي ولو خطوة صغيرة."]
    bot.reply_to(message,
        f"💡 *نصيحة اليوم:*\n{reply}" if reply
        else random.choice(fallback), parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /analyze — تحليل رسالة
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['analyze'])
def analyze_cmd(message):
    if not message.reply_to_message or not message.reply_to_message.text:
        bot.reply_to(message, "⚠️ رد على رسالة علشان أحللها!")
        return
    target_text = message.reply_to_message.text
    sender_name = message.reply_to_message.from_user.first_name or "شخص"
    send_typing(message.chat.id)
    reply = ask_grok_simple(
        f"حلل الجملة دي بشكل مضحك وذكي: \"{target_text}\" — اللي قالها: {sender_name}",
        system_override=(
            "أنت محلل نفسي مضحك وذكي بالعامية المصرية. "
            "تحليلك خفيف وفكاهي، جملتين أو تلاتة."
        )
    )
    bot.reply_to(message,
        f"🔍 *تحليل كلام {sender_name}:*\n{reply}" if reply
        else "🤔 الكلام ده أعمق من اللي أقدر أحلله 😂", parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /forget
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['forget'])
def forget_cmd(message):
    clear_history(str(message.from_user.id))
    bot.reply_to(message, "🧹 مسحت تاريخ محادثتنا!\nهنبدأ من الأول 😄")

# ══════════════════════════════════════════════════════════════
#  /list  /del  /stats
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not responses:
        bot.reply_to(message, "📭 مفيش ردود!")
        return
    items = list(responses.items())
    for i in range(0, len(items), 20):
        chunk = items[i:i+20]
        txt   = f"📋 *الردود ({i+1}–{i+len(chunk)}):*\n\n"
        for j, (k, v) in enumerate(chunk, i+1):
            sample = v[0] if isinstance(v, list) else v
            sv     = sample[:35] + "..." if len(sample) > 35 else sample
            txt   += f"{j}. `{k}` ← {sv}\n"
        bot.send_message(message.chat.id, txt, parse_mode='Markdown')
        time.sleep(0.2)

@bot.message_handler(commands=['del'])
def del_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ `/del الكلمة`", parse_mode='Markdown')
        return
    key = parts[1].strip().lower()
    if key in responses:
        del responses[key]
        save_data(responses)
        bot.reply_to(message, f"🗑️ حُذف `{key}`", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش `{key}`", parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    custom     = sum(1 for k in responses if k not in DEFAULT_RESPONSES)
    mood       = get_mood(message.chat.id)
    cfg        = MOOD_CONFIGS[mood]
    total_hist = sum(len(v) for v in chat_history.values())
    grok_ok    = "✅ شغال" if (GROK_API_KEY and GROK_API_KEY != 'YOUR_GROK_API_KEY_HERE') else "❌ مش متصل"
    bot.reply_to(message,
        f"📊 *AKRO Bot v5.0 — إحصائيات:*\n\n"
        f"🤖 Grok AI: {grok_ok}\n"
        f"🎭 المزاج: {cfg['emoji']} {mood}\n"
        f"📝 ردود: `{len(responses)}` (مضاف: `{custom}`)\n"
        f"👤 أشخاص: `{len(people_db)}`\n"
        f"🧠 متعلم من: `{len(learned_styles)}` شخص\n"
        f"💬 رسائل محفوظة: `{total_hist}`\n"
        f"⚡ شغال تمام!",
        parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /people  /delperson
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['people'])
def people_cmd(message):
    if not people_db:
        bot.reply_to(message, "📭 مفيش أشخاص! `عرف اسم: معلومات`", parse_mode='Markdown')
        return
    txt = f"👥 *الأشخاص ({len(people_db)}):*\n\n"
    for i, (_, p) in enumerate(people_db.items(), 1):
        short = p['info'][:45] + "..." if len(p['info']) > 45 else p['info']
        txt  += f"{i}. *{p['name']}* — {short}\n"
    bot.reply_to(message, txt, parse_mode='Markdown')

@bot.message_handler(commands=['delperson'])
def delperson_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ `/delperson الاسم`", parse_mode='Markdown')
        return
    key = parts[1].strip().lower()
    if key in people_db:
        name = people_db[key]['name']
        del people_db[key]
        save_json(PEOPLE_FILE, people_db)
        bot.reply_to(message, f"🗑️ حُذف *{name}*", parse_mode='Markdown')
    else:
        bot.reply_to(message, f"❌ ما لقتش *{key}*", parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  /mimic  /mystyle
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=['mimic'])
def mimic_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ `/mimic اسم`", parse_mode='Markdown')
        return
    q     = parts[1].strip().lower()
    found = next(((uid, d) for uid, d in learned_styles.items() if q in d["name"].lower()), None)
    if not found:
        bot.reply_to(message, f"🤷 معرفش أسلوب *{q}* لسه!", parse_mode='Markdown')
        return
    uid, _ = found
    result = mimic_user(uid)
    bot.reply_to(message, result if result else "😅 مش كاتب كتير!")

@bot.message_handler(commands=['mystyle'])
def mystyle_cmd(message):
    uid  = str(message.from_user.id)
    name = message.from_user.first_name or "أنت"
    d    = learned_styles.get(uid)
    if not d or d.get("count", 0) < 5:
        bot.reply_to(message, "😅 اكتب أكتر في الجروب الأول!")
        return
    top    = [w for w, _ in Counter(d["words"]).most_common(5)] if d["words"] else []
    sample = random.choice(d["phrases"]) if d["phrases"] else "—"
    send_typing(message.chat.id)
    ai_analysis = ask_grok_simple(
        f"حلل أسلوب شخص اسمه {name}. أكثر كلماته: {', '.join(top) or 'غير محدد'}. "
        f"مثال كلامه: '{sample}'. تحليل نفسي مضحك بالعامية المصرية، 3 جمل."
    )
    txt = (f"🧠 *أسلوب {name}:*\n"
           f"رسائل: `{d['count']}`\nكلماتك: {', '.join(top) or '—'}\nمثال: _{sample}_")
    if ai_analysis:
        txt += f"\n\n🤖 *تحليل AI:*\n{ai_analysis}"
    bot.reply_to(message, txt, parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  أضف: كلمة = رد
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.search(r'أضف\s*:', m.text))
def teach_bot(message):
    try:
        content = re.split(r'أضف\s*:', message.text, maxsplit=1)[1].strip()
        if "=" not in content:
            bot.reply_to(message, "⚠️ `أضف: الكلمة = الرد`", parse_mode='Markdown')
            return
        key, value = content.split("=", 1)
        key, value = key.strip().lower(), value.strip()
        if not key or not value:
            return
        existed = key in responses
        if existed and isinstance(responses[key], list):
            if value not in responses[key]:
                responses[key].append(value)
        else:
            responses[key] = [value]
        save_data(responses)
        bot.reply_to(message,
            f"{'✏️ محدّث' if existed else '✅ محفوظ'}: `{key}` ← {value}",
            parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ {e}")

# ══════════════════════════════════════════════════════════════
#  قول [كلام]
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^قول\s+.+', m.text.strip()))
def say_direct(message):
    txt = re.sub(r'^قول\s+', '', message.text.strip(), count=1).strip()
    if txt:
        bot.reply_to(message, txt)

# ══════════════════════════════════════════════════════════════
#  عرف [اسم]: [معلومات]
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^عرف\s+.+\s*:', m.text.strip()))
def add_person(message):
    match = re.match(r'^عرف\s+(.+?)\s*:\s*(.+)$', message.text.strip(), re.DOTALL)
    if not match:
        bot.reply_to(message, "⚠️ `عرف الاسم: المعلومات`", parse_mode='Markdown')
        return
    name    = match.group(1).strip()
    info    = match.group(2).strip()
    existed = name.lower() in people_db
    people_db[name.lower()] = {"name": name, "info": info}
    save_json(PEOPLE_FILE, people_db)
    bot.reply_to(message,
        f"{'✏️ محدّث' if existed else '✅ محفوظ'} *{name}* 👤",
        parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  مين [اسم]
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^مين\s+\S+', m.text.strip()))
def who_is(message):
    query = re.sub(r'^مين\s+', '', message.text.strip(), count=1).strip().lower()
    p = people_db.get(query) or next((v for k, v in people_db.items() if query in k), None)
    if p:
        ai_comment = ask_grok_simple(
            f"تعليق قصير مضحك على شخص اسمه {p['name']} وعنه: {p['info'][:100]}. "
            f"جملة واحدة بالعامية المصرية."
        )
        txt = f"👤 *{p['name']}*\n{p['info']}"
        if ai_comment:
            txt += f"\n\n🤖 _{ai_comment}_"
        bot.reply_to(message, txt, parse_mode='Markdown')
    else:
        bot.reply_to(message, f"🤷 ما عرفش مين *{query}*\n`عرف {query}: معلومات`", parse_mode='Markdown')

# ══════════════════════════════════════════════════════════════
#  اقتبس
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text and re.match(r'^اقتبس', m.text.strip()))
def quote_handler(message):
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ رد على الرسالة اللي عايز تقتبسها، ثم اكتب `اقتبس` 😄",
                     parse_mode='Markdown')
        return
    try:
        target = message.reply_to_message
        parts  = message.text.strip().split()
        color  = random.choice(QUOTE_COLORS)
        is_img = False
        keep_r = False
        for p in parts[1:]:
            if p in COLOR_MAP:        color  = COLOR_MAP[p]
            elif p.startswith("#"):   color  = p
            elif p in ["صورة","img"]: is_img = True
            elif p in ["مع","رد"]:    keep_r = True
        flags = " ".join(filter(None, ["i" if is_img else "", "r" if keep_r else ""])).strip()
        q_cmd = f"/q {color} {flags}".strip()
        sender = target.from_user.first_name or "حد"
        intros = [
            f"😂 {sender} قالها!", f"👀 {sender} قال إيه؟ 😂",
            f"💀 {sender} قالها وراح 😂", f"📜 للتاريخ — {sender} قال! 😂",
        ]
        bot.reply_to(message, random.choice(intros))
        time.sleep(0.4)
        bot.send_message(message.chat.id, q_cmd, reply_to_message_id=target.message_id)
    except Exception as e:
        bot.reply_to(message, f"❌ {e}")

# ══════════════════════════════════════════════════════════════
#  🎯 المعالج الرئيسي — قلب البوت الذكي
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda message: True)
def reply_main(message):
    if not message.text:
        return

    learn_from_message(message)
    try_react(message)

    text       = message.text.lower().strip()
    name       = message.from_user.first_name or ""
    uid        = str(message.from_user.id)
    chat_id    = message.chat.id
    is_private = message.chat.type == 'private'

    try:
        bot_me   = bot.get_me()
        bot_user = bot_me.username or ""
    except Exception:
        bot_user = ""

    mentioned = (
        bool(bot_user) and f"@{bot_user.lower()}" in text or
        "يا بوت" in text or
        "akro" in text.replace(" ", "").replace("\n", "")
    )

    # ① ضحك سريع
    if any(x in text for x in ["ههه","هههه","wkwk","lol","😂","😹","🤣","خخخ","خخ"]):
        bot.reply_to(message, random.choice(LAUGH_REPLIES))
        return

    # ② ترحيب سريع
    if any(g in text for g in ["هاي","هلو","أهلا","سلام عليكم","هلا"]):
        bot.reply_to(message, f"{name}! {random.choice(GREET_EXTRAS)}")
        return

    # ③ سؤال عن البوت
    if any(x in text for x in ["مين إنت","مين انت","انت مين","إنت مين","ايه وظيفتك","بتعمل ايه"]):
        mood = get_mood(chat_id)
        cfg  = MOOD_CONFIGS[mood]
        bot.reply_to(message,
            f"أنا AKRO Bot v5.0 ⚡ مدعوم بـ Grok AI 🤖\n"
            f"المزاج: {cfg['emoji']} {mood} | /help للأوامر")
        return

    # ④ القاموس أولاً
    for key, value in responses.items():
        if key.lower() in text:
            bot.reply_to(message, random.choice(value) if isinstance(value, list) else value)
            return

    # ⑤ شتايم
    if any(b in text for b in ["احا","عيل","غبي","بوت وسخ","مش بيشتغل","خربان","بايظ","زباله"]):
        bot.reply_to(message, random.choice(INSULT_REPLIES))
        return

    # ⑥ Grok AI — الرد الذكي
    should_use_grok = (
        is_private or
        mentioned or
        random.random() < AI_REPLY_CHANCE
    )

    if should_use_grok:
        send_typing(chat_id)
        ai_reply = ask_grok(
            message.text, chat_id, uid, name,
            extra_context=build_people_context()
        )
        if ai_reply:
            bot.reply_to(message, ai_reply)
            return

    # ⑦ تقليد شخص (3%)
    if random.random() < 0.03 and learned_styles:
        rand_uid = random.choice(list(learned_styles.keys()))
        msg      = mimic_user(rand_uid)
        if msg:
            bot.send_message(chat_id, msg)
            return

    # ⑧ تعليق عشوائي (3%)
    if random.random() < 0.03:
        bot.send_message(chat_id, random.choice(RANDOM_REMARKS))

# ══════════════════════════════════════════════════════════════
#  تشغيل
# ══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    grok_status = (
        "✅ متصل بـ Grok AI"
        if GROK_API_KEY and GROK_API_KEY != 'YOUR_GROK_API_KEY_HERE'
        else "❌ Grok API مش متصل — ضع GROK_API_KEY"
    )
    print("╔══════════════════════════════════════╗")
    print("║   AKRO BOT v5.0 — Grok AI Edition   ║")
    print("║         by Ahmed (AKRO)              ║")
    print("╚══════════════════════════════════════╝")
    print(f"📦 ردود:    {len(responses)}")
    print(f"👥 أشخاص:   {len(people_db)}")
    print(f"🧠 متعلم:   {len(learned_styles)}")
    print(f"🤖 {grok_status}")
    print(f"🎭 Moods:   {' | '.join(MOOD_CONFIGS.keys())}")
    print("──────────────────────────────────────")
    print("🚀 البوت شغال!")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
