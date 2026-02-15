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
        requests.post(url, data=payload, timeout=30)
    except:
        pass

def run_saudi_analyzer():
    try:
        print("📥 جاري سحب بيانات السوق السعودي...")
        response = requests.get(URL, timeout=60)
        
        if response.status_code != 200:
            send_telegram(f"⚠️ خطأ في المصدر: {response.status_code}")
            return

        csv_data = response.text.strip()

        if not csv_data or len(csv_data) < 10: 
            send_telegram("🔔 **قناص السوق السعودي:**\nلا توجد أسهم تطابق الفلتر حالياً.")
            return

        print("🤖 جاري التحليل مع إضافة إخلاء المسؤولية...")
        
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
        
        prompt = f"""
        أنت خبير فني في سوق الأسهم السعودي (تداول).
        البيانات (CSV):
        ```csv
        {csv_data}
        ```

        التعليمات:
        1. **الأسماء:** استخدم الرمز (Code) لمعرفة الاسم العربي للشركة.
        2. **الاختيار:** اختر أفضل 5 فرص إيجابية.
        3. **التحذير:** اختر سهماً سلبياً للملاحظة (إن وجد).
        4. **التنسيق:** التزم بهذا القالب نصياً وأضف التنبيه الأحمر في النهاية:

        تقرير "قناص السوق السعودي" يُحدد 5 أسهم ذات إمكانات ارتدادية وصاعدة مدعومة بتحليل عدة مؤشرات فنية.

        • سهم [الاسم العربي] ([الرمز]) عند [السعر] ريال، [السبب الفني]، الهدف [هدف] والوقف [وقف].

        • سهم [الاسم العربي] ([الرمز]) عند [السعر] ريال، [السبب الفني]، الهدف [هدف] والوقف [وقف].

        • سهم [الاسم العربي] ([الرمز]) عند [السعر] ريال، [السبب الفني]، الهدف [هدف] والوقف [وقف].

        • سهم [الاسم العربي] ([الرمز]) عند [السعر] ريال، [السبب الفني]، الهدف [هدف] والوقف [وقف].

        • سهم [الاسم العربي] ([الرمز]) عند [السعر] ريال، [السبب الفني]، الهدف [هدف] والوقف [وقف].

        ملاحظة: تم استبعاد سهم [الاسم] ([الرمز]) بسبب [السبب].

        🔴 **ملاحظة هامة:** هذه الرسالة ليست توصية بيع أو شراء وإنما قراءة فنية لمؤشرات السوق، والقرار النهائي بيد المستثمر إخلاءً للمسؤولية.
        ✦
        ✦
        ✦
        """

        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        headers_gemini = {'Content-Type': 'application/json'}
        
        # مهلة 120 ثانية لضمان عدم انقطاع الاتصال
        g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=120)
        
        if g_res.status_code == 429 or g_res.status_code == 500:
            time.sleep(10)
            g_res = requests.post(gemini_endpoint, json=payload, headers=headers_gemini, timeout=120)

        if g_res.status_code != 200:
            sys.exit(1)

        analysis = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        send_telegram(analysis)
        print("✅ تم الإرسال مع التنبيه القانوني!")

    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
