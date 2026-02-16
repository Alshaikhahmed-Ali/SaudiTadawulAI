import os, requests, sys, time, csv, io, re

# استيراد قاعدة البيانات الشاملة (392 شركة)
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

# الإعدادات
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def get_market_info(raw_text):
    """استخراج الرمز والاسم وتحديد نوع السوق بدقة"""
    match = re.search(r'(\d{4})', str(raw_text))
    if match:
        symbol = match.group(1)
        name = tadawul_map.get(symbol, f"شركة رمز {symbol}")
        
        # منطق التصنيف بناءً على الرمز
        if symbol.startswith("9") and not symbol.startswith("9300"):
            market_type = "🚀 السوق الموازي (نمو)"
        elif symbol.startswith("433") or symbol.startswith("434") or symbol.startswith("470") or symbol == "9300":
            market_type = "🏗️ صناديق الريت"
        else:
            market_type = "🏢 السوق الرئيسي"
        return symbol, name, market_type
    return None, None, None

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: requests.post(url, data=payload, timeout=30)
    except: pass

def run_saudi_analyzer():
    try:
        print("📥 جاري سحب بيانات السوق...")
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        
        if not csv_text or len(csv_text) < 10: 
            send_telegram("🦅 **قناص السوق السعودي:**\nلا توجد فرص تطابق الفلتر حالياً.")
            return

        # فرز وتصنيف الأسهم برمجياً
        buckets = {}
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]

        for line in lines:
            if len(line) > 5:
                symbol, name, market = get_market_info(line)
                if symbol:
                    if market not in buckets: buckets[market] = []
                    buckets[market].append(f"{name} ({symbol}) | البيانات الخام: {line}")

        # بناء كتلة البيانات للذكاء الاصطناعي
        final_input = ""
        for market_name, items in buckets.items():
            final_input += f"--- {market_name} ---\n" + "\n".join(items) + "\n\n"

        print("🤖 جاري التحليل وصياغة التقرير الإيجابي...")
        
        prompt = f"""
        بصفتك "قناص السوق السعودي"، حلل البيانات الفنية التالية:
        {final_input}

        التعليمات الصارمة:
        1. اعرض فقط الفرص التي تحمل مؤشرات "إيجابية" أو "ارتداد".
        2. التزم بالعناوين: (السوق الرئيسي، السوق الموازي (نمو)، صناديق الريت).
        3. يمنع ذكر أي أسهم تم استبعادها أو تحمل إشارات سلبية.
        4. التنسيق الجمالي:
        🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅
        *تقرير الفرص اللحظية المحدث*

        ### [اسم السوق]
        • [الاسم العربي] ([الرمز]) | [السعر] ريال
        📈 [تحليل إيجابي مختصر جداً] | 🎯 هدف: [الهدف] | 🛡️ وقف: [الوقف]
        ــــــــــــــــــــــــــــــــــــــــــــــــ

        🔴 ملاحظة هامة: هذه الرسالة ليست توصية بيع أو شراء وإنما قراءة فنية لمؤشرات السوق، والقرار النهائي بيد المستثمر.
        ✦✦✦
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'},
            timeout=120
        )

        if g_res.status_code == 200:
            analysis = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            send_telegram(analysis)
            print("✅ تم الإرسال بنجاح!")
        else:
            print(f"❌ خطأ من Gemini: {g_res.status_code}")

    except Exception as e:
        print(f"💥 خطأ فادح: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
