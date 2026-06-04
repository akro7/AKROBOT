"""
╔══════════════════════════════════════════════╗
║     AKRO EKO TURBO - TWRP Bot v3.0          ║
║     مع إصلاح MediaFire + التحقق من الملف    ║
╚══════════════════════════════════════════════╝

pip install pyTelegramBotAPI requests yt-dlp gdown beautifulsoup4 lxml
"""

import os, re, shutil, subprocess, threading, time
import telebot
import requests
from bs4 import BeautifulSoup

# ─── المكتبات الاختيارية ──────────────────────────────────────────────────────
try:
    import yt_dlp;   YTDLP_OK = True
except ImportError:
    YTDLP_OK = False

try:
    import gdown;    GDOWN_OK = True
except ImportError:
    GDOWN_OK = False

try:
    from mega import Mega; MEGA_OK = True
except ImportError:
    MEGA_OK = False

# ─── إعدادات ──────────────────────────────────────────────────────────────────
TOKEN          = '8067365706:AAHFQ2gJk4COdq3QjwVomoxXxPPbbYw7SSc'
bot            = telebot.TeleBot(TOKEN, threaded=True)
TELEGRAM_LIMIT = 20 * 1024 * 1024   # 20 MB
MIN_IMG_SIZE   = 1 * 1024 * 1024    # 1 MB حد أدنى للملف الصحيح
CHUNK          = 65536

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

AKRO_PATCHES = """
# --- AKRO Custom Patches ---
TW_VARIANT := AKRO-UNOFFICIAL
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_DEVICE_VERSION := AKRO_V3
TW_USE_TOOLBOX := true
"""

# ══════════════════════════════════════════════════════════════════════════════
#  🔍 كشف المصدر
# ══════════════════════════════════════════════════════════════════════════════
def detect_source(url: str) -> str:
    if re.search(r'drive\.google\.com|docs\.google\.com', url):    return 'gdrive'
    if re.search(r'mega\.nz|mega\.co\.nz', url):                   return 'mega'
    if re.search(r'mediafire\.com', url):                           return 'mediafire'
    if re.search(r'\.(img|zip|tar\.gz|tar)(\?.*)?$', url, re.I):  return 'direct'
    return 'ytdlp'


# ══════════════════════════════════════════════════════════════════════════════
#  ✅ التحقق من صحة الملف المحمَّل
# ══════════════════════════════════════════════════════════════════════════════
def validate_file(path: str) -> str:
    """
    يتحقق أن الملف:
    1. موجود وليس فارغاً
    2. حجمه > 1MB
    3. ليس HTML (أي لم يحدث redirect لصفحة ويب)
    يُرجع رسالة الخطأ أو None إذا كان الملف صحيحاً
    """
    if not os.path.exists(path):
        return "الملف غير موجود بعد التحميل."

    size = os.path.getsize(path)
    if size == 0:
        return "الملف فارغ (0 bytes) — الرابط لا يُنزِّل ملفاً حقيقياً."

    if size < MIN_IMG_SIZE:
        return (f"الملف صغير جداً ({size/1024:.1f} KB) — "
                f"على الأرجح صفحة HTML وليس ريكفري حقيقي.")

    # تحقق من أول bytes — HTML يبدأ بـ <!DOCTYPE أو <html
    with open(path, 'rb') as f:
        header = f.read(512)
    text_start = header[:20].lower()
    if b'<!doctype' in text_start or b'<html' in text_start:
        return ("الرابط أعاد صفحة HTML بدل الملف.\n"
                "تأكد أن الرابط رابط تحميل مباشر وليس صفحة موقع.")

    return None  # الملف صحيح


# ══════════════════════════════════════════════════════════════════════════════
#  🌐 MediaFire Scraper — يستخرج الرابط المباشر
# ══════════════════════════════════════════════════════════════════════════════
def resolve_mediafire(url: str) -> str:
    """
    يفتح صفحة MediaFire ويستخرج رابط التحميل المباشر الحقيقي.
    يدعم:
      - https://www.mediafire.com/file/XXXXX/filename/file
      - https://download1321.mediafire.com/... (مباشر)
    """
    # إذا كان رابطاً مباشراً من download*.mediafire.com
    if re.search(r'download\d+\.mediafire\.com', url):
        return url  # هو بالفعل مباشر

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"فشل فتح صفحة MediaFire: {e}")

    soup = BeautifulSoup(resp.text, 'lxml')

    # طريقة 1: زر التحميل الرئيسي
    btn = soup.find('a', {'id': 'downloadButton'})
    if btn and btn.get('href'):
        return btn['href']

    # طريقة 2: أي رابط مباشر لـ download*.mediafire
    match = re.search(r'(https://download\d+\.mediafire\.com/[^\s"\'<>]+)', resp.text)
    if match:
        return match.group(1)

    # طريقة 3: og:url أو canonical link
    og = soup.find('meta', property='og:url')
    if og and 'mediafire.com' in (og.get('content', '')):
        # جرب مرة أخرى على الرابط المُنظَّف
        pass

    raise RuntimeError(
        "لم أتمكن من استخراج رابط التحميل من MediaFire.\n"
        "تأكد أن الرابط عام وغير محمي بكلمة مرور.\n"
        "جرب الرفع على gofile.io أو Google Drive."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ⬇️ محركات التحميل
# ══════════════════════════════════════════════════════════════════════════════

def download_direct(url: str, dest: str, progress_cb=None) -> str:
    with requests.get(url, stream=True, timeout=600,
                      headers=HEADERS, allow_redirects=True) as r:
        r.raise_for_status()
        total = int(r.headers.get('content-length', 0))
        done, last = 0, 0
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(chunk_size=CHUNK):
                f.write(chunk)
                done += len(chunk)
                if progress_cb and total and done - last > 5*1024*1024:
                    progress_cb(f"⬇️ {done/1024/1024:.1f}/{total/1024/1024:.1f} MB "
                                f"({done/total*100:.0f}%)")
                    last = done
    return dest


def download_gdrive(url: str, dest: str) -> str:
    if not GDOWN_OK:
        raise RuntimeError("gdown غير مثبت: pip install gdown")
    m = re.search(r'/d/([^/?\s]+)|[?&]id=([^&\s]+)', url)
    if not m:
        raise ValueError("رابط Google Drive غير صحيح.")
    file_id = m.group(1) or m.group(2)
    gdown.download(id=file_id, output=dest, quiet=False, fuzzy=True)
    if not os.path.exists(dest):
        raise RuntimeError("فشل التحميل من Google Drive.")
    return dest


def download_mega(url: str, dest_dir: str) -> str:
    if not MEGA_OK:
        raise RuntimeError("mega.py غير مثبت: pip install mega.py")
    m = Mega().login()
    downloaded = m.download_url(url, dest_path=dest_dir)
    return str(downloaded)


def download_ytdlp(url: str, dest_dir: str, progress_cb=None) -> str:
    if not YTDLP_OK:
        raise RuntimeError("yt-dlp غير مثبت: pip install yt-dlp")

    outtmpl   = os.path.join(dest_dir, '%(title)s.%(ext)s')
    last_t    = {'v': 0}

    def hook(d):
        if d['status'] == 'downloading' and progress_cb:
            if time.time() - last_t['v'] > 3:
                dl    = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                spd   = d.get('speed', 0) or 0
                if total:
                    progress_cb(f"⬇️ {dl/1024/1024:.1f}/{total/1024/1024:.1f} MB "
                                f"({dl/total*100:.0f}%) 🚀{spd/1024:.0f}KB/s")
                last_t['v'] = time.time()

    ydl_opts = {
        'outtmpl': outtmpl, 'progress_hooks': [hook],
        'quiet': True, 'no_warnings': True,
        'format': 'bestaudio/best/bestvideo/best',
        'retries': 5, 'concurrent_fragment_downloads': 4,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info     = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if not os.path.exists(filename):
            files = sorted(
                [os.path.join(dest_dir, f) for f in os.listdir(dest_dir)],
                key=os.path.getmtime, reverse=True)
            filename = files[0] if files else None
        if not filename:
            raise RuntimeError("yt-dlp: لم يُنزَّل أي ملف.")
    return filename


# ══════════════════════════════════════════════════════════════════════════════
#  🧠 التحميل الذكي مع fallback
# ══════════════════════════════════════════════════════════════════════════════
def smart_download(url: str, work_dir: str, progress_cb=None) -> str:
    source   = detect_source(url)
    rec_dir  = os.path.join(work_dir, 'recovery')
    os.makedirs(rec_dir, exist_ok=True)
    dest     = os.path.join(rec_dir, 'recovery.img')

    # ── Google Drive ──────────────────────────────────────────────────────────
    if source == 'gdrive':
        progress_cb and progress_cb("☁️ Google Drive — جارٍ التحميل...")
        download_gdrive(url, dest)

    # ── Mega.nz ───────────────────────────────────────────────────────────────
    elif source == 'mega':
        progress_cb and progress_cb("☁️ Mega.nz — جارٍ التحميل...")
        dl = download_mega(url, rec_dir)
        if dl != dest and os.path.exists(dl):
            shutil.move(dl, dest)

    # ── MediaFire (يحتاج scraping) ────────────────────────────────────────────
    elif source == 'mediafire':
        progress_cb and progress_cb("🔍 MediaFire — جارٍ استخراج رابط التحميل...")
        real_url = resolve_mediafire(url)
        progress_cb and progress_cb(f"✅ رابط مباشر مستخرج\n⬇️ جارٍ التحميل...")
        download_direct(real_url, dest, progress_cb)

    # ── رابط مباشر + fallback على yt-dlp ─────────────────────────────────────
    elif source == 'direct':
        progress_cb and progress_cb("🔗 رابط مباشر — جارٍ التحميل...")
        try:
            download_direct(url, dest, progress_cb)
            err = validate_file(dest)
            if err:
                # الرابط المباشر فشل → جرب yt-dlp
                progress_cb and progress_cb(
                    f"⚠️ الرابط المباشر أعطى ملفاً خاطئاً.\n"
                    f"🔄 جارٍ المحاولة عبر yt-dlp...")
                if os.path.exists(dest): os.remove(dest)
                dl = download_ytdlp(url, rec_dir, progress_cb)
                if dl != dest and os.path.exists(dl):
                    shutil.move(dl, dest)
        except requests.HTTPError as e:
            if '404' in str(e) or '403' in str(e):
                raise RuntimeError(
                    f"❌ الرابط لا يعمل ({e.response.status_code}).\n"
                    "تأكد أن الرابط صحيح ومتاح للعموم.\n"
                    "جرب رفع الملف على gofile.io أو Google Drive.")
            raise

    # ── yt-dlp (1800+ موقع) ───────────────────────────────────────────────────
    else:
        progress_cb and progress_cb("🌐 yt-dlp (1800+ موقع) — جارٍ التحميل...")
        dl = download_ytdlp(url, rec_dir, progress_cb)
        if dl != dest and os.path.exists(dl):
            shutil.move(dl, dest)

    # ── التحقق النهائي من الملف ──────────────────────────────────────────────
    err = validate_file(dest)
    if err:
        raise RuntimeError(f"⚠️ الملف غير صالح:\n{err}")

    return dest


# ══════════════════════════════════════════════════════════════════════════════
#  ⚙️ توليد Device Tree
# ══════════════════════════════════════════════════════════════════════════════
def generate_tree(rec_path: str, output_path: str):
    result = subprocess.run(
        ['python3', '-m', 'twrpdtgen', rec_path, '-o', output_path],
        capture_output=True, text=True, timeout=300
    )
    if result.returncode != 0:
        stderr = result.stderr
        # تحليل الخطأ لإعطاء رسالة أوضح
        if 'unpackimg' in stderr or 'aik' in stderr:
            raise RuntimeError(
                "فشل فك تشفير الـ recovery.img\n"
                "السبب المحتمل: الملف تالف أو نوعه غير مدعوم.\n"
                f"التفاصيل: {stderr[-300:]}")
        raise RuntimeError(f"فشل twrpdtgen:\n{stderr[-400:]}")


def apply_patches(output_path: str):
    for root, _, files in os.walk(output_path):
        if 'BoardConfig.mk' in files:
            with open(os.path.join(root, 'BoardConfig.mk'), 'a', encoding='utf-8') as f:
                f.write(AKRO_PATCHES)
            break


# ══════════════════════════════════════════════════════════════════════════════
#  🚀 المعالج الرئيسي
# ══════════════════════════════════════════════════════════════════════════════
def process_recovery(message, url: str):
    chat_id    = message.chat.id
    work_dir   = f"work_{chat_id}_{int(time.time())}"
    zip_name   = f"TWRP_Tree_{chat_id}"
    zip_path   = f"{zip_name}.zip"
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

        # 1. تحميل ذكي مع تحقق
        rec_path = smart_download(url, work_dir, progress_cb=progress)

        size_mb = os.path.getsize(rec_path) / 1024 / 1024
        progress(f"✅ تم التحميل ({size_mb:.1f} MB)\n⚙️ جارٍ توليد الـ Device Tree...")

        # 2. توليد الـ Tree
        generate_tree(rec_path, output_path)

        # 3. AKRO Patches
        apply_patches(output_path)

        # 4. ضغط
        progress("📦 جارٍ ضغط الملفات...")
        shutil.make_archive(zip_name, 'zip', output_path)
        if not os.path.exists(zip_path):
            raise RuntimeError("فشل إنشاء ملف ZIP.")

        # 5. إرسال
        zip_mb = os.path.getsize(zip_path) / 1024 / 1024
        progress("📤 جارٍ إرسال الملف...")
        with open(zip_path, 'rb') as f:
            bot.send_document(
                chat_id, f,
                caption=(f"✅ *TWRP Device Tree جاهز!*\n"
                         f"📦 الحجم: `{zip_mb:.2f} MB`\n"
                         f"🛠 بواسطة: *AKRO EKO TURBO v3*"),
                parse_mode='Markdown')

        if status_msg:
            try: bot.delete_message(chat_id, status_msg.message_id)
            except: pass

    except Exception as e:
        err = str(e)
        bot.send_message(chat_id,
            f"❌ *خطأ:*\n`{err[:600]}`\n\n"
            "💡 *نصيحة:* تأكد أن الرابط مباشر وعام، أو ارفع الملف على:\n"
            "• gofile.io\n• drive.google.com\n• pixeldrain.com",
            parse_mode='Markdown')

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)


# ══════════════════════════════════════════════════════════════════════════════
#  📨 معالجات Telegram
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    caps = "\n".join([
        f"{'✅' if YTDLP_OK else '❌'} yt-dlp (1800+ موقع)",
        f"{'✅' if GDOWN_OK else '❌'} Google Drive",
        f"{'✅' if MEGA_OK  else '❌'} Mega.nz",
        "✅ MediaFire (scraping تلقائي)",
        "✅ روابط مباشرة",
        "✅ Telegram (حتى 20MB)",
    ])
    bot.send_message(message.chat.id,
        f"⚡️ *AKRO EKO TURBO v3*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 *المواقع المدعومة:*\n{caps}\n\n"
        "📤 *طرق الإرسال:*\n"
        "1️⃣ ملف `.img` مباشر (حتى 20MB)\n"
        "2️⃣ `/url <رابط>` من أي موقع\n"
        "3️⃣ أرسل الرابط كنص عادي\n\n"
        "💡 *أمثلة:*\n"
        "`/url https://www.mediafire.com/file/XXX`\n"
        "`/url https://drive.google.com/file/d/XXX`\n"
        "`/url https://mega.nz/file/XXX`\n"
        "`/url https://gofile.io/d/XXX`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 بواسطة: *AKRO EKO TURBO*",
        parse_mode='Markdown')


@bot.message_handler(commands=['url'])
def cmd_url(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().startswith('http'):
        bot.reply_to(message, "📌 الاستخدام:\n`/url https://رابط-الريكفري`",
                     parse_mode='Markdown')
        return
    url    = parts[1].strip()
    source = detect_source(url)
    labels = {'gdrive':'☁️ Google Drive','mega':'☁️ Mega.nz',
              'mediafire':'📁 MediaFire','direct':'🔗 مباشر','ytdlp':'🌐 yt-dlp'}
    bot.reply_to(message,
        f"🔍 المصدر: *{labels[source]}*\n⏳ جارٍ المعالجة...",
        parse_mode='Markdown')
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()


@bot.message_handler(content_types=['document'])
def handle_file(message):
    doc = message.document
    if not doc.file_name.endswith('.img'):
        bot.reply_to(message, "⚠️ أرسل ملفاً ينتهي بـ `.img` فقط.")
        return
    if doc.file_size > TELEGRAM_LIMIT:
        mb = doc.file_size / 1024 / 1024
        bot.reply_to(message,
            f"⚠️ الملف *{mb:.1f}MB* — يتجاوز حد تيليجرام (20MB).\n\n"
            "📌 ارفعه على أحد هذه المواقع وأرسل الرابط:\n"
            "• gofile.io\n• drive.google.com\n• pixeldrain.com\n• mega.nz",
            parse_mode='Markdown')
        return
    mb = doc.file_size / 1024 / 1024
    bot.reply_to(message, f"📥 *{doc.file_name}* ({mb:.1f}MB)\n⏳ جارٍ المعالجة...",
                 parse_mode='Markdown')
    try:
        info = bot.get_file(doc.file_id)
        url  = f"https://api.telegram.org/file/bot{TOKEN}/{info.file_path}"
        threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()
    except Exception as e:
        bot.reply_to(message, f"❌ فشل: `{e}`", parse_mode='Markdown')


@bot.message_handler(func=lambda m: m.text and re.search(r'https?://\S+', m.text))
def handle_raw_url(message):
    match = re.search(r'(https?://\S+)', message.text)
    if not match:
        return
    url    = match.group(1)
    source = detect_source(url)
    labels = {'gdrive':'☁️ Google Drive','mega':'☁️ Mega.nz',
              'mediafire':'📁 MediaFire','direct':'🔗 مباشر','ytdlp':'🌐 yt-dlp'}
    bot.reply_to(message,
        f"🔍 اكتشفت رابطاً ({labels[source]})\n⏳ جارٍ المعالجة...",
        parse_mode='Markdown')
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
print("⚡️ AKRO EKO TURBO v3.0 يعمل...")
print(f"   yt-dlp      : {'✅' if YTDLP_OK else '❌'}")
print(f"   gdown       : {'✅' if GDOWN_OK else '❌'}")
print(f"   mega.py     : {'✅' if MEGA_OK  else '❌'}")
print(f"   MediaFire   : ✅ (scraping)")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
