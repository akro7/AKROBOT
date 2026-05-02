import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from openai import OpenAI
import google.generativeai as genai
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
PRIMARY_BLUE = "#00F0FF"
ACCENT_CRIMSON = "#FF003C"

def log_status(message, style=PRIMARY_BLUE):
    console.print(Panel(Text(f"» {message}", style=style), border_style=style))

OPENAI_KEY = os.environ.get("OPENAI_KEY")
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

if not all([OPENAI_KEY, GEMINI_KEY, TELEGRAM_TOKEN]):
    raise EnvironmentError("❌ Missing environment variables")

client_oa = OpenAI(api_key=OPENAI_KEY)
genai.configure(api_key=GEMINI_KEY)

# --- [ اكتشاف محرك Gemini المتاح تلقائياً ] ---
def get_best_gemini_model():
    preferred = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
    try:
        available = [m.name for m in genai.list_models() if "generateContent" in m.supported_generation_methods]
        log_status(f"Available Gemini models: {available}")
        for p in preferred:
            for a in available:
                if p in a:
                    log_status(f"Selected: {a}")
                    return a
        if available:
            return available[0]
    except Exception as e:
        log_status(f"Model detection error: {e}", style=ACCENT_CRIMSON)
    return "gemini-2.0-flash"

gemini_model_name = get_best_gemini_model()
gemini_model = genai.GenerativeModel(gemini_model_name)

class OmniOrchestrator:
    def __init__(self):
        self.mode = "GEMINI"

    async def get_gpt_response(self, prompt):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: client_oa.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are OMNI-AI Core, a supreme unified intelligence designed by Ahmed."},
                    {"role": "user", "content": prompt}
                ]
            ))
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ GPT Error: {str(e)}"

    async def get_gemini_response(self, prompt):
        try:
            response = await gemini_model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            return f"❌ Gemini Error: {str(e)}"

orchestrator = OmniOrchestrator()

# --- [ تقسيم الرسائل الطويلة ] ---
async def safe_send(msg_obj, text):
    MAX = 4000
    # إزالة parse_mode لتفادي أخطاء Markdown
    try:
        if len(text) <= MAX:
            await msg_obj.edit_text(text)
        else:
            await msg_obj.edit_text(text[:MAX])
            chat_id = msg_obj.chat.id if hasattr(msg_obj, 'chat') else msg_obj.chat_id
            for i in range(MAX, len(text), MAX):
                await msg_obj.get_bot().send_message(chat_id=chat_id, text=text[i:i+MAX])
    except Exception as e:
        log_status(f"Send error: {e}", style=ACCENT_CRIMSON)
        await msg_obj.edit_text("❌ خطأ في إرسال الرد.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_status(f"Link Established with: {user.first_name}")
    welcome_text = (
        f"⚡ OMNI-AI SYSTEM ACTIVATED ⚡\n\n"
        f"المحرك النشط: {gemini_model_name}\n\n"
        "اختر وضع التشغيل:"
    )
    keyboard = [
        [InlineKeyboardButton("💎 Hybrid Mode", callback_data='mode_hybrid')],
        [InlineKeyboardButton("🔵 GPT-4o Only", callback_data='mode_gpt'),
         InlineKeyboardButton("🔴 Gemini Only", callback_data='mode_gemini')]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'mode_hybrid':
        orchestrator.mode = "HYBRID"
        msg = "✅ Hybrid Mode - GPT + Gemini"
    elif query.data == 'mode_gpt':
        orchestrator.mode = "GPT"
        msg = "✅ GPT-4o Mode"
    else:
        orchestrator.mode = "GEMINI"
        msg = f"✅ Gemini Mode ({gemini_model_name})"
    await query.edit_message_text(text=f"{msg}\nأرسل سؤالك الآن...")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    status_msg = await update.message.reply_text("🌀 جاري المعالجة...")

    try:
        if orchestrator.mode == "HYBRID":
            gpt_task = asyncio.create_task(orchestrator.get_gpt_response(user_input))
            gemini_task = asyncio.create_task(orchestrator.get_gemini_response(user_input))
            gpt_res, gem_res = await asyncio.gather(gpt_task, gemini_task)
            final_response = f"🔹 GPT-4o:\n{gpt_res}\n\n🔸 Gemini:\n{gem_res}"
        elif orchestrator.mode == "GPT":
            final_response = await orchestrator.get_gpt_response(user_input)
        else:
            final_response = await orchestrator.get_gemini_response(user_input)

        await safe_send(status_msg, final_response)
        log_status(f"Done for {update.effective_user.first_name}")

    except Exception as e:
        log_status(f"ERROR: {str(e)}", style=ACCENT_CRIMSON)
        await status_msg.edit_text(f"❌ خطأ: {str(e)}")

if __name__ == '__main__':
    log_status("OMNI-AI CORE IS BOOTING UP...")
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    console.print("[bold cyan]System is Live.[/bold cyan]")
    application.run_polling()
