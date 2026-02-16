import os, requests, re

# استيراد القاموس الذهبي الموثق
try: 
    from companies import tadawul_map
except ImportError: 
    tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

# إيموجي الأرقام
EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def run_saudi_analyzer():
    try:
        # 1. جلب البيانات اللحظية
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text or len(csv_text) < 10: return

        # 2. تجهيز البيانات (رموز فقط)
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        ai_input = ""
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    ai_input += f"ID:{symbol} | Data:{line}\n"

        if not ai_input: return

        # 3. برومبت "إجباري": يمنع الرد الفارغ ويمنع المسميات الخارجية
        prompt = f"""
        Analyze these symbols technically. You MUST return at least 5 opportunities.
        If indicators are weak, pick the best relative ones.
        Output format: SYMBOL|TARGET|STOP|TECHNICAL_STRENGTH
        Strict Rules: NO NAMES. NO INTROS. NO EMPTY RESPONSE.
        Data:
        {ai_input}
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        if g_res.status_code != 200: return
        raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']

        # 4. بناء الرسالة برمجياً (بايثون يفرض الاسم والترقيم)
        report_lines = raw_output.strip().split('\n')
        if not report_lines or len(report_lines[0]) < 5:
            # نظام الطوارئ إذا حاول AI التهرب
            return 

        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية الموثق*\n\n"
        
        count = 0
        for row in report_lines:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol = parts[0].strip()
                target = parts[1].strip()
                stop = parts[2].strip()
                analysis = parts[3].strip()
                
                info = tadawul_map.get(symbol)
                if info:
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • {info['name']} ({symbol})\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة هامة: هذه الرسالة ليست توصية بيع أو شراء. فالقرار الاستثماري مسؤوليتك، والتقرير هذا قراءة فنية فقط.\n✦✦✦"
        
        # 5. الإرسال لتيليجرام
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown"})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
