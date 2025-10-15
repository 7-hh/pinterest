import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعدادات البوت
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
OWNER_ID = int(os.getenv('OWNER_ID', 'YOUR_OWNER_ID_HERE'))
CHANNEL_ID = os.getenv('CHANNEL_ID', '@h2tow')

# إعدادات Clarifai
CLARIFAI_API_KEY = os.getenv('CLARIFAI_API_KEY', 'YOUR_CLARIFAI_API_KEY_HERE')

# إعدادات Pinterest
PINTEREST_SEARCH_URL = "https://www.pinterest.com/resource/BaseSearchResource/get/"
PINTEREST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'X-Requested-With': 'XMLHttpRequest',
    'X-APP-VERSION': '1.0.0',
    'X-Pinterest-AppVersion': '1.0.0'
}

# رسائل البوت
MESSAGES = {
    'start': '''
🎨 مرحباً بك في بوت البحث عن الصور الذكي!

يمكنك:
📸 إرسال صورة للبحث عن صور مشابهة
💬 كتابة وصف للبحث عن صور تناسب الوصف

استخدم /start لبدء البحث
    ''',
    'not_subscribed': '''
❌ يجب عليك الاشتراك في القناة أولاً!

📢 قناة البوت: @h2tow
👤 مطور البوت: @J2J_2

بعد الاشتراك، اضغط /start مرة أخرى
    ''',
    'processing': '🔍 جاري البحث عن الصور المشابهة...',
    'no_results': '❌ لم يتم العثور على صور مشابهة',
    'error': '❌ حدث خطأ أثناء البحث، حاول مرة أخرى'
}
