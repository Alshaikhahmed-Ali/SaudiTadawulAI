import os
import requests
import sys
import time

# --- الإعدادات ---
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        pass

def run_saudi_analyzer():
    try:
        print("📥 جاري سحب بيانات السوق السعودي...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(URL, headers=headers, timeout=30)
        raw_text = response.text.strip()
        
        if not raw_text or "No stocks found" in raw_text:
            send_telegram("🔔 **ماسح السوق السعودي**\n\nلم يتم العثور على فرص تطابق الفلتر الفني اليوم.")
            return

        print("🤖 جاري الاتصال بالمحلل المالي...")
        
        # استخدام الموديل المستقر
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
        
        prompt = f"""
        أنت محلل مالي خبير في سوق الأسهم السعودي (تداول). لديك البيانات الفنية الخام التالية:
        {raw_text}

        المطلوب:
        1. اختر أفضل 3 أسهم واعدة فنياً لليوم.
        2. اكتب تقريراً احترافياً مختصراً باللهجة المالية السعودية.
        3. التزم تماماً بالقالب التالي:

        🇸🇦 **تقرير تداول الذكي اليومي** 🇸🇦

        🚀 **[اسم السهم] (الرمز)** - السعر: [السعر الحالي] ريال
        📊 **النظرة الفنية:** [جملة واحدة قوية]
        🎯 **الخطة المقترحة:**
        • الدخول: [منطقة السعر]
        • الهدف: [سعر مستهدف]
        • الوقف: [سعر الوقف]
        
        ---
        ⚠️ *إخلاء مسؤولية: هذا تحليل فني آلي وليس دعوة ملزمة.*
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        headers_gemini = {'Content-Type': 'application/json'}
        g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=30)
        
        # معالجة ضغط الطلبات
        if g_res.status_code == 429:
            time.sleep(20)
            g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=30)

        if g_res.status_code != 200:
            error_msg = g_res.text
            print(f"❌ Gemini Error: {error_msg}")
            send_telegram(f"⚠️ **خطأ تقني:**\n`{error_msg[:200]}`")
            sys.exit(1)

        analysis = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        
        send_telegram(analysis)
        print("✅ تم إرسال التقرير السعودي بنجاح!")

    except Exception as e:
        print(f"💥 خطأ غير متوقع: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
