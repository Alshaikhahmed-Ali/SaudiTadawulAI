import os, requests, re

# استيراد القاموس الذهبي الموثق
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def run_saudi_analyzer():
    try:
        # 1. جلب البيانات اللحظية
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text: return

        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        # 2. تحضير البيانات واستخراج الأسعار الحالية برمجياً
        ai_input = ""
        stock_prices = {} # لحفظ السعر الحالي لكل رمز
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    # محاولة استخراج أول رقم عشري في السطر كـ "سعر حالي"
                    p_match = re.search(r'(\d+\.\d+)', line)
                    stock_prices[symbol] = p_match.group(1) if p_match else "---"
                    ai_input += f"ID:{symbol} Price:{stock_prices[symbol]} RawData:{line}\n"

        # 3. برومبت "الأرقام الصارمة"
        prompt = f"""
        Analyze these stocks. Return ONLY the top 5 positive ones.
        For each stock, calculate a target (+3%) and a stop loss (-2%) based on the Price provided.
        Format per line: SYMBOL|TARGET|STOP|ANALYSIS
        Strict Rules: NO NAMES. NO INTROS. USE NUMBERS FOR TARGET/STOP.
        Data:
        {ai_input}
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        final_list = []
        if g_res.status_code == 200:
            raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            final_list = [l for l in raw_output.strip().split('\n') if '|' in l]

        # بناء الرسالة النهائية
        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية بالأسعار والشارتات*\n\n"
        
        count = 0
        for row in final_list:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    chart_url = f"https://ar.tradingview.com/symbols/TADAWUL-{symbol}/"
                    current_p = stock_prices.get(symbol, "---")
                    
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • {info['name']} ({symbol}) | {current_p} ريال\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += f"🔗 [لمشاهدة الشارت اضغط هنا]({chart_url})\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة: القرار الاستثماري مسؤوليتك، والتقرير قراءة فنية فقط."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_web_page_preview": False})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
