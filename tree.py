import os
import subprocess
import shutil
import telebot

# إعدادات البوت - تم تحديث التوكن
TOKEN = '8067365706:AAFCnoBEiKB8ghHrN1Zo1qO_rKoimzrmcoE'
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['document'])
def handle_recovery(message):
    # التأكد إن الملف المرسل هو ملف ريكفري
    if message.document.file_name.endswith('.img'):
        sent_msg = bot.reply_to(message, "⏳ جارٍ تحميل ملف الريكفري ومعالجته... استنى شوية يا بطل.")
        
        # 1. إنشاء مجلدات العمل
        work_dir = f"work_{message.chat.id}"
        os.makedirs(work_dir, exist_ok=True)
        os.makedirs(f"{work_dir}/recovery", exist_ok=True)
        
        # 2. تحميل الملف من تيليجرام
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        rec_path = f"{work_dir}/recovery/recovery.img"
        
        with open(rec_path, 'wb') as f:
            f.write(downloaded_file)

        try:
            # 3. تشغيل twrpdtgen لتوليد الـ Tree
            output_path = f"{work_dir}/output"
            # تم إضافة --target عشان لو الجهاز قديم شوية يشتغل
            subprocess.run(['python3', '-m', 'twrpdtgen', rec_path, '-o', output_path], check=True)

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

            # 6. إرسال الملف النهائي
            with open(f"{zip_file_name}.zip", 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ تم توليد الـ Device Tree بنجاح! \nبواسطة: AKRO EKO TURBO")

        except Exception as e:
            bot.reply_to(message, f"❌ حصلت مشكلة أثناء المعالجة: {str(e)}")
        
        finally:
            # 7. تنظيف الملفات المؤقتة
            shutil.rmtree(work_dir, ignore_errors=True)
            if os.path.exists(f"{zip_file_name}.zip"):
                os.remove(f"{zip_file_name}.zip")
    else:
        bot.reply_to(message, "⚠️ يا زميلي ابعت ملف ينتهي بـ .img عشان أعرف أشتغل عليه.")

print("⚡️ بوت تحويل الريكفري شغال الآن (AKRO EKO TURBO)...")
bot.infinity_polling()
