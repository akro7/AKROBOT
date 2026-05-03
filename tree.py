import os
import subprocess
import shutil
import telebot
import requests
import re

# ===== إعدادات البوت =====
TOKEN = '8067365706:AAFCnoBEiKB8ghHrN1Zo1qO_rKoimzrmcoE'
bot = telebot.TeleBot(TOKEN)

TELEGRAM_MAX_SIZE = 20 * 1024 * 1024  # 20MB بالبايت

# ===================================================
# /start - رسالة الترحيب وشرح الاستخدام
# ===================================================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    text = (
        "⚡️ *مرحباً في بوت AKRO EKO TURBO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔧 *وظيفة البوت:*\n"
        "توليد TWRP Device Tree من ملف recovery.img\n\n"
        "📤 *طريقة الاستخدام:*\n\n"
        "1️⃣ *إذا الملف أقل من 20MB:*\n"
        "   أرسل ملف `.img` مباشرةً\n\n"
        "2️⃣ *إذا الملف أكبر من 20MB:*\n"
        "   أرسل الرابط المباشر للملف هكذا:\n"
        "   `/url https://رابط-الملف-هنا`\n\n"
        "💡 *روابط مدعومة:*\n"
        "   • Google Drive (رابط مباشر)\n"
        "   • Telegram CDN\n"
        "   • أي رابط HTTP/HTTPS مباشر\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛠 بواسطة: *AKRO EKO TURBO*"
    )
    bot.send_message(message.chat.id, text, parse_mode='Markdown')


# ===================================================
# الدالة المركزية: معالجة ملف الريكفري
# ===================================================
def process_recovery(message, download_url, file_name="recovery.img"):
    work_dir = f"work_{message.chat.id}"
    os.makedirs(f"{work_dir}/recovery", exist_ok=True)
    rec_path = f"{work_dir}/recovery/recovery.img"
    output_path = f"{work_dir}/output"
    zip_file_name = f"TWRP_Tree_{message.chat.id}"
    full_zip_path = f"{zip_file_name}.zip"

    try:
        # ── تحميل الملف ──
        bot.send_message(message.chat.id, "⬇️ جارٍ تحميل الملف... انتظر.")
        with requests.get(download_url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(rec_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)

        downloaded_mb = os.path.getsize(rec_path) / (1024 * 1024)
        bot.send_message(message.chat.id, f"✅ تم التحميل ({downloaded_mb:.1f}MB)\n⚙️ جارٍ توليد الـ Device Tree...")

        # ── تشغيل twrpdtgen ──
        result = subprocess.run(
            ['python3', '-m', 'twrpdtgen', rec_path, '-o', output_path],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            raise Exception(f"فشل twrpdtgen:\n{result.stderr[-500:]}")

        # ── تطبيق AKRO Patches ──
        for root, dirs, files in os.walk(output_path):
            if "BoardConfig.mk" in files:
                board_config = os.path.join(root, "BoardConfig.mk")
                with open(board_config, 'a', encoding='utf-8') as f:
                    f.write("\n# --- AKRO Custom Patches ---\n")
                    f.write("TW_VARIANT := AKRO-UNOFFICIAL\n")
                    f.write("TW_INCLUDE_CRYPTO := true\n")
                    f.write("TW_INCLUDE_CRYPTO_FBE := true\n")
                    f.write("TW_DEVICE_VERSION := AKRO_V1\n")
                break

        # ── ضغط وإرسال الناتج ──
        shutil.make_archive(zip_file_name, 'zip', output_path)

        if not os.path.exists(full_zip_path):
            raise Exception("فشل إنشاء ملف الـ ZIP.")

        zip_size_mb = os.path.getsize(full_zip_path) / (1024 * 1024)
        with open(full_zip_path, 'rb') as f:
            bot.send_document(
                message.chat.id, f,
                caption=(
                    f"✅ *تم توليد الـ Device Tree بنجاح!*\n"
                    f"📦 حجم الـ Tree: `{zip_size_mb:.2f}MB`\n"
                    f"🛠 بواسطة: *AKRO EKO TURBO*"
                ),
                parse_mode='Markdown'
            )

    except requests.exceptions.ConnectionError:
        bot.reply_to(message, "❌ فشل الاتصال. تأكد أن الرابط صحيح ومتاح.")
    except requests.exceptions.Timeout:
        bot.reply_to(message, "❌ انتهت مهلة التحميل. الملف بطيء جداً أو الرابط منتهي.")
    except subprocess.TimeoutExpired:
        bot.reply_to(message, "❌ استغرق التوليد وقتاً طويلاً جداً. جرب ملف أصغر.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ:\n`{str(e)[:400]}`", parse_mode='Markdown')

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        if os.path.exists(full_zip_path):
            os.remove(full_zip_path)


# ===================================================
# معالج الملفات المرسلة مباشرةً (حتى 20MB)
# ===================================================
@bot.message_handler(content_types=['document'])
def handle_file(message):
    doc = message.document
    if not doc.file_name.endswith('.img'):
        bot.reply_to(message, "⚠️ أرسل ملفاً ينتهي بـ `.img` فقط.")
        return

    if doc.file_size > TELEGRAM_MAX_SIZE:
        size_mb = doc.file_size / (1024 * 1024)
        bot.reply_to(
            message,
            f"⚠️ *حجم الملف {size_mb:.1f}MB* — أكبر من حد تيليجرام (20MB).\n\n"
            f"📌 *الحل:* ارفع الملف على أي استضافة وأرسل الرابط:\n"
            f"`/url https://رابط-الملف.img`",
            parse_mode='Markdown'
        )
        return

    size_mb = doc.file_size / (1024 * 1024)
    bot.reply_to(message, f"📥 حجم الملف: {size_mb:.2f}MB\nجارٍ المعالجة...")

    try:
        file_info = bot.get_file(doc.file_id)
        download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        process_recovery(message, download_url, doc.file_name)
    except Exception as e:
        bot.reply_to(message, f"❌ فشل الحصول على رابط الملف:\n`{e}`", parse_mode='Markdown')


# ===================================================
# معالج الرابط المباشر /url - يحل مشكلة الـ 20MB
# ===================================================
@bot.message_handler(commands=['url'])
def handle_url(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(
            message,
            "📌 *الاستخدام الصحيح:*\n`/url https://رابط-الملف.img`",
            parse_mode='Markdown'
        )
        return

    url = parts[1].strip()

    # التحقق من صحة الرابط
    if not re.match(r'https?://', url):
        bot.reply_to(message, "❌ الرابط غير صحيح. يجب أن يبدأ بـ `http://` أو `https://`", parse_mode='Markdown')
        return

    bot.reply_to(message, f"🔗 تم استلام الرابط:\n`{url}`\nجارٍ البدء...", parse_mode='Markdown')
    process_recovery(message, url)


# ===================================================
# معالج أي رسالة نصية تحتوي على رابط مباشرة
# ===================================================
@bot.message_handler(func=lambda m: m.text and re.search(r'https?://\S+\.img', m.text))
def handle_direct_link(message):
    match = re.search(r'(https?://\S+\.img)', message.text)
    if match:
        url = match.group(1)
        bot.reply_to(message, f"🔗 اكتشفت رابط `.img` مباشر:\n`{url}`\nجارٍ المعالجة...", parse_mode='Markdown')
        process_recovery(message, url)


# ===================================================
# تشغيل البوت
# ===================================================
print("⚡️ بوت AKRO EKO TURBO يعمل الآن وجاهز لاستلام الريكفري...")
print("✅ يدعم: ملفات مباشرة (>20MB) + روابط خارجية (بدون حد)")
bot.infinity_polling()
