import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from anthropic import AsyncAnthropic # مكتبة كلود
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from gtts import gTTS

console = Console()
PRIMARY = "#00F0FF"
ERROR   = "#FF003C"

def log_status(message, style=PRIMARY):
    console.print(Panel(Text(f"» {message}", style=style), border_style=style))

# الإعدادات
GROQ_KEY       = os.environ.get("GROQ_KEY")
CLAUDE_KEY     = os.environ.get("CLAUDE_KEY") # مفتاح كلود الجديد
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WELCOME_VIDEO_PATH = "welcome.mp4"

if not all([GROQ_KEY, CLAUDE_KEY, TELEGRAM_TOKEN]):
    raise EnvironmentError("❌ Missing KEYS (GROQ, CLAUDE, or TELEGRAM)")

# تهيئة المحركات
groq_client = Groq(api_key=GROQ_KEY)
claude_client = AsyncAnthropic(api_key=CLAUDE_KEY)

# دالة Groq (Llama)
async def get_groq_response(prompt: str, image_url: str = None) -> str:
    try:
        model = "llama-3.3-70b-versatile"
        messages = [{"role": "system", "content": "You are OMNI-AI, a supreme intelligence designed by Ahmed (AKRO). Answer in the same language the user writes in."}]
        if image_url:
            model = "llama-3.2-11b-vision-preview"
            messages.append({"role": "user", "content": [{"type": "text", "text": prompt if prompt else "Analyze this image"}, {"type": "image_url", "image_url": {"url": image_url}}]})
        else:
            messages.append({"role": "user", "content": prompt})

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: groq_client.chat.completions.create(model=model, messages=messages, max_tokens=2048))
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Groq Error: {str(e)}"

# دالة Claude (AI CLAUDE)
async def get_claude_response(prompt: str) -> str:
    try:
        response = await claude_client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2048,
            system="You are OMNI-AI (Claude Edition), designed by Ahmed (AKRO). Provide high-level technical and creative responses.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        return f"❌ Claude Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_status(f"Connected: {user.first_name} [{user.id}]")
    
    caption_text = (
        "⚡ GROK-AI ACTIVATED ⚡\n\n"
        "المحرك الافتراضي: Groq (AKRO-X-👻😂❤️‍🩹)\n"
        "المحرك المتقدم: Claude 3.5 🧠\n\n"
        "أنا الآن أدعم:\n"
        "1️⃣ الرد الذكي (Groq/Claude) 🤖\n"
        "2️⃣ فهم الصور (أرسل صورة) 🖼\n"
        "3️⃣ إنشاء صور (/gen نص) 🎨\n"
        "4️⃣ تحويل النص لصوت (/voice نص) 🎙\n"
        "5️⃣ سؤال كلود مباشرة (/ask نص) 💬\n\n"
        "ابعت أي سؤال وأنا هرد عليك فوراً 🚀"
    )

    try:
        if os.path.exists(WELCOME_VIDEO_PATH):
            with open(WELCOME_VIDEO_PATH, "rb") as video:
                await update.message.reply_video(video=video, caption=caption_text)
        else:
            await update.message.reply_text(caption_text)
    except Exception as e:
        log_status(f"Media Error: {e}", style=ERROR)
        await update.message.reply_text(caption_text)

# أمر خاص بسؤال كلود فقط
async def ask_claude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("💬 أكتب سؤالك لـ كلود بعد الأمر، مثال:\n/ask كيف ابرمج بوت؟")
        return
    
    status_msg = await update.message.reply_text("🧠 جاري استشارة كلود (Claude 3.5)...")
    response = await get_claude_response(prompt)
    await status_msg.edit_text(response)

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("❌ أكتب وصف الصورة بعد الأمر.")
        return
    msg = await update.message.reply_text("🎨 جاري رسم خيالك...")
    image_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed=42&model=flux"
    await update.message.reply_photo(photo=image_url, caption=f"✅ تم إنشاء: {prompt}")
    await msg.delete()

async def text_to_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ أكتب النص المراد تحويله لصوت.")
        return
    tts = gTTS(text=text, lang='ar')
    tts.save("voice.mp3")
    await update.message.reply_voice(voice=open("voice.mp3", "rb"))
    os.remove("voice.mp3")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        image_url = photo_file.file_path
        status_msg = await update.message.reply_text("🧐 جاري تحليل الصورة بذكاء (Groq Vision)...")
        response = await get_groq_response(update.message.caption or "Analyze this", image_url)
        await status_msg.edit_text(response)
    else:
        user_input = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        status_msg = await update.message.reply_text("🌀 جاري المعالجة...")
        # هنا البوت يستخدم Groq للدردشة العادية، ولو عاوز كلود استخدم /ask
        response = await get_groq_response(user_input)
        await status_msg.edit_text(response)

if __name__ == '__main__':
    log_status("OMNI-AI BOOTING UP WITH CLAUDE SUPPORT...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask_claude)) # أمر كلود الجديد
    app.add_handler(CommandHandler("gen", generate_image))
    app.add_handler(CommandHandler("voice", text_to_voice))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    app.run_polling(drop_pending_updates=True)
