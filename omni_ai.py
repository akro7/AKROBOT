import os
import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq
from anthropic import AsyncAnthropic
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from gtts import gTTS

console = Console()
PRIMARY = "#00F0FF"
ERROR   = "#FF003C"
SUCCESS = "#00FF88"

def log_status(message, style=PRIMARY):
    console.print(Panel(Text(f"» {message}", style=style), border_style=style))

# ── الإعدادات ──────────────────────────────────────────────────────────────────
GROQ_KEY       = os.environ.get("GROQ_KEY")
CLAUDE_KEY     = os.environ.get("CLAUDE_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
WELCOME_VIDEO  = "welcome.mp4"

if not all([GROQ_KEY, CLAUDE_KEY, TELEGRAM_TOKEN]):
    raise EnvironmentError("❌ مفاتيح ناقصة — تحقق من GROQ_KEY و CLAUDE_KEY و TELEGRAM_TOKEN")

groq_client   = Groq(api_key=GROQ_KEY)
claude_client = AsyncAnthropic(api_key=CLAUDE_KEY)

# ── محدد المحرك التلقائي (Claude يقرر) ────────────────────────────────────────
async def pick_engine(prompt: str) -> str:
    """
    يرسل السؤال لـ Claude ويطلب منه فقط أن يختار المحرك المناسب:
    - 'claude'  → للأسئلة التقنية والإبداعية والتحليلية المعقدة
    - 'groq'   → للدردشة العامة والأسئلة البسيطة والسريعة
    """
    try:
        decision = await claude_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=10,
            system=(
                "You are an engine router. "
                "Given a user message, reply with ONLY one word: 'claude' or 'groq'.\n"
                "Use 'claude' for: code, analysis, writing, math, complex reasoning.\n"
                "Use 'groq' for: casual chat, simple questions, greetings, quick facts."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
        choice = decision.content[0].text.strip().lower()
        return "claude" if "claude" in choice else "groq"
    except Exception:
        return "groq"  # fallback آمن

# ── محرك Groq (Llama — سريع) ──────────────────────────────────────────────────
async def get_groq_response(prompt: str, image_url: str = None) -> str:
    try:
        model    = "llama-3.3-70b-versatile"
        messages = [{
            "role": "system",
            "content": (
                "أنت OMNI-AI، ذكاء اصطناعي متقدم صممه Ahmed (AKRO). "
                "رد دائماً بنفس لغة المستخدم. كن دقيقاً ومفيداً."
            )
        }]

        if image_url:
            model = "llama-3.2-11b-vision-preview"
            messages.append({"role": "user", "content": [
                {"type": "text",      "text": prompt or "حلل هذه الصورة"},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]})
        else:
            messages.append({"role": "user", "content": prompt})

        loop     = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: groq_client.chat.completions.create(
                model=model, messages=messages, max_tokens=2048
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ خطأ في Groq: {e}"

# ── محرك Claude (تحليل — دقيق) ───────────────────────────────────────────────
CLAUDE_AVAILABLE = True  # يتغير تلقائياً لو الرصيد خلص

async def get_claude_response(prompt: str) -> tuple[str, bool]:
    """يرجع (الرد، نجح؟)"""
    global CLAUDE_AVAILABLE
    try:
        response = await claude_client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2048,
            system=(
                "أنت OMNI-AI (نسخة Claude)، صممك Ahmed (AKRO). "
                "قدّم ردوداً تقنية وإبداعية عالية الجودة، "
                "مع أمثلة عملية عند الحاجة. رد بنفس لغة المستخدم."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
        CLAUDE_AVAILABLE = True
        return response.content[0].text, True
    except Exception as e:
        err = str(e)
        # رصيد منتهي أو مشكلة billing → عطّل Claude مؤقتاً
        if "credit" in err.lower() or "balance" in err.lower() or "billing" in err.lower():
            CLAUDE_AVAILABLE = False
            log_status("Claude API: رصيد منتهٍ — سيُستخدم Groq كبديل", style=ERROR)
        return err, False

# ── الاختيار التلقائي للمحرك ──────────────────────────────────────────────────
async def smart_response(prompt: str) -> tuple[str, str]:
    """يرجع (الرد، اسم_المحرك_المستخدم)"""
    engine = await pick_engine(prompt)

    if engine == "claude" and CLAUDE_AVAILABLE:
        reply, ok = await get_claude_response(prompt)
        if ok:
            return reply, "claude"
        # Claude فشل → fallback لـ Groq
        log_status("Fallback → Groq", style=ERROR)

    reply = await get_groq_response(prompt)
    return reply, "groq"

# ── /start ────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_status(f"Connected: {user.first_name} [{user.id}]")

    caption = (
        "⚡ OMNI-AI — مُفعَّل ⚡\n\n"
        "🤖 المحرك يُختار تلقائياً بناءً على سؤالك:\n"
        "   • 🧠 Claude  → تقنية / تحليل / كود / إبداع\n"
        "   • ⚡ Groq    → دردشة / أسئلة سريعة\n\n"
        "📋 الأوامر المتاحة:\n"
        "   /ask  [نص]   — اسأل Claude مباشرة\n"
        "   /gen  [نص]   — أنشئ صورة من وصف\n"
        "   /voice [نص]  — حوّل النص لصوت 🎙\n\n"
        "💬 أو ابعت أي رسالة وسيتكفل البوت بالباقي 🚀\n\n"
        "━━━━━━━━━━━━━━━━━\n"
        "🔧 Powered by AKRO"
    )

    try:
        if os.path.exists(WELCOME_VIDEO):
            with open(WELCOME_VIDEO, "rb") as v:
                await update.message.reply_video(video=v, caption=caption)
        else:
            await update.message.reply_text(caption)
    except Exception as e:
        log_status(f"Media Error: {e}", style=ERROR)
        await update.message.reply_text(caption)

# ── /ask (Claude مباشرة) ──────────────────────────────────────────────────────
async def ask_claude(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text(
            "💬 استخدام:\n/ask [سؤالك]\n\nمثال:\n/ask اشرح لي خوارزمية Dijkstra"
        )
        return

    if not CLAUDE_AVAILABLE:
        await update.message.reply_text(
            "⚠️ *رصيد Claude منتهٍ*\n"
            "جاري التحويل لـ Groq.\n"
            "شحن الرصيد: https://console.anthropic.com/settings/billing",
            parse_mode="Markdown"
        )
        msg = await update.message.reply_text("⚡ Groq يجيب...")
        reply = await get_groq_response(prompt)
        await msg.edit_text(f"⚡ *Groq (بديل):*\n\n{reply}", parse_mode="Markdown")
        return

    msg = await update.message.reply_text("🧠 Claude يفكر...")
    reply, ok = await get_claude_response(prompt)
    if ok:
        await msg.edit_text(f"🧠 *Claude:*\n\n{reply}", parse_mode="Markdown")
    else:
        fallback = await get_groq_response(prompt)
        await msg.edit_text(f"⚡ *Groq (بديل):*\n\n{fallback}", parse_mode="Markdown")

# ── /gen (توليد صور) ─────────────────────────────────────────────────────────
async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("🎨 استخدام:\n/gen [وصف الصورة]")
        return

    msg = await update.message.reply_text("🎨 جاري رسم خيالك...")
    url = f"https://pollinations.ai/p/{prompt.replace(' ', '%20')}?width=1024&height=1024&seed=42&model=flux"
    await update.message.reply_photo(photo=url, caption=f"✅ {prompt}")
    await msg.delete()

# ── /voice (نص لصوت) ─────────────────────────────────────────────────────────
async def text_to_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args).strip()
    if not text:
        await update.message.reply_text("🎙 استخدام:\n/voice [النص المراد قراءته]")
        return

    tts = gTTS(text=text, lang='ar')
    tts.save("voice.mp3")
    with open("voice.mp3", "rb") as f:
        await update.message.reply_voice(voice=f)
    os.remove("voice.mp3")

# ── handle_message (الرسائل العادية) ─────────────────────────────────────────
ENGINE_EMOJI = {"claude": "🧠", "groq": "⚡"}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ── صورة ──
    if update.message.photo:
        photo  = await update.message.photo[-1].get_file()
        msg    = await update.message.reply_text("🖼 جاري تحليل الصورة...")
        reply  = await get_groq_response(
            update.message.caption or "حلل هذه الصورة",
            image_url=photo.file_path
        )
        await msg.edit_text(f"⚡ *Groq Vision:*\n\n{reply}", parse_mode="Markdown")
        return

    # ── نص عادي ──
    user_input = update.message.text.strip()
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    status = await update.message.reply_text("🌀 اختيار المحرك المناسب...")
    reply, engine = await smart_response(user_input)

    emoji = ENGINE_EMOJI.get(engine, "🤖")
    label = "Claude 🧠" if engine == "claude" else "Groq ⚡"

    await status.edit_text(
        f"{emoji} *{label}:*\n\n{reply}",
        parse_mode="Markdown"
    )
    log_status(f"Engine used: {engine.upper()} | User: {update.effective_user.id}", style=SUCCESS)

# ── التشغيل ───────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    log_status("OMNI-AI BOOTING — AUTO ENGINE MODE ACTIVE")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask",   ask_claude))
    app.add_handler(CommandHandler("gen",   generate_image))
    app.add_handler(CommandHandler("voice", text_to_voice))
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_message))

    log_status("✅ Bot is running — waiting for messages...", style=SUCCESS)
    app.run_polling(drop_pending_updates=True)
