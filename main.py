import os, requests, sys, time, re

# استيراد القاموس الذهبي المدقق (392 شركة)
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
    """استخراج الرمز والاسم والسوق من القاموس المدقق"""
    match = re.search(r'(\d{4})', str(raw_line))
    if match:
        symbol = match.group(1)
        details = tadawul_map.get(symbol)
        if details:
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
        # 1. سحب البيانات اللحظية من الفلتر
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
                    # نرسل الاسم العربي الصريح لضمان عدم التخمين
                    market_sections[market].append(f"الشركة: {name} | الرمز: {symbol} | البيانات الفنية: {line}")

        # 3. تجهيز السياق للذكاء الاصطناعي
        full_context = ""
        for m_name, stocks in market_sections.items():
            full_context += f"--- {m_name} ---\n" + "\n".join(stocks) + "\n\n"

        # 4. البرومبت الصارم لمنع التأليف وإضافة ترقيم الإيموجي
        prompt = f"""
        أنت محلل فني آلي "قناص السوق السعودي". 
        المصدر الوحيد للأسماء والحقائق هو البيانات التالية:
        {full_context}

        التعليمات الصارمة (ممنوع مخالفتها):
        1. استخدم الأسماء العربية المذكورة في البيانات حرفياً؛ يحظر تماماً تخمين أو اختراع أسماء من عندك.
        2. اعرض فقط الشركات التي تظهر مؤشرات إيجابية (قوة، ارتداد، اختراق).
        3. قم بترقيم الأسهم في كل قسم باستخدام أرقام الإيموجي (1️⃣، 2️⃣، 3️⃣، 4️⃣، 5️⃣...).
        4. يمنع ذكر أي شركة لم ترد في القائمة أعلاه أو أي شركة سلبية.

        التنسيق المطلوب للرسالة:
        🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅
        *تقرير الفرص اللحظية*

        ### [اسم القسم/السوق]
        [رقم الإيموجي] • [الاسم العربي من البيانات] ([الرمز]) | [السعر] ريال
        📈 [التحليل الفني الإيجابي] | 🎯 هدف: [الهدف] | 🛡️ وقف: [الوقف]
        ــــــــــــــــــــــــــــــــــــــــــــــــ
        
        🔴 ملاحظة هامة:هذ الرسالة ليست توصية بيع او شراء.فالقرار الاستثماري مسؤوليتك، والتقرير هذا قراءة فنية فقط.
        ✦✦✦
        """

        # طلب التحليل من جيميناي
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
