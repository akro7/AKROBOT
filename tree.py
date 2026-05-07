"""
╔══════════════════════════════════════════════╗
║     AKRO EKO TURBO - TWRP Bot v3.0          ║
║     مع إصلاح الكودنايم + MediaFire          ║
╚══════════════════════════════════════════════╝

pip install pyTelegramBotAPI requests yt-dlp gdown beautifulsoup4 lxml twrpdtgen
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
TOKEN          = '8067365706:AAFCnoBEiKB8ghHrN1Zo1qO_rKoimzrmcoE'
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
    if not os.path.exists(path):
        return "الملف غير موجود بعد التحميل."

    size = os.path.getsize(path)
    if size == 0:
        return "الملف فارغ (0 bytes) — الرابط لا يُنزِّل ملفاً حقيقياً."

    if size < MIN_IMG_SIZE:
        return (f"الملف صغير جداً ({size/1024:.1f} KB) — "
                f"على الأرجح صفحة HTML وليس ريكفري حقيقي.")

    with open(path, 'rb') as f:
        header = f.read(512)
    text_start = header[:20].lower()
    if b'<!doctype' in text_start or b'<html' in text_start:
        return ("الرابط أعاد صفحة HTML بدل الملف.\n"
                "تأكد أن الرابط رابط تحميل مباشر وليس صفحة موقع.")

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  🌐 MediaFire Scraper
# ══════════════════════════════════════════════════════════════════════════════
def resolve_mediafire(url: str) -> str:
    if re.search(r'download\d+\.mediafire\.com', url):
        return url

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"فشل فتح صفحة MediaFire: {e}")

    soup = BeautifulSoup(resp.text, 'lxml')
    btn = soup.find('a', {'id': 'downloadButton'})
    if btn and btn.get('href'):
        return btn['href']

    match = re.search(r'(https://download\d+\.mediafire\.com/[^\s"\'<>]+)', resp.text)
    if match:
        return match.group(1)

    raise RuntimeError(
        "لم أتمكن من استخراج رابط التحميل من MediaFire.\n"
        "تأكد أن الرابط عام وغير محمي بكلمة مرور."
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
    return filename


def smart_download(url: str, work_dir: str, progress_cb=None) -> str:
    source   = detect_source(url)
    rec_dir  = os.path.join(work_dir, 'recovery')
    os.makedirs(rec_dir, exist_ok=True)
    dest     = os.path.join(rec_dir, 'recovery.img')

    if source == 'gdrive':
        progress_cb and progress_cb("☁️ Google Drive — جارٍ التحميل...")
        download_gdrive(url, dest)
    elif source == 'mega':
        progress_cb and progress_cb("☁️ Mega.nz — جارٍ التحميل...")
        dl = download_mega(url, rec_dir)
        if dl != dest and os.path.exists(dl): shutil.move(dl, dest)
    elif source == 'mediafire':
        progress_cb and progress_cb("🔍 MediaFire — جارٍ استخراج الرابط...")
        real_url = resolve_mediafire(url)
        download_direct(real_url, dest, progress_cb)
    elif source == 'direct':
        progress_cb and progress_cb("🔗 رابط مباشر — جارٍ التحميل...")
        try:
            download_direct(url, dest, progress_cb)
            err = validate_file(dest)
            if err:
                if os.path.exists(dest): os.remove(dest)
                dl = download_ytdlp(url, rec_dir, progress_cb)
                if dl != dest and os.path.exists(dl): shutil.move(dl, dest)
        except Exception:
            dl = download_ytdlp(url, rec_dir, progress_cb)
            if dl != dest and os.path.exists(dl): shutil.move(dl, dest)
    else:
        progress_cb and progress_cb("🌐 yt-dlp — جارٍ التحميل...")
        dl = download_ytdlp(url, rec_dir, progress_cb)
        if dl != dest and os.path.exists(dl): shutil.move(dl, dest)

    err = validate_file(dest)
    if err: raise RuntimeError(f"⚠️ الملف غير صالح:\n{err}")
    return dest


# ══════════════════════════════════════════════════════════════════════════════
#  ⚙️ توليد Device Tree (مع إصلاح الـ Codename)
# ══════════════════════════════════════════════════════════════════════════════
def generate_tree(rec_path: str, output_path: str):
    """
    إصلاح SyntaxError عبر كتابة كود الحقن بطريقة السطر الواحد الصحيحة برمجياً
    """
    # الكود المحقون معدل ليعمل كـ One-liner بدون أخطاء Indentation
    patch_code = (
        "import sebaubuntu_libs.libandroid.device_info as d; "
        "orig = d.DeviceInfo.get_first_prop; "
        "def patched(self, props): "
        "try: return orig(self, props) "
        "except: "
        "for p in props: "
        "if p in self.props: return self.props[p] "
        "return 'akro_device'; "
        "d.DeviceInfo.get_first_prop = patched; "
        "from twrpdtgen.__main__ import main; main()"
    ).replace('\n', '') # التأكد من عدم وجود سطور زائدة

    # استخدام الصيغة الأكثر أماناً للحقن البرمجي
    full_cmd = [
        'python3', '-c', 
        "import sebaubuntu_libs.libandroid.device_info as d; "
        "orig = d.DeviceInfo.get_first_prop; "
        "d.DeviceInfo.get_first_prop = lambda self, props: next((self.props[p] for p in props if p in self.props), 'akro_device'); "
        "from twrpdtgen.__main__ import main; main()",
        rec_path, '-o', output_path
    ]

    result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=300)
    
    if result.returncode != 0:
        stderr = result.stderr
        if 'unpackimg' in stderr or 'aik' in stderr:
            raise RuntimeError("فشل فك تشفير الـ recovery.img (الملف تالف أو غير مدعوم).")
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
            if status_msg: bot.edit_message_text(text, chat_id, status_msg.message_id)
            else: status_msg = bot.send_message(chat_id, text)
        except Exception: pass

    try:
        os.makedirs(work_dir, exist_ok=True)
        output_path = os.path.join(work_dir, 'output')

        rec_path = smart_download(url, work_dir, progress_cb=progress)
        size_mb = os.path.getsize(rec_path) / 1024 / 1024
        progress(f"✅ تم التحميل ({size_mb:.1f} MB)\n⚙️ جارٍ توليد الـ Tree (تخطي الـ Codename)...")

        generate_tree(rec_path, output_path)
        apply_patches(output_path)

        progress("📦 جارٍ ضغط الملفات...")
        shutil.make_archive(zip_name, 'zip', output_path)
        
        zip_mb = os.path.getsize(zip_path) / 1024 / 1024
        with open(zip_path, 'rb') as f:
            bot.send_document(
                chat_id, f,
                caption=(f"✅ *TWRP Device Tree جاهز!*\n"
                         f"📦 الحجم: `{zip_mb:.2f} MB`\n"
                         f"🛠 تم إصلاح مشكلة الـ Codename و SyntaxError"),
                parse_mode='Markdown')

        if status_msg: bot.delete_message(chat_id, status_msg.message_id)

    except Exception as e:
        bot.send_message(chat_id, f"❌ *خطأ:*\n`{str(e)[:600]}`", parse_mode='Markdown')
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(zip_path): os.remove(zip_path)


# ══════════════════════════════════════════════════════════════════════════════
#  📨 معالجات Telegram
# ══════════════════════════════════════════════════════════════════════════════

@bot.message_handler(commands=['start', 'help'])
def cmd_start(message):
    bot.send_message(message.chat.id,
        "⚡️ *AKRO EKO TURBO v3*\n"
        "تم حل مشكلة الـ SyntaxError وتخطي الـ Codename.\n\n"
        "أرسل رابط الملف مباشرة أو استخدم `/url`.",
        parse_mode='Markdown')

@bot.message_handler(commands=['url'])
def cmd_url(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2: return
    url = parts[1].strip()
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()

@bot.message_handler(content_types=['document'])
def handle_file(message):
    doc = message.document
    if not doc.file_name.endswith('.img'): return
    if doc.file_size > TELEGRAM_LIMIT: return
    info = bot.get_file(doc.file_id)
    url  = f"https://api.telegram.org/file/bot{TOKEN}/{info.file_path}"
    threading.Thread(target=process_recovery, args=(message, url), daemon=True).start()

@bot.message_handler(func=lambda m: m.text and re.search(r'https?://\S+', m.text))
def handle_raw_url(message):
    match = re.search(r'(https?://\S+)', message.text)
    if match:
        threading.Thread(target=process_recovery, args=(message, match.group(1)), daemon=True).start()

print("⚡️ AKRO EKO TURBO v3.0 (Fixed Syntax) يعمل...")
bot.infinity_polling()
