import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
PRIMARY = "#00F0FF"
ERROR   = "#FF003C"

def log_status(message, style=PRIMARY):
    console.print(Panel(Text(f"» {message}", style=style), border_style=style))

GROQ_KEY       = os.environ.get("GROQ_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not all([GROQ_KEY, TELEGRAM_TOKEN]):
    raise EnvironmentError("❌ Missing GROQ_KEY or TELEGRAM_TOKEN")

client = Groq(api_key=GROQ_KEY)

async def get_groq_response(prompt: str) -> str:
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are OMNI-AI, a supreme intelligence designed by Ahmed (AKRO). Answer in the same language the user writes in."},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=2048,
        ))
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Groq Error: {str(e)}"

async def safe_send(msg_obj, text: str):
    MAX = 4000
    try:
        if len(text) <= MAX:
            await msg_obj.edit_text(text)
        else:
            await msg_obj.edit_text(text[:MAX])
            for i in range(MAX, len(text), MAX):
                await msg_obj.get_bot().send_message(
                    chat_id=msg_obj.chat.id, text=text[i:i+MAX]
                )
    except Exception as e:
        log_status(f"Send error: {e}", style=ERROR)
        await msg_obj.edit_text("❌ خطأ في إرسال الرد.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_status(f"Connected: {user.first_name} [{user.id}]")
    await update.message.reply_text(
        "⚡ OMNI-AI ACTIVATED ⚡\n\n"
        "المحرك: Groq (llama-3.3-70b)\n\n"
        "ابعت أي سؤال وأنا هرد عليك فوراً 🚀"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("🌀 جاري المعالجة...")

    response = await get_groq_response(user_input)
    await safe_send(status_msg, response)
    log_status(f"Done for {update.effective_user.first_name}")

if __name__ == '__main__':
    log_status("OMNI-AI BOOTING UP...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    console.print("[bold cyan]System is Live.[/bold cyan]")
    app.run_polling()
