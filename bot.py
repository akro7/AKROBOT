import telebot
import random
import json
import os
import re
import time
from collections import Counter
import requests

# ========================================
#   AKRO BOT v5.0 - ULTIMATE MERGE
#   v4.0 (Logic) + v5.0 (Grok AI)
#   Developed by Ahmed (AKRO)
# ========================================

# الإعدادات الأساسية
TOKEN = os.getenv('BOT_TOKEN') or '7721384317:AAHaTZ-iM3RhBmjBgxdaN84ah3DjKUU_LT0'
GROK_API_KEY = os.getenv('GROQ_KEY') # جلب المفتاح من السيكرتس
GROK_MODEL   = os.getenv('GROK_MODEL') or 'grok-2-latest'
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

bot = telebot.TeleBot(TOKEN)

DATA_FILE   = 'memory.json'
PEOPLE_FILE = 'people.json'
LEARN_FILE  = 'learned.json'
CONTEXT_DIR = 'contexts.json'

# ══════════════════════════════════════════
#  تحميل وحفظ JSON (النسخة المحسنة والآمنة)
# ══════════════════════════════════════════
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return json.loads(content) if content else default
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

# تحميل قواعد البيانات عند التشغيل
people_db      = load_json(PEOPLE_FILE, {})
learned_styles = load_json(LEARN_FILE,  {})
user_contexts  = load_json(CONTEXT_DIR, {})

# ══════════════════════════════════════════
#  قاموس الردود الضخم (من v4.0)
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
    "يا بوت":      ["أيوه 😄", "تأمر يا باشا 🫡", "أنا هنا ⚡"],
    "والله":       ["والله الله 😂", "صح 👍", "😄"],
    "حلو":         ["ومنك للبنين 😂", "إنت الأحلى ❤️", "😄✨"],
    "جميل":        ["ومنك 😄", "الله يجمّلك ✨", "إنت الأجمل 😂"],
    "صح":          ["صح 💯", "بالظبط 👍", "أيوه 😄"],
    "غلط":         ["مش صح 😅", "لأ يا عم 😂", "راجع كلامك 😄"],
    "عاوز":        ["قول اللي عاوزه 😄", "تأمر 🫡", "أيوه؟ 👂"],
}

def load_data():
    saved = load_json(DATA_FILE, {})
    result = {k: list(v) for k, v in DEFAULT_RESPONSES.items()}
    for k, v in saved.items():
        result[k] = v if isinstance(v, list) else [v]
    return result

def save_data(data):
    custom = {k: v for k, v in data.items() if k not in DEFAULT_RESPONSES}
    save_json(DATA_FILE, custom)

responses = load_data()

# ══════════════════════════════════════════
#  نظام السياق والتعلم والمحاكاة
# ══════════════════════════════════════════
def update_context(uid, role, text):
    uid = str(uid)
    if uid not in user_contexts:
        user_contexts[uid] = []
    user_contexts[uid].append({"role": role, "content": text})
    if len(user_contexts[uid]) > 6:
        user_contexts[uid] = user_contexts[uid][-6:]
    save_json(CONTEXT_DIR, user_contexts)

def learn_from_message(message):
    if not message.text or len(message.text) < 4: return
    uid  = str(message.from_user.id)
    name = message.from_user.first_name or "مجهول"
    text = message.text.strip()
    if text.startswith('/') or any(x in text for x in ['أضف', 'عرف', 'قول']): return
    
    if uid not in learned_styles:
        learned_styles[uid] = {"name": name, "phrases": [], "words": [], "count": 0}
    
    learned_styles[uid]["count"] = learned_styles[uid].get("count", 0) + 1
    phrases = learned_styles[uid]["phrases"]
    phrases.append(text)
    if len(phrases) > 40: phrases.pop(0)
    
    words = [w for w in text.split() if len(w) > 3]
    learned_styles[uid]["words"].extend(words)
    if len(learned_styles[uid]["words"]) > 200:
        learned_styles[uid]["words"] = [w for w, _ in Counter(learned_styles[uid]["words"]).most_common(80)]
    save_json(LEARN_FILE, learned_styles)

def mimic_user(uid):
    uid = str(uid)
    if uid not in learned_styles or not learned_styles[uid]["phrases"]: return None
    d = learned_styles[uid]
    phrase = random.choice(d["phrases"])
    return random.choice([
        f"😂 {d['name']} كان بيقول: \"{phrase}\"",
        f"👀 فاكر لما {d['name']} قال: \"{phrase}\" ؟",
        f"🎤 {d['name']} قالها: \"{phrase}\" 😂"
    ])

# ══════════════════════════════════════════
#  ريأكت إيموجي ذكي
# ══════════════════════════════════════════
REACT_RULES = [
    (["ههه","هههه","😂","😹","🤣"], 0.65, ["😂","🤣","💀"]),
    (["حلو","جميل","رائع"], 0.55, ["❤️","🔥","✨"]),
    (["تعبان","زهقت","زعلان"], 0.55, ["❤️","😔","🫂"]),
    (["والله","الحمد لله"], 0.45, ["🙏","✨"]),
    (["صح","بالظبط"], 0.50, ["👍","💯"]),
]

def try_react(message):
    if not message.text: return
    text = message.text.lower()
    for keywords, chance, emojis in REACT_RULES:
        if any(k in text for k in keywords):
            if random.random() < chance:
                try:
                    bot.set_message_reaction(message.chat.id, message.message_id, [telebot.types.ReactionTypeEmoji(random.choice(emojis))])
                except: pass
                return

# ══════════════════════════════════════════
#  نظام Grok AI (المزاج والسياق)
# ══════════════════════════════════════════
SYSTEM_BASE = "أنت AKRO Bot، ذكي جداً، اجتماعي، وتفهم المشاعر البشرية بعمق. ترد دائماً بجمل عربية غنية بالمعاني. استخدم العامية المصرية بذكاء."

def detect_mood(text):
    text = text.lower()
    mood_map = {"joy": ["😂","ضحك","حلو"], "sadness": ["حزين","تعبان"], "love": ["بحبك","❤️"], "wisdom": ["نصيحة","حكمة"]}
    for mood, keys in mood_map.items():
        if any(k in text for k in keys): return mood
    return "neutral"

def ask_grok(user_text, mood, history):
    if not GROK_API_KEY: return None
    messages = [{"role": "system", "content": SYSTEM_BASE + f"\nحالة المستخدم الآن: {mood}"}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    try:
        res = requests.post(GROK_API_URL, json={"model": GROK_MODEL, "messages": messages, "temperature": 0.8},
                            headers={"Authorization": f"Bearer {GROK_API_KEY}"}, timeout=15)
        return res.json()["choices"][0]["message"]["content"].strip()
    except: return None

# ══════════════════════════════════════════
#  إعدادات QuotLy والألوان (من v4.0)
# ══════════════════════════════════════════
QUOTE_COLORS = ["red","blue","green","purple","orange","pink","white","random","#cbafff","#ff6b6b","#4ecdc4","#ffd700","#00bcd4","#e91e63"]
COLOR_MAP = {"احمر":"red","أحمر":"red","ازرق":"blue","أزرق":"blue","اخضر":"green","أخضر":"green","بنفسجي":"purple","ذهبي":"#ffd700"}
LAUGH_REPLIES = ["😂💀", "يموت 😂", "ده إيه 😂", "جاب جاب 💀", "خلاص 😂"]
RANDOM_REMARKS = ["😂 ركزوا", "👀 شايف كل حاجة", "يا رغيكم 😂", "تحفة الجروب ده 😂"]

# ══════════════════════════════════════════
#  الأوامر (Commands)
# ══════════════════════════════════════════

@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name or "صاحبي"
    bot.reply_to(message, f"أهلاً يا {name}! 👋\nأنا AKRO Bot v5.0 (Ultimate) ⚡\nمتصل بذكاء Grok AI ومعايا كل مميزاتي القديمة.\n/help للأوامر")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, "🤖 *أوامر البوت:*\n\n📝 `أضف: كلمة = الرد`\n🗣️ `قول أي كلام`\n👤 `عرف اسم: معلومة`\n🔍 `مين اسم`\n🎨 `اقتبس` (بالرد)\n🧠 `/mimic اسم`\n📋 `/list` · `/del` · `/stats`", parse_mode='Markdown')

@bot.message_handler(commands=['list'])
def list_cmd(message):
    if not responses: return bot.reply_to(message, "📭 مفيش ردود!")
    items = list(responses.items())
    for i in range(0, len(items), 20):
        chunk = items[i:i+20]
        txt = f"📋 *الردود ({i+1}–{i+len(chunk)}):*\n\n"
        for j, (k, v) in enumerate(chunk, i+1):
            txt += f"{j}. `{k}`\n"
        bot.send_message(message.chat.id, txt, parse_mode='Markdown')

@bot.message_handler(commands=['del'])
def del_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ `/del كلمة`")
    key = parts[1].strip().lower()
    if key in responses:
        del responses[key]
        save_data(responses)
        bot.reply_to(message, f"🗑️ حُذف `{key}`")
    else: bot.reply_to(message, "❌ مش موجود")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    custom = sum(1 for k in responses if k not in DEFAULT_RESPONSES)
    bot.reply_to(message, f"📊 *إحصائيات:*\nردود: `{len(responses)}` (مضاف: `{custom}`)\nأشخاص: `{len(people_db)}`\nمتعلم: `{len(learned_styles)}` شخص", parse_mode='Markdown')

@bot.message_handler(commands=['mimic'])
def mimic_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return bot.reply_to(message, "⚠️ `/mimic اسم`")
    q = parts[1].strip().lower()
    found = next(((uid, d) for uid, d in learned_styles.items() if q in d["name"].lower()), None)
    if found: bot.reply_to(message, mimic_user(found[0]))
    else: bot.reply_to(message, "🤷 معرفش أسلوبه لسه!")

# ══════════════════════════════════════════
#  المعالجات الذكية (Regex Handlers)
# ══════════════════════════════════════════

@bot.message_handler(func=lambda m: m.text and re.search(r'أضف\s*:', m.text))
def teach_bot(message):
    try:
        content = re.split(r'أضف\s*:', message.text, maxsplit=1)[1].strip()
        if "=" not in content: return bot.reply_to(message, "⚠️ `أضف: كلمة = رد`")
        key, value = content.split("=", 1)
        key, value = key.strip().lower(), value.strip()
        if key not in responses: responses[key] = []
        responses[key].append(value)
        save_data(responses)
        bot.reply_to(message, f"✅ تم حفظ: `{key}` ← {value}")
    except: pass

@bot.message_handler(func=lambda m: m.text and re.match(r'^عرف\s+.+\s*:', m.text.strip()))
def add_person(message):
    match = re.match(r'^عرف\s+(.+?)\s*:\s*(.+)$', message.text.strip(), re.DOTALL)
    if match:
        name, info = match.group(1).strip(), match.group(2).strip()
        people_db[name.lower()] = {"name": name, "info": info}
        save_json(PEOPLE_FILE, people_db)
        bot.reply_to(message, f"✅ عرفت *{name}* 👤", parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text and re.match(r'^مين\s+\S+', m.text.strip()))
def who_is(message):
    query = re.sub(r'^مين\s+', '', message.text.strip(), count=1).strip().lower()
    p = people_db.get(query) or next((v for k, v in people_db.items() if query in k), None)
    if p: bot.reply_to(message, f"👤 *{p['name']}*\n{p['info']}", parse_mode='Markdown')
    else: bot.reply_to(message, f"🤷 ما عرفش مين {query}")

@bot.message_handler(func=lambda m: m.text and re.match(r'^اقتبس', m.text.strip()))
def quote_handler(message):
    if not message.reply_to_message: return bot.reply_to(message, "⚠️ رد على رسالة للاقتباس")
    target = message.reply_to_message
    parts = message.text.strip().split()
    color = random.choice(QUOTE_COLORS)
    for p in parts[1:]:
        if p in COLOR_MAP: color = COLOR_MAP[p]
    bot.reply_to(message, f"😂 {target.from_user.first_name} قالها!")
    bot.send_message(message.chat.id, f"/q {color}", reply_to_message_id=target.message_id)

# ══════════════════════════════════════════
#  المعالج الرئيسي (The Brain)
# ══════════════════════════════════════════
@bot.message_handler(func=lambda message: True)
def reply_main(message):
    if not message.text: return
    
    learn_from_message(message)
    try_react(message)
    
    text = message.text.lower().strip()
    uid = str(message.from_user.id)

    # 1. الضحك السريع
    if any(x in text for x in ["ههه","هههه","😂","🤣"]):
        bot.reply_to(message, random.choice(LAUGH_REPLIES))
        return

    # 2. القاموس المحفوظ
    for key, value in responses.items():
        if key.lower() in text:
            bot.reply_to(message, random.choice(value))
            return

    # 3. عشوائيات (تعليق أو محاكاة)
    if random.random() < 0.03:
        bot.send_message(message.chat.id, random.choice(RANDOM_REMARKS))
        return

    # 4. الذكاء الاصطناعي (Grok) - الملاذ الأخير
    mood = detect_mood(text)
    update_context(uid, "user", message.text)
    bot.send_chat_action(message.chat.id, "typing")
    ai_reply = ask_grok(message.text, mood, user_contexts.get(uid, []))
    
    if ai_reply:
        bot.reply_to(message, ai_reply)
        update_context(uid, "assistant", ai_reply)

# التشغيل
if __name__ == "__main__":
    print("🚀 AKRO BOT v5.0 Ultimate is Online!")
    bot.infinity_polling()
