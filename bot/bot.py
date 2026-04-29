"""
╔══════════════════════════════════════════════╗
║         AKRO MEDIA SYSTEM v3.0               ║
║    Advanced Telegram Media Downloader        ║
║    Powered by yt-dlp + aria2c + ffmpeg       ║
╚══════════════════════════════════════════════╝

Features:
- Inline keyboard for quality/format selection
- Real-time download progress bar
- Audio-only extraction (MP3/M4A)
- Smart file size validation (50MB Telegram limit)
- Auto-compression for oversized videos
- Per-user rate limiting & queue
- Cancel button support
- Retry mechanism on failure
- Auto-cleanup after upload
- Playlist detection with limit warning
- Detailed error reporting
- Admin stats command
"""

import os
import re
import time
import asyncio
import html
import logging
import json
import uuid
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict

import yt_dlp
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError

# ─── إعدادات أساسية ────────────────────────────────────────────────────────────

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [5921061565]  # أضف Chat ID بتاعك هنا للحصول على أوامر الأدمن مثل: [123456789]

DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

MAX_FILE_SIZE_MB = 49        # حد Telegram = 50MB
MAX_PLAYLIST_ITEMS = 5       # أقصى عدد فيديوهات من قائمة تشغيل
RATE_LIMIT_SECONDS = 10      # وقت الانتظار بين كل طلبين لنفس المستخدم
MAX_QUEUE_PER_USER = 2       # أقصى طلبات في نفس الوقت لمستخدم واحد
EXECUTOR_WORKERS = 6

# ─── تسجيل الأحداث ────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s → %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger("AKRO")

# ─── حالة النظام ──────────────────────────────────────────────────────────────

executor = ThreadPoolExecutor(max_workers=EXECUTOR_WORKERS)
user_last_request: dict[int, float] = {}          # rate limiting
user_active_downloads: dict[int, int] = defaultdict(int)  # queue count
active_tasks: dict[str, asyncio.Task] = {}        # لإلغاء التنزيل
bot_stats = {
    "started": datetime.now().isoformat(),
    "total_downloads": 0,
    "failed_downloads": 0,
    "total_bytes": 0,
}

# ─── أدوات مساعدة ─────────────────────────────────────────────────────────────

def fmt_size(size_bytes: int) -> str:
    """تحويل البايتات لصيغة مقروءة"""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes/1024:.1f}KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes/1024**2:.1f}MB"
    return f"{size_bytes/1024**3:.2f}GB"

def fmt_speed(bps: float) -> str:
    return f"{fmt_size(int(bps))}/s"

def fmt_eta(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}ث"
    elif seconds < 3600:
        return f"{int(seconds//60)}د {int(seconds%60)}ث"
    return f"{int(seconds//3600)}س {int((seconds%3600)//60)}د"

def progress_bar(percent: float, length: int = 12) -> str:
    filled = int(length * percent / 100)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

def clean_title(title: str) -> str:
    """تنظيف عنوان الفيديو"""
    title = re.sub(r'[^\w\s\-_.,!؟!،()[\]{}]', '', title, flags=re.UNICODE)
    return title[:80].strip() or "Media"

def is_playlist(url: str) -> bool:
    return any(k in url for k in ["playlist", "list=", "/channel/", "@", "/c/"])

# ─── فحص وتقليص حجم الملف ──────────────────────────────────────────────────────

def compress_video(input_path: str, max_mb: int = MAX_FILE_SIZE_MB) -> str | None:
    """ضغط الفيديو باستخدام ffmpeg إذا كان أكبر من الحد المسموح"""
    try:
        import subprocess
        output_path = input_path.replace(".mp4", "_compressed.mp4")
        size_mb = os.path.getsize(input_path) / (1024 ** 2)
        
        if size_mb <= max_mb:
            return input_path
        
        # حساب معدل البت المطلوب
        cmd_probe = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "json", input_path
        ]
        probe = subprocess.run(cmd_probe, capture_output=True, text=True)
        duration = float(json.loads(probe.stdout)["format"]["duration"])
        target_bitrate = int((max_mb * 8 * 1024) / duration)  # kbps
        
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-b:v", f"{max(200, target_bitrate - 128)}k",
            "-b:a", "128k",
            "-vf", "scale=-2:720",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, timeout=300)
        
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        logger.warning(f"Compress failed: {e}")
    return None

# ─── تنزيل الوسائط ────────────────────────────────────────────────────────────

class DownloadProgress:
    """تتبع تقدم التنزيل"""
    def __init__(self, callback):
        self.callback = callback
        self.last_update = 0
        self.info = {}

    def hook(self, d: dict):
        if d["status"] == "downloading":
            now = time.time()
            if now - self.last_update < 2.5:  # تحديث كل 2.5 ثانية
                return
            self.last_update = now
            
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed", 0) or 0
            eta = d.get("eta", 0) or 0
            percent = (downloaded / total * 100) if total else 0
            
            self.info = {
                "percent": percent,
                "downloaded": downloaded,
                "total": total,
                "speed": speed,
                "eta": eta,
                "filename": d.get("filename", ""),
            }
            
            if self.callback:
                asyncio.run_coroutine_threadsafe(
                    self.callback(self.info),
                    asyncio.get_event_loop()
                )


def fetch_info_only(url: str) -> dict | None:
    """جلب معلومات الوسائط فقط بدون تنزيل"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": True,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        logger.error(f"Info fetch error: {e}")
        return None


def fetch_media(
    url: str,
    chat_id: int,
    format_choice: str = "video_best",
    progress_callback=None,
) -> dict | None:
    """
    تنزيل الوسائط مع دعم:
    - video_best: أفضل جودة فيديو
    - video_720: حتى 720p
    - video_480: حتى 480p
    - audio_mp3: صوت MP3
    - audio_m4a: صوت M4A
    """

    base_out = str(DOWNLOADS_DIR / f"{chat_id}_%(id)s")

    if format_choice == "audio_mp3":
        fmt = "bestaudio/best"
        post = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        out_ext = "mp3"
    elif format_choice == "audio_m4a":
        fmt = "bestaudio[ext=m4a]/bestaudio/best"
        post = []
        out_ext = "m4a"
    elif format_choice == "video_720":
        fmt = "bestvideo[height<=720][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=720]/best"
        post = []
        out_ext = "mp4"
    elif format_choice == "video_480":
        fmt = "bestvideo[height<=480][vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[height<=480]/best"
        post = []
        out_ext = "mp4"
    else:  # video_best
        fmt = "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best[ext=mp4]/best"
        post = []
        out_ext = "mp4"

    tracker = DownloadProgress(progress_callback)

    ydl_opts = {
        "format": fmt,
        "merge_output_format": "mp4" if "video" in format_choice else None,
        "outtmpl": f"{base_out}.%(ext)s",
        "writethumbnail": format_choice.startswith("video"),
        "external_downloader": "aria2c",
        "external_downloader_args": {
            "aria2c": ["-x16", "-s16", "-j4", "-k1M", "--allow-overwrite=true"]
        },
        "postprocessors": post,
        "progress_hooks": [tracker.hook],
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "noplaylist": True,  # تجنب تنزيل قوائم التشغيل بشكل تلقائي
        "max_filesize": MAX_FILE_SIZE_MB * 1024 * 1024 * 3,  # 3x buffer للفحص المسبق
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                return None

            # تحديد مسار الملف
            base = ydl.prepare_filename(info)
            base_name = os.path.splitext(base)[0]

            if format_choice.startswith("audio"):
                file_path = f"{base_name}.{out_ext}"
                if not os.path.exists(file_path):
                    # جرب أي ملف صوتي موجود
                    for ext in ["mp3", "m4a", "opus", "webm", "ogg"]:
                        candidate = f"{base_name}.{ext}"
                        if os.path.exists(candidate):
                            file_path = candidate
                            break
                thumb_path = None
            else:
                file_path = f"{base_name}.mp4"
                if not os.path.exists(file_path):
                    file_path = base

                # صورة الغلاف
                thumb_path = None
                for ext in ["jpg", "jpeg", "webp", "png"]:
                    t = f"{base_name}.{ext}"
                    if os.path.exists(t):
                        thumb_path = t
                        break

            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return None

            file_size = os.path.getsize(file_path)

            return {
                "file": file_path,
                "thumb": thumb_path,
                "title": info.get("title", "Media"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader") or info.get("channel", "Unknown"),
                "view_count": info.get("view_count", 0),
                "size": file_size,
                "format": format_choice,
                "width": info.get("width", 0),
                "height": info.get("height", 0),
            }

    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp Download Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected fetch error: {e}")
        return None


# ─── معالجات الأوامر ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛰 <b>AKRO MEDIA SYSTEM v3.0</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📥 أرسل رابط الفيديو وسأعرض عليك خيارات الجودة\n\n"
        "🌐 <b>المنصات المدعومة:</b>\n"
        "• YouTube • TikTok • Instagram\n"
        "• Twitter/X • Facebook • Twitch\n"
        "• Dailymotion • Vimeo • وأكثر من 1000 موقع\n\n"
        "⚡ <b>الميزات:</b>\n"
        "• اختيار جودة الفيديو (Best / 720p / 480p)\n"
        "• استخراج الصوت (MP3 / M4A)\n"
        "• ضغط تلقائي للملفات الكبيرة\n"
        "• شريط تقدم حي أثناء التنزيل\n"
        "• زر إلغاء فوري\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🔗 أرسل الرابط الآن!"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 <b>دليل AKRO MEDIA</b>\n\n"
        "1️⃣ أرسل رابط الفيديو\n"
        "2️⃣ اختر الصيغة المطلوبة من القائمة\n"
        "3️⃣ انتظر شريط التقدم\n"
        "4️⃣ استلم ملفك مباشرة!\n\n"
        "⚠️ <b>ملاحظات:</b>\n"
        "• الحد الأقصى للملف: 50MB\n"
        "• الفيديوهات الأكبر تُضغط تلقائياً\n"
        "• قد تستغرق الملفات الكبيرة وقتاً أطول\n\n"
        "🛠 <b>أوامر:</b>\n"
        "/start - الترحيب\n"
        "/help - هذه الرسالة\n"
        "/cancel - إلغاء التنزيل الحالي"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid in active_tasks and not active_tasks[uid].done():
        active_tasks[uid].cancel()
        await update.message.reply_text("🚫 <b>تم إلغاء التنزيل.</b>", parse_mode="HTML")
    else:
        await update.message.reply_text("⚪ لا يوجد تنزيل نشط حالياً.", parse_mode="HTML")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS and ADMIN_IDS:
        return
    
    uptime = datetime.now() - datetime.fromisoformat(bot_stats["started"])
    hours, rem = divmod(int(uptime.total_seconds()), 3600)
    mins = rem // 60
    
    text = (
        "📊 <b>AKRO System Stats</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⏱ وقت التشغيل: {hours}س {mins}د\n"
        f"✅ تنزيلات ناجحة: {bot_stats['total_downloads']}\n"
        f"❌ تنزيلات فاشلة: {bot_stats['failed_downloads']}\n"
        f"📦 البيانات المنقولة: {fmt_size(bot_stats['total_bytes'])}\n"
        f"👥 مستخدمون نشطون: {len(user_active_downloads)}\n"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ─── معالج الروابط ────────────────────────────────────────────────────────────

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        return

    user = update.effective_user
    uid = user.id

    # Rate limiting
    now = time.time()
    if uid in user_last_request:
        elapsed = now - user_last_request[uid]
        if elapsed < RATE_LIMIT_SECONDS:
            wait = int(RATE_LIMIT_SECONDS - elapsed) + 1
            await update.message.reply_text(
                f"⏳ انتظر <b>{wait}</b> ثانية قبل الطلب التالي.",
                parse_mode="HTML"
            )
            return

    # Queue limit
    if user_active_downloads[uid] >= MAX_QUEUE_PER_USER:
        await update.message.reply_text(
            "🔄 لديك تنزيلات نشطة. استخدم /cancel أو انتظر اكتمالها.",
            parse_mode="HTML"
        )
        return

    user_last_request[uid] = now

    # كشف قائمة التشغيل
    if is_playlist(url):
        url_id = str(uuid.uuid4())[:8]
        context.user_data[url_id] = url
        
        await update.message.reply_text(
            f"⚠️ <b>تم اكتشاف قائمة تشغيل!</b>\n"
            f"سيتم تنزيل أول {MAX_PLAYLIST_ITEMS} فيديوهات فقط.\n"
            "هل تريد المتابعة؟",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ نعم، تابع", callback_data=f"pl_confirm|{url_id}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="pl_cancel"),
            ]])
        )
        return

    await show_format_menu(update, context, url)


async def show_format_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """عرض قائمة اختيار الجودة"""
    msg = await update.message.reply_text(
        "🔍 <b>جاري قراءة معلومات الوسائط...</b>",
        parse_mode="HTML"
    )

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(executor, fetch_info_only, url)

    if not info:
        await msg.edit_text(
            "⚠️ <b>لم أستطع قراءة معلومات الرابط.</b>\n"
            "تأكد من صحة الرابط أو أن المحتوى متاح للعموم.",
            parse_mode="HTML"
        )
        return

    title = html.escape(clean_title(info.get("title", "Media")))
    duration_s = info.get("duration", 0) or 0
    duration_str = f"{int(duration_s//60)}:{int(duration_s%60):02d}" if duration_s else "غير محدد"
    uploader = html.escape(str(info.get("uploader") or info.get("channel", "Unknown"))[:40])
    
    # تخزين الرابط بمعرف قصير لتفادي خطأ Button_data_invalid الخاص بالحجم
    url_id = str(uuid.uuid4())[:8]
    context.user_data[url_id] = url
    cb = lambda choice: f"dl|{choice}|{url_id}"

    keyboard = [
        [
            InlineKeyboardButton("🎬 أفضل جودة", callback_data=cb("video_best")),
            InlineKeyboardButton("📺 720p", callback_data=cb("video_720")),
        ],
        [
            InlineKeyboardButton("📱 480p", callback_data=cb("video_480")),
            InlineKeyboardButton("🎵 MP3", callback_data=cb("audio_mp3")),
        ],
        [
            InlineKeyboardButton("🎧 M4A (أقل ضياناً)", callback_data=cb("audio_m4a")),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_menu"),
        ],
    ]

    text = (
        f"🎯 <b>{title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 {uploader}\n"
        f"⏱ المدة: {duration_str}\n\n"
        f"📌 اختر صيغة التنزيل:"
    )

    await msg.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))


# ─── معالج الأزرار ────────────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # إلغاء القائمة
    if data == "cancel_menu":
        await query.message.delete()
        return

    # إلغاء قائمة التشغيل
    if data == "pl_cancel":
        await query.message.edit_text("❌ <b>تم الإلغاء.</b>", parse_mode="HTML")
        return

    # تأكيد قائمة التشغيل
    if data.startswith("pl_confirm|"):
        url_id = data.split("|", 1)[1]
        url = context.user_data.get(url_id)
        if not url:
            await query.message.edit_text("❌ رابط منتهي الصلاحية. أرسل الرابط مجدداً.", parse_mode="HTML")
            return
            
        await query.message.delete()
        await show_format_menu(update, context, url)
        return

    # تنزيل
    if data.startswith("dl|"):
        parts = data.split("|", 2)
        if len(parts) != 3:
            await query.message.edit_text("❌ بيانات غير صالحة.", parse_mode="HTML")
            return

        _, format_choice, url_id = parts
        url = context.user_data.get(url_id)
        
        if not url:
            await query.message.edit_text("❌ رابط منتهي الصلاحية. أرسل الرابط مجدداً.", parse_mode="HTML")
            return

        uid = query.from_user.id
        task = asyncio.create_task(
            execute_download(query, context, url, format_choice, uid)
        )
        active_tasks[str(uid)] = task


async def execute_download(query, context, url: str, format_choice: str, uid: int):
    """تنفيذ التنزيل مع تحديثات مباشرة"""
    user_active_downloads[uid] += 1
    start_time = time.time()
    status_msg = query.message
    result = None
    compressed_path = None

    FORMAT_LABELS = {
        "video_best": "🎬 أفضل جودة",
        "video_720": "📺 720p",
        "video_480": "📱 480p",
        "audio_mp3": "🎵 MP3",
        "audio_m4a": "🎧 M4A",
    }
    label = FORMAT_LABELS.get(format_choice, format_choice)

    async def update_progress(info: dict):
        """تحديث رسالة التقدم"""
        percent = info.get("percent", 0)
        downloaded = info.get("downloaded", 0)
        total = info.get("total", 0)
        speed = info.get("speed", 0)
        eta = info.get("eta", 0)

        bar = progress_bar(percent)
        size_info = f"{fmt_size(downloaded)}/{fmt_size(total)}" if total else fmt_size(downloaded)

        text = (
            f"⬇️ <b>جاري التنزيل... {label}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{bar} <b>{percent:.1f}%</b>\n\n"
            f"📦 {size_info}\n"
            f"⚡ {fmt_speed(speed)}\n"
            f"⏳ متبقي: {fmt_eta(eta)}\n\n"
            f"🚫 /cancel للإلغاء"
        )
        try:
            await status_msg.edit_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🚫 إلغاء التنزيل", callback_data="cancel_menu")
                ]])
            )
        except TelegramError:
            pass

    try:
        await status_msg.edit_text(
            f"⚙️ <b>تحضير التنزيل...</b>\n{label}",
            parse_mode="HTML"
        )

        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor, fetch_media, url, uid, format_choice, update_progress
            ),
            timeout=600  # 10 دقائق كحد أقصى
        )

        if not result or not os.path.exists(result["file"]):
            raise ValueError("الملف لم يتم إنشاؤه بعد التنزيل")

        file_size = result["size"]
        limit = MAX_FILE_SIZE_MB * 1024 * 1024

        # ضغط إذا كان الملف كبيراً
        if file_size > limit and format_choice.startswith("video"):
            await status_msg.edit_text(
                f"📦 <b>الملف ({fmt_size(file_size)}) أكبر من الحد.</b>\n"
                "🗜 جاري الضغط التلقائي...",
                parse_mode="HTML"
            )
            compressed_path = await loop.run_in_executor(
                executor, compress_video, result["file"], MAX_FILE_SIZE_MB
            )
            if compressed_path and compressed_path != result["file"]:
                result["file"] = compressed_path
                result["size"] = os.path.getsize(compressed_path)
                file_size = result["size"]

        if file_size > limit:
            await status_msg.edit_text(
                f"⚠️ <b>حجم الملف ({fmt_size(file_size)}) يتجاوز حد Telegram (50MB).</b>\n\n"
                "💡 جرب اختيار جودة أقل مثل 480p أو MP3.",
                parse_mode="HTML"
            )
            bot_stats["failed_downloads"] += 1
            return

        # رفع الملف
        elapsed = time.time() - start_time
        await status_msg.edit_text(
            f"🚀 <b>رفع الملف...</b>\n{label} | {fmt_size(file_size)}",
            parse_mode="HTML"
        )

        title = html.escape(clean_title(result["title"]))
        uploader = html.escape(str(result.get("uploader", "Unknown"))[:40])
        duration = result.get("duration", 0)
        dur_str = f"{int(duration//60)}:{int(duration%60):02d}" if duration else ""

        caption = (
            f"🛰 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 {uploader}\n"
        )
        if dur_str:
            caption += f"⏱ {dur_str}\n"
        caption += (
            f"📦 {fmt_size(file_size)}\n"
            f"📡 <b>AKRO MEDIA SYSTEM</b>"
        )

        chat_id = query.message.chat_id
        thumb_file = None

        with open(result["file"], "rb") as media_file:
            if format_choice.startswith("audio"):
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=media_file,
                    caption=caption,
                    title=result["title"][:60],
                    performer="AKRO Media",
                    parse_mode="HTML",
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=60,
                )
            else:
                if result.get("thumb") and os.path.exists(result["thumb"]):
                    thumb_file = open(result["thumb"], "rb")

                await context.bot.send_video(
                    chat_id=chat_id,
                    video=media_file,
                    caption=caption,
                    thumbnail=thumb_file,
                    supports_streaming=True,
                    width=result.get("width", 0) or None,
                    height=result.get("height", 0) or None,
                    duration=int(duration) or None,
                    parse_mode="HTML",
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=60,
                )

        if thumb_file:
            thumb_file.close()

        # إحصائيات
        total_elapsed = time.time() - start_time
        bot_stats["total_downloads"] += 1
        bot_stats["total_bytes"] += file_size

        await status_msg.delete()
        logger.info(
            f"✅ Upload success | user={uid} | format={format_choice} | "
            f"size={fmt_size(file_size)} | time={total_elapsed:.1f}s"
        )

    except asyncio.CancelledError:
        await status_msg.edit_text("🚫 <b>تم إلغاء التنزيل.</b>", parse_mode="HTML")
        bot_stats["failed_downloads"] += 1

    except asyncio.TimeoutError:
        await status_msg.edit_text(
            "⏰ <b>انتهت مهلة التنزيل (10 دقائق).</b>\n"
            "جرب رابطاً آخر أو جودة أقل.",
            parse_mode="HTML"
        )
        bot_stats["failed_downloads"] += 1

    except Exception as e:
        logger.error(f"Download execution error: {e}", exc_info=True)
        await status_msg.edit_text(
            "🚫 <b>خطأ في المعالجة.</b>\n\n"
            f"<code>{html.escape(str(e)[:200])}</code>",
            parse_mode="HTML"
        )
        bot_stats["failed_downloads"] += 1

    finally:
        # تنظيف الملفات
        user_active_downloads[uid] = max(0, user_active_downloads[uid] - 1)

        files_to_clean = []
        if result:
            files_to_clean.append(result.get("file"))
            files_to_clean.append(result.get("thumb"))
        if compressed_path:
            files_to_clean.append(compressed_path)

        for f in files_to_clean:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

        # تنظيف الملفات اليتيمة في مجلد التنزيل
        try:
            for old_file in DOWNLOADS_DIR.glob(f"{uid}_*"):
                if time.time() - old_file.stat().st_mtime > 3600:  # أقدم من ساعة
                    old_file.unlink(missing_ok=True)
        except Exception:
            pass

        if str(uid) in active_tasks:
            del active_tasks[str(uid)]


# ─── معالج الأخطاء العام ──────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Global error: {context.error}", exc_info=context.error)


# ─── نقطة الدخول ──────────────────────────────────────────────────────────────

def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("❌ ضع التوكن في متغير البيئة BOT_TOKEN أو في الكود مباشرة")

    # تأكد من وجود مجلد التنزيلات
    DOWNLOADS_DIR.mkdir(exist_ok=True)

    app = Application.builder().token(TOKEN).build()

    # أوامر
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # الرسائل والأزرار
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_callback))

    # معالج الأخطاء
    app.add_error_handler(error_handler)

    print("""
╔══════════════════════════════════════════╗
║     💎 AKRO MEDIA SYSTEM v3.0 ONLINE    ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   ║
║  Workers: 6  |  Max File: 49MB          ║
║  Rate Limit: 10s | Queue: 2/user        ║
╚══════════════════════════════════════════╝
""")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
