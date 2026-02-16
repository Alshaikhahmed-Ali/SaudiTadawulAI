import os, requests, re

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def run_saudi_analyzer():
    try:
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text: return

        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        ai_input = ""
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    ai_input += f"ID:{symbol} | Data:{line}\n"

        # أمر إجباري لضمان عدم الفراغ
        prompt = f"Analyze these: {ai_input}. You MUST return at least 5 lines. Format: SYMBOL|TARGET|STOP|ANALYSIS"

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        if g_res.status_code != 200: return
        raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        final_output = [l for l in raw_output.strip().split('\n') if '|' in l]

        if not final_output: return

        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص مع الشارتات المباشرة*\n\n"
        count = 0
        for row in final_output:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    # رابط الشارت المباشر من TradingView
                    chart_url = f"https://ar.tradingview.com/symbols/TADAWUL-{symbol}/"
                    
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • [{info['name']} ({symbol})]({chart_url})\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += f"🔗 [لمشاهدة الشارت اضغط هنا]({chart_url})\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة: التقرير قراءة فنية فقط وليس توصية."
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_web_page_preview": False})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
