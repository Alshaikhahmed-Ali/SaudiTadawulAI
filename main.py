import os
import requests

# الإعدادات
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)

def debug_fetch():
    try:
        print("📥 جاري سحب البيانات للكشف...")
        # محاولة محاكاة متصفح حقيقي لتجاوز الحجب البسيط
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(URL, headers=headers, timeout=30)
        content = response.text
        
        # إرسال أول 500 حرف فقط لنرى ما هي الصفحة
        preview = content[:500]
        
        msg = f"🔍 **تقرير كشف الأخطاء:**\n\nحالة الاتصال: {response.status_code}\n\n**ما يراه البوت (أول 500 حرف):**\n`{preview}`"
        
        send_telegram(msg)
        print("✅ تم إرسال تقرير الكشف.")

    except Exception as e:
        send_telegram(f"💥 خطأ فادح: {str(e)}")

if __name__ == "__main__":
    debug_fetch()
