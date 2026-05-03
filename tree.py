import os
import subprocess
import shutil
import telebot
import requests

# إعدادات البوت - التوكن الخاص بك
TOKEN = '8067365706:AAFCnoBEiKB8ghHrN1Zo1qO_rKoimzrmcoE'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['document'])
def handle_recovery(message):
    # التأكد إن الملف المرسل هو ملف ريكفري
    if message.document.file_name.endswith('.img'):
        file_size_mb = message.document.file_size / (1024 * 1024)
        bot.reply_to(message, f"⏳ حجم الملف {file_size_mb:.2f}MB\nجارٍ التحميل والمعالجة... انتظر ثواني.")
        
        # 1. إنشاء مجلدات العمل
        work_dir = f"work_{message.chat.id}"
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(f"{work_dir}/recovery", exist_ok=True)
        rec_path = f"{work_dir}/recovery/recovery.img"

        try:
            # 2. تحميل الملف بطريقة تتخطى مشاكل المكتبة العادية مع الملفات الكبيرة
            file_info = bot.get_file(message.document.file_id)
            download_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
            
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(rec_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 3. تشغيل twrpdtgen لتوليد الـ Tree
            output_path = f"{work_dir}/output"
            # تشغيل الأداة
            result = subprocess.run(['python3', '-m', 'twrpdtgen', rec_path, '-o', output_path], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"فشل توليد الشجرة: {result.stderr}")

            # 4. إضافة تعديلات AKRO (Patching)
            board_config = None
            for root, dirs, files in os.walk(output_path):
                if "BoardConfig.mk" in files:
                    board_config = os.path.join(root, "BoardConfig.mk")
                    break
            
            if board_config:
                with open(board_config, 'a', encoding='utf-8') as f:
                    f.write("\n# --- AKRO Custom Patches ---\n")
                    f.write("TW_VARIANT := AKRO-UNOFFICIAL\n")
                    f.write("TW_INCLUDE_CRYPTO := true\n")
                    f.write("TW_INCLUDE_CRYPTO_FBE := true\n")
                    f.write("TW_DEVICE_VERSION := AKRO_V1\n")

            # 5. ضغط المجلد الناتج
            zip_file_name = f"TWRP_Tree_{message.chat.id}"
            shutil.make_archive(zip_file_name, 'zip', output_path)
            full_zip_path = f"{zip_file_name}.zip"

            # 6. إرسال الملف النهائي
            if os.path.exists(full_zip_path):
                with open(full_zip_path, 'rb') as f:
                    bot.send_document(message.chat.id, f, caption="✅ تم توليد الـ Device Tree بنجاح!\nبواسطة: AKRO EKO TURBO")
            else:
                bot.reply_to(message, "❌ فشل إنشاء ملف الـ Zip.")

        except Exception as e:
            error_msg = str(e)
            if "file is too big" in error_msg or "400" in error_msg:
                bot.reply_to(message, "❌ فشل التحميل: الملف كبير جداً على قيود تيليجرام (20MB).\nحاول رفع ريكفري أصغر أو استخدام رابط خارجي.")
            else:
                bot.reply_to(message, f"❌ حدث خطأ: {error_msg}")
        
        finally:
            # 7. تنظيف الملفات المؤقتة
            shutil.rmtree(work_dir, ignore_errors=True)
            if 'full_zip_path' in locals() and os.path.exists(full_zip_path):
                os.remove(full_zip_path)
    else:
        bot.reply_to(message, "⚠️ يا زميلي ابعت ملف ينتهي بـ .img عشان أعرف أشتغل عليه.")

print("⚡️ بوت AKRO EKO TURBO يعمل الآن وجاهز لاستلام الريكفري...")
bot.infinity_polling()
