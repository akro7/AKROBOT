"""
╔══════════════════════════════════════════════╗
║     AKRO EKO TURBO - TWRP Bot v2.0          ║
║     يدعم 1800+ موقع عبر yt-dlp              ║
╚══════════════════════════════════════════════╝

تثبيت المتطلبات:
    pip install pyTelegramBotAPI requests yt-dlp gdown

لدعم Mega.nz (اختياري):
    pip install mega.py

لدعم Google Drive الكبيرة:
    pip install gdown
"""

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import telebot
import requests

# ─── المتطلبات الاختيارية ─────────────────────────────────────────────────────
try:
    import yt_dlp
    YTDLP_OK = True
except ImportError:
    YTDLP_OK = False
    print("⚠️ yt-dlp غير مثبت — شغّل: pip install yt-dlp")

try:
    import gdown
    GDOWN_OK = True
except ImportError:
    GDOWN_OK = False

try:
    from mega import Mega
    MEGA_OK = True
except ImportError:
    MEGA_OK = False

# ─── إعدادات البوت ────────────────────────────────────────────────────────────
TOKEN   = '8067365706:AAFCnoBEiKB8ghHrN1Zo1qO_rKoimzrmcoE'
bot     = telebot.TeleBot(TOKEN, threaded=True)

TELEGRAM_LIMIT = 20 * 1024 * 1024   # 20 MB
CHUNK           = 65536               # 64 KB

# ══════════════════════════════════════════════════════════════════════════════
#  الكشف التلقائي عن نوع الرابط
# ══════════════════════════════════════════════════════════════════════════════
def detect_source(url: str) -> str:
    """يُرجع: 'gdrive' | 'mega' | 'direct' | 'ytdlp'"""
    if re.search(r'drive\.google\.com|docs\.google\.com', url):
        return 'gdrive'
    if re.search(r'mega\.nz|mega\.co\.nz', url):
        return 'mega'
    # روابط مباشرة لملفات img/zip/tar
    if re.search(r'\.(img|zip|tar\.gz|tar)(\?.*)?$', url, re.I):
        return 'direct'
    return 'ytdlp'   # yt-dlp يجرب 1800+ موقع


# ══════════════════════════════════════════════════════════════════════════════
#  محركات التحميل
# ══════════════════════════════════════════════════════════════════════════════

def download_direct(url: str, dest: str, progress_cb=None) -> str:
    """تحميل رابط مباشر HTTP/HTTPS مع متابعة التقدم"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0 Safari/537.36'
    }
    with requests.get(url, stream=True, timeout=600, headers=headers) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        downloaded = 0
        last_report = 0
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=CHUNK):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total and downloaded - last_report > 5 * 1024 * 1024:
                    pct = downloaded / total * 100
                    progress_cb(f"⬇️ {downloaded/1024/1024:.1f} / {total/1024/1024:.1f} MB  ({pct:.0f}%)")
                    last_report = downloaded
    return dest


def download_gdrive(url: str, dest: str) -> str:
    """Google Drive عبر gdown — يتخطى حد الـ 15MB"""
    if not GDOWN_OK:
        raise RuntimeError("gdown غير مثبت.\nشغّل: pip install gdown")
    # استخراج file_id
    m = re.search(r'/d/([^/]+)|id=([^&]+)', url)
    if not m:
        raise ValueError("لم أتعرف على رابط Google Drive.")
    file_id = m.group(1) or m.group(2)
    gdown.download(id=file_id, output=dest, quiet=False, fuzzy=True)
    if not os.path.exists(dest):
        raise RuntimeError("فشل التحميل من Google Drive.")
    return dest


def download_mega(url: str, dest_dir: str) -> str:
    """Mega.nz عبر mega.py"""
    if not MEGA_OK:
        raise RuntimeError("mega.py غير مثبت.\nشغّل: pip install mega.py")
    mega = Mega()
    m = mega.login()
    downloaded = m.download_url(url, dest_path=dest_dir)
    return str(downloaded)


def download_ytdlp(url: str, dest_dir: str, progress_cb=None) -> str:
    """
    yt-dlp — يدعم 1800+ موقع.
    يُستخدم هنا لتحميل الملف كما هو (ليس فيديو بالضرورة).
    """
    if not YTDLP_OK:
        raise RuntimeError("yt-dlp غير مثبت.\nشغّل: pip install yt-dlp")

    outtmpl = os.path.join(dest_dir, '%(title)s.%(ext)s')
    last_msg = {'t': 0}

    def hook(d):
        if d['status'] == 'downloading' and progress_cb:
            now = time.time()
            if now - last_msg['t'] > 3:
                downloaded = d.get('downloaded_bytes', 0)
                total      = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                speed      = d.get('speed', 0) or 0
                if total:
                    pct = downloaded / total * 100
                    progress_cb(
                        f"⬇️ {downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB "
                        f"({pct:.0f}%)  🚀 {speed/1024:.0f} KB/s"
                    )
                last_msg['t'] = now

    ydl_opts = {
        'outtmpl'        : outtmpl,
        'progress_hooks' : [hook],
        'quiet'          : True,
        'no_warnings'    : True,
        # تحميل أفضل جودة (لكن بدون دمج — نريد ملف واحد)
        'format'         : 'bestaudio/best/bestvideo/best',
        # تخطي الأخطاء وإكمال التحميل
        'ignoreerrors'   : False,
        'retries'        : 5,
        'concurrent_fragment_downloads': 4,
        # لو الملف أكبر من 2GB
        'buffersize'     : 1024 * 16,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        # أحياناً يختلف الامتداد بعد التحويل
        if not os.path.exists(filename):
            # نبحث عن أحدث ملف في المجلد
            files = sorted(
                [os.path.join(dest_dir, f) for f in os.listdir(dest_dir)],
                key=os.path.getmtime, reverse=True
            )
            if files:
                filename = files[0]
            else:
                raise RuntimeError("لم يُوجد ملف بعد التحميل.")
    return filename


# ══════════════════════════════════════════════════════════════════════════════
#  المحرك الرئيسي: التحميل الذكي
# ══════════════════════════════════════════════════════════════════════════════

def smart_download(url: str, work_dir: str, progress_cb=None) -> str:
    """
    يختار المحرك المناسب تلقائياً ويُرجع مسار الملف المحمّل.
    """
    source = detect_source(url)
    rec_dir = os.path.join(work_dir, 'recovery')
    os.makedirs(rec_dir, exist_ok=True)
    dest_file = os.path.join(rec_dir, 'recovery.img')

    if source == 'gdrive':
        progress_cb and progress_cb("☁️ Google Drive مكتشف — جارٍ التحميل...")
        return download_gdrive(url, dest_file)

    elif source == 'mega':
        progress_cb and progress_cb("☁️ Mega.nz مكتشف — جارٍ التحميل...")
        downloaded = download_mega(url, rec_dir)
        # أعد تسمية أي ملف .img موجود
        for f in os.listdir(rec_dir):
            if f.endswith('.img'):
                full = os.path.join(rec_dir, f)
                if full != dest_file:
                    os.rename(full, dest_file)
        return dest_file

    elif source == 'direct':
        progress_cb and progress_cb("🔗 رابط مباشر — جارٍ التحميل...")
        return download_direct(url, dest_file, progress_cb)

    else:  # ytdlp
        progress_cb and progress_cb(f"🌐 yt-dlp (1800+ موقع) — جارٍ التحميل...")
        downloaded = download_ytdlp(url, rec_dir, progress_cb)
        if downloaded != dest_file:
            shutil.move(downloaded, dest_file)
        return dest_file


# ══════════════════════════════════════════════════════════════════════════════
#  توليد Device Tree
# ══════════════════════════════════════════════════════════════════════════════

AKRO_PATCHES = """
# --- AKRO Custom Patches ---
TW_VARIANT := AKRO-UNOFFICIAL
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_DEVICE_VERSION := AKRO_V2
TW_USE_TOOLBOX := true
"""

def generate_tree(rec_path: str, output_path: str):
    result = subprocess.run(
        ['python3', '-m', 'twrpdtgen', rec_path, '-o', output_path],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        raise RuntimeError(f"فشل twrpdtgen:\n{result.stderr[-600:]}")

def apply_patches(output_path: str):
    for root, _, files in os.walk(output_path):
        if 'BoardConfig.mk' in files:
            with open(os.path.join(root, 'BoardConfig.mk'), 'a', encoding='utf-8') as f:
                f.write(AKRO_PATCHES)
            break


# ══════════════════════════════════════════════════════════════════════════════
#  الدالة الرئيسية: معالجة الريكفري كاملةً
# ══════════════════════════════════════════════════════════════════════════════

def process_recovery(message, url: str):
    chat_id  = message.chat.id
    work_dir = f"work_{chat_id}_{int(time.time())}"
    zip_name = f"TWRP_Tree_{chat_id}"
    zip_path = f"{zip_name}.zip"
    status_msg = None

    def progress(text):
        nonlocal status_msg
        try:
            if status_msg:
                bot.edit_message_text(text, chat_id, status_msg.message_id)
            else:
                status_msg = bot.send_message(chat_id, text)
        except Exception:
            pass

    try:
        os.makedirs(work_dir, exist_ok=True)
        output_path = os.path.join(work_dir, 'output')

        # 1. تحميل ذكي
        rec_path = smart_download(url, work_dir, progress_cb=progress)

        size_mb = os.path.getsize(rec_path) / 1024 / 1024
        progress(f"✅ تم التحميل ({size_mb:.1f} MB)\n⚙️ جارٍ توليد الـ Device Tree...")

        # 2. توليد الـ Tree
        generate_tree(rec_path, output_path)

        # 3. تطبيق AKRO Patches
        apply_patches(output_path)

        # 4. ضغط
        progress("📦 جارٍ ضغط الملفات...")
        shutil.make_archive(zip_name, 'zip', output_path)

        if not os.path.exists(zip_path):
            raise RuntimeError("فشل إنشاء ملف ZIP.")

        zip_mb = os.path.getsize(zip_path) / 1024 / 1024

        # 5. إرسال
        progress("📤 جارٍ إرسال الملف...")
        with open(zip_path, 'rb') as f:
            bot.send_document(
                chat_id, f,
                caption=(
                    f"✅ *TWRP Device Tree جاهز!*\n"
                    f"📦 الحجم: `{zip_mb:.2f} MB`\n"
                    f"🛠 بواسطة: *AKRO EKO TURBO v2*"
                ),
                parse_mode='Markdown'
            )
        # حذف رسالة الحالة
        if status_msg:
            try: bot.delete_message(chat_id, status_msg.message_id)
            except: pass

    except Exception as e:
        err = str(e)
        bot.send_message(chat_id, f"❌ *خطأ:*\n`{err[:500]}`", parse_mode='Markdown')

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)


# ══════════════════════════════════════════════════════════════════════════════
#  معالجات رسائل Telegram
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    caps = "\n".join([
        "✅ yt-dlp (1800+ موقع)" if YTDLP_OK  else "❌ yt-dlp (غير مثبت)",
        "✅ Google Drive"         if GDOWN_OK  else "❌ Google Drive (pip install gdown)",
        "✅ Mega.nz"              if MEGA_OK   else "❌ Mega.nz  (pip install mega.py)",
        "✅ روابط مباشرة (دائماً)",
        "✅ Telegram (حتى 20MB)",
    ])
    text = (
        "⚡️ *AKRO EKO TURBO — v2.0*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🌐 *المواقع المدعومة:*\n"
        f"{caps}\n\n"
        "📤 *طرق الإرسال:*\n"
        "1️⃣ أرسل ملف `.img` مباشرةً (حتى 20MB)\n"
        "2️⃣ `/url <رابط>` — من أي موقع\n"
        "3️⃣ أرسل الرابط مباشرةً في الرسالة\n\n"
        "💡 *أمثلة روابط مقبولة:*\n"
        "`/url https://drive.google.com/file/d/XXX`\n"
        "`/url https://mega.nz/file/XXX`\n"
        "`/url https://mediafire.com/file/XXX`\n"
        "`/url https://github.com/.../recovery.img`\n"
        "`/url https://sourceforge.net/...`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 بواسطة: *AKRO EKO TURBO*"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


@bot.message_handler(commands=['url'])
def cmd_url(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().startswith('http'):
        bot.reply_to(
            message,
            "📌 الاستخدام:\n`/url https://رابط-الريكفري`",
            parse_mode='Markdown'
        )
        return
    url = parts[1].strip()
    source = detect_source(url)
    icons = {'gdrive': '☁️ Google Drive', 'mega': '☁️ Mega.nz',
             'direct': '🔗 رابط مباشر', 'ytdlp': '🌐 yt-dlp'}
    bot.reply_to(message, f"🔍 المصدر: *{icons[source]}*\n⏳ جارٍ المعالجة...", parse_mode='Markdown')
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()


@bot.message_handler(content_types=['document'])
def handle_file(message):
    doc = message.document
    if not doc.file_name.endswith('.img'):
        bot.reply_to(message, "⚠️ أرسل ملفاً ينتهي بـ `.img` فقط.")
        return

    if doc.file_size > TELEGRAM_LIMIT:
        mb = doc.file_size / 1024 / 1024
        bot.reply_to(
            message,
            f"⚠️ الملف {mb:.1f}MB — يتجاوز حد تيليجرام (20MB).\n\n"
            "📌 الحل — ارفعه على أي موقع وأرسل:\n"
            "`/url https://رابط-الملف`\n\n"
            "🌐 مواقع مجانية مقترحة:\n"
            "• gofile.io\n• transfer.sh\n• pixeldrain.com\n• Google Drive",
            parse_mode='Markdown'
        )
        return

    size_mb = doc.file_size / 1024 / 1024
    bot.reply_to(message, f"📥 الملف: {doc.file_name} ({size_mb:.1f}MB)\n⏳ جارٍ المعالجة...")

    try:
        file_info = bot.get_file(doc.file_id)
        url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()
    except Exception as e:
        bot.reply_to(message, f"❌ فشل الحصول على الملف: `{e}`", parse_mode='Markdown')


@bot.message_handler(func=lambda m: m.text and re.search(r'https?://\S+', m.text))
def handle_raw_url(message):
    """يستقبل أي رابط يُرسل كنص عادي"""
    match = re.search(r'(https?://\S+)', message.text)
    if not match:
        return
    url = match.group(1)
    source = detect_source(url)
    icons = {'gdrive': '☁️ Google Drive', 'mega': '☁️ Mega.nz',
             'direct': '🔗 رابط مباشر', 'ytdlp': '🌐 yt-dlp'}
    bot.reply_to(
        message,
        f"🔍 اكتشفت رابطاً ({icons[source]})\n⏳ جارٍ المعالجة...",
        parse_mode='Markdown'
    )
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
print("⚡️ AKRO EKO TURBO v2.0 يعمل...")
print(f"   yt-dlp  : {'✅' if YTDLP_OK else '❌'}")
print(f"   gdown   : {'✅' if GDOWN_OK else '❌'}")
print(f"   mega.py : {'✅' if MEGA_OK  else '❌'}")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
