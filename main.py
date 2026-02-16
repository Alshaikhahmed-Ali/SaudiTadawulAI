import os, requests, sys, time, re

# استيراد القاموس الذهبي المدقق
try: 
    from companies import tadawul_map
except ImportError: 
    tadawul_map = {}

# إعدادات الربط
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def get_stock_details(raw_line):
    """استخراج الرمز والاسم والسوق من القاموس الجديد"""
    match = re.search(r'(\d{4})', str(raw_line))
    if match:
        symbol = match.group(1)
        details = tadawul_map.get(symbol)
        if details:
            # نسحب الاسم ونوع السوق اللذين وضعتهما أنت في الإكسل
            return symbol, details['name'], details['market']
    return None, None, None

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try: 
        requests.post(url, data=payload, timeout=30)
    except: 
        pass

def run_saudi_analyzer():
    try:
        # 1. سحب البيانات من الفلتر
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        
        if not csv_text or len(csv_text) < 10: 
            return

        # 2. الفرز البرمجي بناءً على تصنيفات البروفيسور في الإكسل
        market_sections = {}
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]

        for line in lines:
            if len(line) > 5:
                symbol, name, market = get_stock_details(line)
                if symbol:
                    if market not in market_sections: market_sections[market] = []
                    # نرسل البيانات نظيفة تماماً لـ AI
                    market_sections[market].append(f"الشركة: {name} | الرمز: {symbol} | البيانات الفنية: {line}")

        # 3. تجهيز المدخلات للمحلل الذكي
        full_context = ""
        for m_name, stocks in market_sections.items():
            full_context += f"### {m_name} ###\n" + "\n".join(stocks) + "\n\n"

        # 4. صياغة التعليمات النهائية لـ AI
        prompt = f"""
        بصفتك خبير "قناص السوق السعودي"، حلل البيانات التالية:
        {full_context}

        التعليمات الصارمة:
        1. التزم بالأسماء العربية وتصنيفات الأسواق المذكورة في البيانات حرفياً.
        2. اختر فقط الفرص التي تظهر إشارات ارتداد أو اختراق إيجابية.
        3. يمنع منعاً باتاً ذكر أي سهم مستبعد أو سلبي في الرسالة.
        
        التنسيق المطلوب:
        🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅
        *تقرير الفرص اللحظية*

        ### [اسم السوق من البيانات]
        • [الاسم العربي] ([الرمز]) | [السعر] ريال
        📈 [تحليل فني موجز ومشوق] | 🎯 هدف: [الهدف] | 🛡️ وقف: [الوقف]
        ــــــــــــــــــــــــــــــــــــــــــــــــ
        
        🔴 ملاحظة هامة: القراءة فنية فقط، والقرار الاستثماري مسؤوليتك.
        ✦✦✦
        """

        # طلب التحليل من Gemini
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, 
            timeout=120
        )

        if g_res.status_code == 200:
            report = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            send_telegram(report)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
