import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from clarifai.rest import ClarifaiApp
from clarifai.rest import Image as ClarifaiImage
from PIL import Image
import io
import json
import re

from config import *

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تهيئة Clarifai
clarifai_app = ClarifaiApp(api_key=CLARIFAI_API_KEY)

class PinterestSearcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(PINTEREST_HEADERS)
    
    async def search_pinterest(self, query, max_results=10):
        """البحث في Pinterest عن الصور"""
        try:
            # إعداد معاملات البحث
            params = {
                'source_url': f'/search/pins/?q={query}',
                'data': json.dumps({
                    'options': {
                        'query': query,
                        'scope': 'pins',
                        'no_pinterest_filter': False
                    },
                    'context': {}
                })
            }
            
            response = self.session.get(PINTEREST_SEARCH_URL, params=params)
            response.raise_for_status()
            
            data = response.json()
            pins = data.get('resource_response', {}).get('data', {}).get('results', [])
            
            results = []
            for pin in pins[:max_results]:
                if 'images' in pin and 'orig' in pin['images']:
                    image_url = pin['images']['orig']['url']
                    title = pin.get('title', '')
                    link = pin.get('link', '')
                    
                    results.append({
                        'image_url': image_url,
                        'title': title,
                        'link': link
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"خطأ في البحث في Pinterest: {e}")
            return []

class TelegramBot:
    def __init__(self):
        self.pinterest_searcher = PinterestSearcher()
    
    async def check_subscription(self, user_id):
        """التحقق من اشتراك المستخدم في القناة"""
        try:
            # يمكن إضافة منطق التحقق من الاشتراك هنا
            # للتبسيط، سنعتبر أن المستخدم مشترك
            return True
        except Exception as e:
            logger.error(f"خطأ في التحقق من الاشتراك: {e}")
            return False
    
    async def get_image_description(self, image_url):
        """الحصول على وصف الصورة باستخدام Clarifai"""
        try:
            # تحليل الصورة باستخدام Clarifai
            model = clarifai_app.models.get('general-image-recognition')
            response = model.predict_by_url(image_url)
            
            # استخراج المفاهيم (concepts) من الاستجابة
            concepts = response['outputs'][0]['data']['concepts']
            
            # أخذ أهم 5 مفاهيم
            top_concepts = sorted(concepts, key=lambda x: x['value'], reverse=True)[:5]
            
            # إنشاء وصف من المفاهيم
            description = ', '.join([concept['name'] for concept in top_concepts])
            
            return description
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الصورة: {e}")
            return None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user_id = update.effective_user.id
        
        # التحقق من الاشتراك
        if not await self.check_subscription(user_id):
            await update.message.reply_text(MESSAGES['not_subscribed'])
            return
        
        await update.message.reply_text(MESSAGES['start'])
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الصور المرسلة"""
        user_id = update.effective_user.id
        
        # التحقق من الاشتراك
        if not await self.check_subscription(user_id):
            await update.message.reply_text(MESSAGES['not_subscribed'])
            return
        
        # إرسال رسالة المعالجة
        processing_msg = await update.message.reply_text(MESSAGES['processing'])
        
        try:
            # الحصول على الصورة
            photo = update.message.photo[-1]  # أعلى دقة
            file = await context.bot.get_file(photo.file_id)
            
            # تحليل الصورة
            description = await self.get_image_description(file.file_path)
            
            if not description:
                await processing_msg.edit_text(MESSAGES['error'])
                return
            
            # البحث في Pinterest
            results = await self.pinterest_searcher.search_pinterest(description)
            
            if not results:
                await processing_msg.edit_text(MESSAGES['no_results'])
                return
            
            # إرسال النتائج
            await processing_msg.delete()
            
            # إرسال أول صورة مع الوصف
            first_result = results[0]
            caption = f"🔍 **نتائج البحث:**\n\n📝 **الوصف:** {description}\n\n📌 **العنوان:** {first_result['title']}"
            
            keyboard = []
            if first_result['link']:
                keyboard.append([InlineKeyboardButton("🔗 رابط الصورة", url=first_result['link'])])
            
            if len(results) > 1:
                keyboard.append([InlineKeyboardButton("📸 عرض المزيد", callback_data=f"more_{user_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await update.message.reply_photo(
                photo=first_result['image_url'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # حفظ النتائج للمستخدم
            context.user_data[f'results_{user_id}'] = results
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الصورة: {e}")
            await processing_msg.edit_text(MESSAGES['error'])
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج النصوص المرسلة"""
        user_id = update.effective_user.id
        
        # التحقق من الاشتراك
        if not await self.check_subscription(user_id):
            await update.message.reply_text(MESSAGES['not_subscribed'])
            return
        
        # إرسال رسالة المعالجة
        processing_msg = await update.message.reply_text(MESSAGES['processing'])
        
        try:
            # البحث في Pinterest باستخدام النص
            query = update.message.text
            results = await self.pinterest_searcher.search_pinterest(query)
            
            if not results:
                await processing_msg.edit_text(MESSAGES['no_results'])
                return
            
            # إرسال النتائج
            await processing_msg.delete()
            
            # إرسال أول صورة
            first_result = results[0]
            caption = f"🔍 **نتائج البحث:**\n\n📝 **الاستعلام:** {query}\n\n📌 **العنوان:** {first_result['title']}"
            
            keyboard = []
            if first_result['link']:
                keyboard.append([InlineKeyboardButton("🔗 رابط الصورة", url=first_result['link'])])
            
            if len(results) > 1:
                keyboard.append([InlineKeyboardButton("📸 عرض المزيد", callback_data=f"more_{user_id}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            
            await update.message.reply_photo(
                photo=first_result['image_url'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # حفظ النتائج للمستخدم
            context.user_data[f'results_{user_id}'] = results
            
        except Exception as e:
            logger.error(f"خطأ في معالجة النص: {e}")
            await processing_msg.edit_text(MESSAGES['error'])
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار التفاعلية"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        
        if query.data.startswith('more_'):
            # عرض المزيد من النتائج
            results = context.user_data.get(f'results_{user_id}', [])
            
            if len(results) > 1:
                # إرسال باقي النتائج
                for i, result in enumerate(results[1:6], 1):  # عرض 5 صور إضافية
                    caption = f"📸 **النتيجة {i+1}:**\n\n📌 **العنوان:** {result['title']}"
                    
                    keyboard = []
                    if result['link']:
                        keyboard.append([InlineKeyboardButton("🔗 رابط الصورة", url=result['link'])])
                    
                    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
                    
                    await query.message.reply_photo(
                        photo=result['image_url'],
                        caption=caption,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                
                await query.edit_message_text("✅ تم عرض جميع النتائج المتاحة")

def main():
    """تشغيل البوت"""
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إنشاء البوت
    bot = TelegramBot()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_text))
    
    # تشغيل البوت
    logger.info("بدء تشغيل البوت...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
