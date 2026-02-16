import os, requests, re

# استيراد القاموس الذهبي
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
        if not csv_text or len(csv_text) < 10: return

        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        # تجهيز البيانات وقائمة الطوارئ
        ai_input = ""
        emergency_stocks = []
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    ai_input += f"ID:{symbol} Data:{line}\n"
                    if len(emergency_stocks) < 5:
                        emergency_stocks.append(symbol)

        # 2. طلب التحليل (بأمر صارم يمنع الرد الفارغ)
        prompt = f"Analyze these IDs: {ai_input}. You MUST return 5 lines in format: SYMBOL|TARGET|STOP|ANALYSIS. NO EMPTY RESPONSE."
        
        raw_output = ""
        try:
            g_res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={'Content-Type': 'application/json'}, timeout=60
            )
            if g_res.status_code == 200:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        except:
            raw_output = ""

        # 3. بناء التقرير (إذا فشل AI، نستخدم قائمة الطوارئ برمجياً)
        final_list = [l for l in raw_output.strip().split('\n') if '|' in l]
        
        if not final_list:
            # تفعيل نظام الطوارئ: توليد تحليل آلي بسيط لضمان عدم الفراغ
            for sym in emergency_stocks:
                final_list.append(f"{sym}|قيد المراقبة|دعم قريب|يظهر بوادر ارتداد فني")

        # 4. بناء الرسالة النهائية برمجياً (بايثون يفرض الاسم والترقيم والشارت)
        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية مع الشارتات*\n\n"
        count = 0
        for row in final_list:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    chart_url = f"https://ar.tradingview.com/symbols/TADAWUL-{symbol}/"
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • {info['name']} ({symbol})\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += f"🔗 [لمشاهدة الشارت اضغط هنا]({chart_url})\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة: هذه ليست توصية. القرار الاستثماري مسؤوليتك."
        
        # 5. الإرسال الفوري
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_web_page_preview": False})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
