import os, requests, sys, time, csv, io, re

# استيراد قاعدة البيانات الشاملة
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

# الإعدادات
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

def get_clean_data(raw_text):
    match = re.search(r'(\d{4})', str(raw_text))
    if match:
        symbol = match.group(1)
        name = tadawul_map.get(symbol, f"شركة ({symbol})")
        market_type = "main"
        if symbol.startswith("9"): market_type = "nomu"
        elif symbol.startswith("433") or symbol.startswith("434") or symbol.startswith("47"): market_type = "reit"
        return symbol, name, market_type
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
        if not csv_text or len(csv_text) < 10: 
            send_telegram("🦅 **قناص السوق السعودي:**\nلا توجد فرص تطابق الفلتر حالياً.")
            return

        # تجميع الأسهم حسب السوق
        markets = {"main": [], "nomu": [], "reit": []}
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]

        for line in lines:
            if len(line) > 5:
                symbol, name, m_type = get_clean_data(line)
                if symbol: markets[m_type].append(f"{name} ({symbol}) | البيانات: {line}")

        # بناء محتوى التحليل
        final_input = ""
        for k, v in markets.items():
            if v: final_input += f"--- {k.upper()} ---\n" + "\n".join(v) + "\n\n"

        prompt = f"""
        أنت قناص السوق السعودي، حلل البيانات التالية:
        {final_input}
        المطلوب: اختر أفضل الفرص الإيجابية فقط، صنفها تحت العناوين: (السوق الرئيسي، نمو، الريت).
        لا تذكر أي أسهم مستبعدة. استخدم الإيموجي المناسب. التزم بالتنسيق:
        🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅
        ### [اسم السوق]
        • [الاسم العربي] ([الرمز]) | [السعر] ريال
        📈 [التحليل] | 🎯 هدف: [الهدف] | 🛡️ وقف: [الوقف]
        🔴 ملاحظة هامة: هذه الرسالة ليست توصية بيع أو شراء وإنما قراءة فنية، والقرار النهائي بيد المستثمر.
        ✦✦✦
        """

        g_res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
                              json={"contents": [{"parts": [{"text": prompt}]}]}, headers={'Content-Type': 'application/json'}, timeout=120)

        analysis = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        send_telegram(analysis)
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    run_saudi_analyzer()
