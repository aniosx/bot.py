#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import threading
from flask import Flask
from dotenv import load_dotenv
from telegram import Update, ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحميل متغيرات البيئة
load_dotenv()

# إعداد البوت
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("رمز TELEGRAM_TOKEN غير موجود في متغيرات البيئة.")

OWNER_ID = os.getenv('OWNER_ID')
if not OWNER_ID or not OWNER_ID.isdigit():
    raise ValueError("OWNER_ID غير موجود أو غير صالح في متغيرات البيئة.")
OWNER_ID = int(OWNER_ID)

PORT = int(os.environ.get('PORT', 8080))

# قاموس لتخزين الرسائل ومرسليها
message_registry = {}

# قائمة المستخدمين المحظورين (في الذاكرة)
blocked_users = set()

# ملف لتخزين المستخدمين المحظورين
BLOCKED_USERS_FILE = 'blocked_users.json'

# إنشاء تطبيق Flask للتأكد من التشغيل
app = Flask(__name__)

@app.route('/')
def index():
    return 'البوت يعمل!'

def load_blocked_users():
    """تحميل قائمة المستخدمين المحظورين من الملف."""
    global blocked_users
    try:
        if os.path.exists(BLOCKED_USERS_FILE):
            with open(BLOCKED_USERS_FILE, 'r') as f:
                blocked_list = json.load(f)
                blocked_users = set(blocked_list)
                logger.info(f"تم تحميل {len(blocked_users)} مستخدمين محظورين من الملف")
    except Exception as e:
        logger.error(f"خطأ أثناء تحميل المستخدمين المحظورين: {e}")

def save_blocked_users():
    """حفظ قائمة المستخدمين المحظورين في الملف."""
    try:
        with open(BLOCKED_USERS_FILE, 'w') as f:
            json.dump(list(blocked_users), f)
            logger.info(f"تم حفظ {len(blocked_users)} مستخدمين محظورين في الملف")
    except Exception as e:
        logger.error(f"خطأ أثناء حفظ المستخدمين المحظورين: {e}")

def start(update: Update, context: CallbackContext) -> None:
    """معالج أمر /start."""
    user = update.effective_user
    
    if user.id in blocked_users and user.id != OWNER_ID:
        update.message.reply_text("تم حظرك ولا يمكنك استخدام هذا البوت.")
        return
    
    update.message.reply_text(
        f'مرحبًا {user.first_name}! '
        f'أرسل لي رسالة وسيتم إرسالها إلى صاحب البوت.'
    )
    
    if user.id != OWNER_ID:
        # إرسال اسم المستخدم الأول والأخير ورابط حسابه فقط
        full_name = f"{user.first_name} {user.last_name or ''}".strip()
        username = f"@{user.username}" if user.username else full_name
        user_link = f"<a href='tg://user?id={user.id}'>{username}</a>"
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"مستخدم جديد: {user_link} بدأ استخدام البوت.",
            parse_mode=ParseMode.HTML
        )

def help_command(update: Update, context: CallbackContext) -> None:
    """معالج أمر /help."""
    user = update.effective_user
    
    if user.id in blocked_users and user.id != OWNER_ID:
        update.message.reply_text("تم حظرك ولا يمكنك استخدام هذا البوت.")
        return
    
    help_text = (
        'الأوامر المتاحة:\n'
        '/start - بدء تشغيل البوت\n'
        '/help - عرض هذه الرسالة\n\n'
        'لاستخدام البوت، أرسل رسالة وسيتم نقلها إلى صاحب البوت.'
    )
    
    if user.id == OWNER_ID:
        help_text += (
            '\n\nأوامر الإدارة (لصاحب البوت فقط):\n'
            '/block [user_id] - حظر مستخدم\n'
            '/unblock [user_id] - إلغاء حظر مستخدم\n'
            '/blocklist - عرض قائمة المستخدمين المحظورين'
        )
    
    update.message.reply_text(help_text)

def block_user(update: Update, context: CallbackContext) -> None:
    """معالج أمر /block لحظر مستخدم."""
    user = update.effective_user
    
    if user.id != OWNER_ID:
        update.message.reply_text("هذا الأمر مخصص لصاحب البوت فقط.")
        return
    
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "يرجى تحديد معرف المستخدم المراد حظره.\n"
            "مثال: /block 123456789"
        )
        return
    
    user_id = int(context.args[0])
    
    if user_id == OWNER_ID:
        update.message.reply_text("لا يمكنك حظر نفسك.")
        return
    
    blocked_users.add(user_id)
    save_blocked_users()
    
    update.message.reply_text(f"تم حظر المستخدم ذو المعرف {user_id}.")

def unblock_user(update: Update, context: CallbackContext) -> None:
    """معالج أمر /unblock لإلغاء حظر مستخدم."""
    user = update.effective_user
    
    if user.id != OWNER_ID:
        update.message.reply_text("هذا الأمر مخصص لصاحب البوت فقط.")
        return
    
    if not context.args or not context.args[0].isdigit():
        update.message.reply_text(
            "يرجى تحديد معرف المستخدم المراد إلغاء حظره.\n"
            "مثال: /unblock 123456789"
        )
        return
    
    user_id = int(context.args[0])
    
    if user_id in blocked_users:
        blocked_users.remove(user_id)
        save_blocked_users()
        update.message.reply_text(f"تم إلغاء حظر المستخدم ذو المعرف {user_id}.")
    else:
        update.message.reply_text(f"المستخدم ذو المعرف {user_id} غير محظور.")

def blocklist(update: Update, context: CallbackContext) -> None:
    """معالج أمر /blocklist لعرض قائمة المستخدمين المحظورين."""
    user = update.effective_user
    
    if user.id != OWNER_ID:
        update.message.reply_text("هذا الأمر مخصص لصاحب البوت فقط.")
        return
    
    if not blocked_users:
        update.message.reply_text("لا يوجد مستخدمين محظورين.")
        return
    
    blocklist_text = "قائمة المستخدمين المحظورين:\n"
    for blocked_id in blocked_users:
        blocklist_text += f"- المعرف: {blocked_id}\n"
    
    update.message.reply_text(blocklist_text)

def forward_message(update: Update, context: CallbackContext) -> None:
    """نقل الرسائل من المستخدمين إلى صاحب البوت."""
    user = update.effective_user
    message = update.message
    
    if user.id == OWNER_ID:
        return
    
    if user.id in blocked_users:
        update.message.reply_text("تم حظرك ولا يمكنك إرسال رسائل عبر هذا البوت.")
        return
    
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    username = f"@{user.username}" if user.username else full_name
    sender_info = f"<a href='tg://user?id={user.id}'>{username}</a>\n"
    
    reply_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("الرد", callback_data=f"reply_{user.id}_{message.message_id}"),
            InlineKeyboardButton("حظر", callback_data=f"block_{user.id}")
        ]
    ])
    
    if message.text:
        forwarded = context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}\n{message.text}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.photo:
        photo = message.photo[-1]
        caption = message.caption or ""
        forwarded = context.bot.send_photo(
            chat_id=OWNER_ID,
            photo=photo.file_id,
            caption=f"{sender_info}\n{caption}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.document:
        forwarded = context.bot.send_document(
            chat_id=OWNER_ID,
            document=message.document.file_id,
            caption=f"{sender_info}\n{message.document.file_name or ''}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.video:
        forwarded = context.bot.send_video(
            chat_id=OWNER_ID,
            video=message.video.file_id,
            caption=f"{sender_info}\n{message.caption or ''}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id" : user.id,
            "original_message_id": message.message_id
        }
    
    elif message.voice:
        forwarded = context.bot.send_voice(
            chat_id=OWNER_ID,
            voice=message.voice.file_id,
            caption=f"{sender_info}\nرسالة صوتية",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.audio:
        forwarded = context.bot.send_audio(
            chat_id=OWNER_ID,
            audio=message.audio.file_id,
            caption=f"{sender_info}\n{message.audio.title or ''}",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    elif message.sticker:
        forwarded = context.bot.send_sticker(
            chat_id=OWNER_ID,
            sticker=message.sticker.file_id
        )
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}\nتم إرسال ملصق",
            parse_mode=ParseMode.HTML,
            reply_to_message_id=forwarded.message_id,
            reply_markup=reply_keyboard
        )
        message_registry[f"{forwarded.message_id}"] = {
            "user_id": user.id,
            "original_message_id": message.message_id
        }
    
    else:
        update.message.reply_text("هذا النوع من الرسائل غير مدعوم حاليًا.")
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"{sender_info}\nرسالة من نوع غير مدعوم",
            parse_mode=ParseMode.HTML,
            reply_markup=reply_keyboard
        )
    
    update.message.reply_text("تم إرسال رسالتك.")

def handle_reply_button(update: Update, context: CallbackContext) -> None:
    """معالج النقر على الأزرار الداخلية."""
    query = update.callback_query
    query.answer()
    
    if query.from_user.id != OWNER_ID:
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=query.from_user.id,
            text="هذه الأزرار مخصصة لصاحب البوت فقط."
        )
        return
    
    data = query.data.split("_")
    
    if len(data) >= 3 and data[0] == "reply":
        user_id = int(data[1])
        context.user_data["waiting_for_reply"] = True
        context.user_data["reply_to"] = user_id
        context.user_data["original_message"] = query.message.message_id
        
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=OWNER_ID,
            text="أرسل ردك الآن"
        )
    
    elif len(data) >= 2 and data[0] == "block":
        user_id = int(data[1])
        
        if user_id == OWNER_ID:
            context.bot.send_message(
                chat_id=OWNER_ID,
                text="لا يمكنك حظر نفسك."
            )
            return
        
        blocked_users.add(user_id)
        save_blocked_users()
        
        query.edit_message_reply_markup(None)
        context.bot.send_message(
            chat_id=OWNER_ID,
            text=f"تم حظر المستخدم ذو المعرف {user_id}."
        )

def handle_owner_reply(update: Update, context: CallbackContext) -> None:
    """معالج ردود صاحب البوت."""
    user = update.effective_user
    message = update.message
    
    if user.id != OWNER_ID:
        return
    
    if context.user_data.get("waiting_for_reply") and "reply_to" in context.user_data:
        target_user_id = context.user_data["reply_to"]
        
        if target_user_id in blocked_users:
            context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"هذا المستخدم (المعرف: {target_user_id}) محظور. قم بإلغاء الحظر باستخدام /unblock {target_user_id} لإرسال رسائل إليه."
            )
            # إزالة حالة الانتظار
            context.user_data.pop("waiting_for_reply", None)
            context.user_data.pop("reply_to", None)
            context.user_data.pop("original_message", None)
            return
        
        try:
            if message.text:
                context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"رد من صاحب البوت: {message.text}"
                )
            elif message.photo:
                photo = message.photo[-1]
                caption = message.caption or ""
                context.bot.send_photo(
                    chat_id=target_user_id,
                    photo=photo.file_id,
                    caption=f"رد من صاحب البوت: {caption}"
                )
            elif message.document:
                context.bot.send_document(
                    chat_id=target_user_id,
                    document=message.document.file_id,
                    caption=f"رد من صاحب البوت: {message.caption or ''}"
                )
            elif message.video:
                context.bot.send_video(
                    chat_id=target_user_id,
                    video=message.video.file_id,
                    caption=f"رد من صاحب البوت: {message.caption or ''}"
                )
            elif message.voice:
                context.bot.send_voice(
                    chat_id=target_user_id,
                    voice=message.voice.file_id,
                    caption="رد صوتي من صاحب البوت"
                )
            elif message.audio:
                context.bot.send_audio(
                    chat_id=target_user_id,
                    audio=message.audio.file_id,
                    caption=f"رد صوتي من صاحب البوت: {message.caption or ''}"
                )
            elif message.sticker:
                context.bot.send_sticker(
                    chat_id=target_user_id,
                    sticker=message.sticker.file_id
                )
            else:
                context.bot.send_message(
                    chat_id=target_user_id,
                    text="رد صاحب البوت بنوع رسالة غير مدعوم."
                )
            
            context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"تم إرسال ردك إلى المستخدم ذو المعرف: {target_user_id}"
            )
            
            # إزالة حالة الانتظار
            context.user_data.pop("waiting_for_reply", None)
            context.user_data.pop("reply_to", None)
            context.user_data.pop("original_message", None)
        
        except Exception as e:
            context.bot.send_message(
                chat_id=OWNER_ID,
                text=f"خطأ أثناء إرسال الرد: {str(e)}"
            )
            # إزالة حالة الانتظار في حالة الخطأ
            context.user_data.pop("waiting_for_reply", None)
            context.user_data.pop("reply_to", None)
            context.user_data.pop("original_message", None)

def error_handler(update: Update, context: CallbackContext) -> None:
    """معالجة الأخطاء التي تحدث أثناء معالجة التحديثات."""
    logger.exception("حدث خطأ أثناء معالجة التحديث.", exc_info=context.error)
    if update and update.effective_chat:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="حدث خطأ. يرجى المحاولة لاحقًا."
        )

def run_flask():
    """تشغيل تطبيق Flask للتأكد من التشغيل."""
    app.run(host='0.0.0.0', port=PORT)

def main() -> None:
    """الدالة الرئيسية لتشغيل البوت."""
    load_blocked_users()
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("block", block_user))
    dispatcher.add_handler(CommandHandler("unblock", unblock_user))
    dispatcher.add_handler(CommandHandler("blocklist", blocklist))
    dispatcher.add_handler(CallbackQueryHandler(handle_reply_button))
    dispatcher.add_handler(MessageHandler(
        Filters.user(OWNER_ID) & (Filters.text | Filters.photo | Filters.document | Filters.video | Filters.voice | Filters.audio | Filters.sticker),
        handle_owner_reply
    ))
    dispatcher.add_handler(MessageHandler(
        Filters.text | Filters.photo | Filters.document | Filters.video |
        Filters.voice | Filters.audio | Filters.sticker,
        forward_message
    ))
    dispatcher.add_error_handler(error_handler)
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    updater.start_polling()
    logger.info("تم تشغيل البوت. اضغط Ctrl+C للإيقاف.")
    updater.idle()

if __name__ == '__main__':
    main()
