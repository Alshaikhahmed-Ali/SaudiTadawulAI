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
        response = requests.get(URL, timeout=30)
        
        if response.status_code != 200:
            send_telegram(f"⚠️ خطأ في المصدر: {response.status_code}")
            return

        csv_data = response.text.strip()

        if not csv_data or len(csv_data) < 10: 
            send_telegram("🔔 **قناص السوق السعودي:**\nلا توجد أسهم تطابق الفلتر حالياً.")
            return

        print("🤖 جاري التحليل وصياغة التقرير للجمهور...")
        
        gemini_endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}"
        
        # --- التعديل الجوهري في البرومبت ---
        prompt = f"""
        أنت "قناص السوق السعودي"، محلل فني آلي يخاطب جمهور قناة تليجرام عامة.
        لديك بيانات فنية لأسهم (CSV):
        ```csv
        {csv_data}
        ```

        المطلوب منك بدقة:
        1. اختر أفضل 5 أسهم فنية (إيجابية) من القائمة.
        2. اختر سهماً واحداً "سلبياً" أو "متضخماً" (RSI فوق 70 أو 80) لتضعه في الملاحظة كتحذير (إذا وجد).
        3. صغ الرسالة لتكون موجهة للجمهور مباشرة بأسلوب مهني وموجز.
        4. التزم بهذا القالب نصياً (لا تغير الهيكل):

        تقرير "قناص السوق السعودي" يُحدد 5 أسهم ذات إمكانات ارتدادية وصاعدة مدعومة بتحليل عدة مؤشرات فنية.

        • سهم [اسم السهم 1] ([الرمز]) عند [السعر] ريال، [سبب فني قصير جداً مثل: تقاطع إيجابي/ارتداد]، الهدف [هدف] والوقف [وقف].

        • سهم [اسم السهم 2] ([الرمز]) عند [السعر] ريال، [سبب فني قصير]، الهدف [هدف] والوقف [وقف].

        • سهم [اسم السهم 3] ([الرمز]) عند [السعر] ريال، [سبب فني قصير]، الهدف [هدف] والوقف [وقف].

        • سهم [اسم السهم 4] ([الرمز]) عند [السعر] ريال، [سبب فني قصير]، الهدف [هدف] والوقف [وقف].

        • سهم [اسم السهم 5] ([الرمز]) عند [السعر] ريال، [سبب فني قصير]، الهدف [هدف] والوقف [وقف].

        ملاحظة: تم استبعاد سهم [اسم سهم سلبي إن وجد] بسبب [السبب مثل: تشبع شرائي/RSI متضخم].

        تنبيه: قرارات الشراء والبيع مسؤولية المُستثمر.
        ✦
        ✦
        ✦
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
        print("✅ تم إرسال التقرير بتنسيق القناة!")

    except Exception as e:
        print(f"💥 Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
