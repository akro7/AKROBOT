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
# تأكد أن اسم السيكرت في جيت هب هو BOT_TOKEN
TOKEN = os.getenv('BOT_TOKEN') or '7721384317:AAHaTZ-iM3RhBmjBgxdaN84ah3DjKUU_LT0'
# تأكد أن اسم السيكرت في جيت هب هو GROQ_KEY كما يظهر في صورك
GROK_API_KEY = os.getenv('GROK_API_KEY') 
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
#  قاموس الردود الضخم
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
}

def load_data():
    saved = load_json(DATA_FILE, {})
    # التصحيح: استخدام {} بدلاً من () لعمل Dict Comprehension
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

# ══════════════════════════════════════════
#  ريأكت إيموجي ذكي
# ══════════════════════════════════════════
REACT_RULES = [
    (["ههه","هههه","😂","😹","🤣"], 0.65, ["😂","🤣","💀"]),
    (["حلو","جميل","رائع"], 0.55, ["❤️","🔥","✨"]),
    (["تعبان","زهقت","زعلان"], 0.55, ["❤️","😔","🫂"]),
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
#  نظام Grok AI
# ══════════════════════════════════════════
SYSTEM_BASE = "أنت AKRO Bot، مطور من قبل أحمد يونيس. أنت ذكي واجتماعي جداً، ترد بالعامية المصرية بأسلوب شبابي ومرح."

def ask_grok(user_text, history):
    if not GROK_API_KEY: return None
    messages = [{"role": "system", "content": SYSTEM_BASE}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    try:
        res = requests.post(GROK_API_URL, json={"model": GROK_MODEL, "messages": messages, "temperature": 0.8},
                            headers={"Authorization": f"Bearer {GROK_API_KEY}"}, timeout=15)
        return res.json()["choices"][0]["message"]["content"].strip()
    except: return None

# ══════════════════════════════════════════
#  الأوامر (Commands)
# ══════════════════════════════════════════

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, f"أهلاً يا {message.from_user.first_name}! 👋\nأنا AKRO Bot v5.0 جاهز للخدمة ⚡")

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    custom = sum(1 for k in responses if k not in DEFAULT_RESPONSES)
    bot.reply_to(message, f"📊 *إحصائيات:*\nردود مضافة: `{custom}`\nأشخاص تم تعريفهم: `{len(people_db)}`", parse_mode='Markdown')

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

    # الرد من القاموس أولاً
    for key, value in responses.items():
        if key.lower() in text:
            bot.reply_to(message, random.choice(value))
            return

    # الذكاء الاصطناعي كخيار أخير
    update_context(uid, "user", message.text)
    bot.send_chat_action(message.chat.id, "typing")
    ai_reply = ask_grok(message.text, user_contexts.get(uid, []))
    
    if ai_reply:
        bot.reply_to(message, ai_reply)
        update_context(uid, "assistant", ai_reply)

# التشغيل مع حل مشكلة الـ Conflict
if __name__ == "__main__":
    print("🚀 AKRO BOT v5.0 is Online!")
    # مسح الـ Webhook القديم لتجنب خطأ 409
    bot.remove_webhook()
    time.sleep(1)
    bot.infinity_polling(skip_pending=True)
