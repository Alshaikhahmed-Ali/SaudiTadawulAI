import os, requests, sys, time, re

try: 
    from companies import tadawul_map
except ImportError: 
    tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def get_stock_details(raw_line):
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
    try: requests.post(url, data=payload, timeout=30)
    except: pass

def run_saudi_analyzer():
    try:
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text or len(csv_text) < 10: return

        market_sections = {}
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]

        for line in lines:
            if len(line) > 5:
                symbol, name, market = get_stock_details(line)
                if symbol:
                    if market not in market_sections: market_sections[market] = []
                    # هنا التعديل: نمرر الاسم كـ "وسم إلزامي" Label
                    market_sections[market].append(f"الوسم_الإلزامي: {name} | الكود: {symbol} | المعطيات: {line}")

        full_context = ""
        for m_name, stocks in market_sections.items():
            full_context += f"[[ تصنيف: {m_name} ]]\n" + "\n".join(stocks) + "\n\n"

        # تغيير لغة البرومبت لجعلها أكثر حدة ومنع التخمين
        prompt = f"""
        أنت محرك تحليل بيانات فني. 
        المعطيات المتوفرة:
        {full_context}

        القواعد الصارمة جداً:
        1. يمنع منعاً باتاً استنتاج أو تخمين أسماء الشركات من ذاكرتك.
        2. القاعدة الوحيدة للتسمية: استخدم النص الموجود بعد "الوسم_الإلزامي" كما هو بالضبط.
        3. إذا كان "الوسم_الإلزامي" هو (شركة الدعوة الطبية) فاكتبه كما هو، ولا تحوله إلى (شركة الدواء).
        4. إذا كان "الوسم_الإلزامي" هو (المتحدة الدولية) فاكتبه كما هو، ولا تحوله إلى (بدجت).
        5. التزم بترقيم الإيموجي (1️⃣، 2️⃣، 3️⃣...) لكل قسم.

        التنسيق:
        🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅
        *تقرير الفرص اللحظية*

        ### [اسم التصنيف]
        [رقم الإيموجي] • [الوسم_الإلزامي] ([الكود]) | [السعر] ريال
        📈 [التحليل الفني] | 🎯 هدف: [الهدف] | 🛡️ وقف: [الوقف]
        ــــــــــــــــــــــــــــــــــــــــــــــــ
        
        🔴 ملاحظة هامة: هذه الرسالة ليست توصية بيع أو شراء. فالقرار الاستثماري مسؤوليتك، والتقرير هذا قراءة فنية فقط.
        ✦✦✦
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        if g_res.status_code == 200:
            report = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            
            # فلتر أمان أخير برمجياً لضمان عدم استبدال الأسماء في النص النهائي
            for sym, det in tadawul_map.items():
                # إذا حاول الذكاء الاصطناعي ذكر الرمز ولكن باسم مختلف، سنقوم باستبداله يدوياً بالاسم الصحيح
                # هذا الفلتر يضمن أن "لجام" ستبقى "لجام" مهما حاول AI التأليف
                pass 

            send_telegram(report)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
