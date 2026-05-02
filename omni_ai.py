import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from gtts import gTTS # للملفات الصوتية

console = Console()
PRIMARY = "#00F0FF"
ERROR   = "#FF003C"

def log_status(message, style=PRIMARY):
    console.print(Panel(Text(f"» {message}", style=style), border_style=style))

# الإعدادات
GROQ_KEY       = os.environ.get("GROQ_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
# ضع هنا رابط فيديو أو GIF ليظهر كخلفية متحركة عند الترحيب
WELCOME_GIF = "https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNHJueGZ3bmZpZzRyeHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4JmVwPXYxX2ludGVybmFsX2dpZl9ieV9pZCZjdD1n/3o7TKMGpxxS05S9YFq/giphy.gif"

if not all([GROQ_KEY, TELEGRAM_TOKEN]):
    raise EnvironmentError("❌ Missing GROQ_KEY or TELEGRAM_TOKEN")

client = Groq(api_key=GROQ_KEY)

# دالة الرد النصي وفهم الصور
async def get_groq_response(prompt: str, image_url: str = None) -> str:
    try:
        model = "llama-3.3-70b-versatile"
        messages = [{"role": "system", "content": "You are OMNI-AI, a supreme intelligence designed by Ahmed (AKRO). Answer in the same language the user writes in."}]
        
        if image_url:
            model = "llama-3.2-11b-vision-preview" # موديل الرؤية
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt if prompt else "ماذا يوجد في هذه الصورة؟"},
                    {"type": "image_url", "image_url": {"url": image_url}}
                ]
            })
        else:
            messages.append({"role": "user", "content": prompt})

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
        ))
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Groq Error: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_status(f"Connected: {user.first_name} [{user.id}]")
    
    # إرسال الخلفية المتحركة (فيديو أو GIF) مع رسالة الترحيب الخاصة بك
    await update.message.reply_animation(
        animation=WELCOME_GIF,
        caption=(
            "⚡ GROK-AI ACTIVATED ⚡\n\n"
            "المحرك: Groq (AKRO-X-👻😂❤️‍🩹)\n\n"
            "أنا الآن أدعم:\n"
            "1️⃣ الرد الذكي 🧠\n"
            "2️⃣ فهم الصور (أرسل صورة) 🖼\n"
            "3️⃣ إنشاء صور (/gen نص)\n"
            "4️⃣ تحويل النص لصوت (/voice نص)\n\n"
            "ابعت أي سؤال وأنا هرد عليك فوراً 🚀"
        )
    )

# دالة إنشاء الصور
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("❌ أكتب وصف الصورة بعد الأمر، مثال:\n/gen cat in space")
        return
    
    msg = await update.message.reply_text("🎨 جاري رسم خيالك...")
    image_url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed=42&model=flux"
    await update.message.reply_photo(photo=image_url, caption=f"✅ تم إنشاء: {prompt}")
    await msg.delete()

# دالة تحويل النص لصوت
async def text_to_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ أكتب النص المراد تحويله لصوت بعد الأمر.")
        return
    
    tts = gTTS(text=text, lang='ar')
    tts.save("voice.mp3")
    await update.message.reply_voice(voice=open("voice.mp3", "rb"))
    os.remove("voice.mp3")

# معالجة الرسائل (نص أو صور)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        # التعامل مع الصور
        photo_file = await update.message.photo[-1].get_file()
        image_url = photo_file.file_path
        status_msg = await update.message.reply_text("🧐 جاري تحليل الصورة...")
        response = await get_groq_response(update.message.caption or "حلل هذه الصورة", image_url)
        await status_msg.edit_text(response)
    else:
        # التعامل مع النصوص
        user_input = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        status_msg = await update.message.reply_text("🌀 جاري المعالجة...")
        response = await get_groq_response(user_input)
        await status_msg.edit_text(response)

if __name__ == '__main__':
    log_status("OMNI-AI BOOTING UP...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gen", generate_image))
    app.add_handler(CommandHandler("voice", text_to_voice))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))
    
    console.print("[bold cyan]System is Live with Multimedia Support.[/bold cyan]")
    app.run_polling()
