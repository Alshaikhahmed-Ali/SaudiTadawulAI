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
        print("📥 جاري سحب بيانات CSV من MarketInOut...")
        response = requests.get(URL, timeout=30)
        
        if response.status_code != 200:
            send_telegram(f"⚠️ خطأ في المصدر: {response.status_code}")
            return

        csv_data = response.text.strip()

        # التحقق من أن البيانات ليست فارغة
        if not csv_data or len(csv_data) < 10: 
            send_telegram("🔔 **البوت السعودي:**\nلا توجد أسهم تطابق الفلتر حالياً.")
            return

        print("🤖 جاري إرسال ملف CSV إلى Gemini للتحليل...")
        
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
        
        # برومبت محسن للتعامل مع CSV
        prompt = f"""
        أنت محلل مالي خبير في السوق السعودي (تداول).
        لديك بيانات فنية بصيغة CSV (قيم مفصولة بفواصل) للأسهم التالية:
        
        ```csv
        {csv_data}
        ```

        المطلوب:
        1. اقرأ البيانات جيداً (السعر، التغير، السيولة، المؤشرات).
        2. اختر أفضل 3 فرص (أسهم) واعدة فنياً لليوم.
        3. اكتب تقريراً بلهجة سعودية مالية احترافية.
        4. التزم بهذا القالب:

        🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦

        📈 **[اسم الشركة] (الرمز)**
        • السعر: [السعر الحالي] ريال
        • التحليل: [سبب الاختيار الفني باختصار]
        • 🎯 الهدف: [هدف مضاربي قريب]
        • 🛡️ الوقف: [سعر الوقف]

        ---
        ⚠️ *تنبيه: قرار البيع والشراء مسؤوليتك.*
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        headers_gemini = {'Content-Type': 'application/json'}
        g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=30)
        
        if g_res.status_code == 429:
            time.sleep(20)
            g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=30)

        if g_res.status_code != 200:
            sys.exit(1)

        analysis = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        send_telegram(analysis)
        print("✅ تم الإرسال بنجاح!")

    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
