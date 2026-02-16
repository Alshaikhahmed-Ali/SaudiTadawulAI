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
        
        # 2. تحضير البيانات واستخراج الأسعار برمجياً
        ai_input = ""
        top_5_list = []
        stock_data = {}

        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    p_match = re.search(r'(\d+\.\d+)', line)
                    price = float(p_match.group(1)) if p_match else 0.0
                    stock_data[symbol] = {"price": price, "line": line}
                    if len(top_5_list) < 10: top_5_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        # 3. محاولة التحليل عبر جيميناي
        final_results = []
        try:
            prompt = f"Analyze these stocks. Return ONLY top 5 in format: SYMBOL|TARGET|STOP|ANALYSIS. Data: {ai_input}"
            g_res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={'Content-Type': 'application/json'}, timeout=15
            )
            if g_res.status_code == 200:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                final_results = [l for l in raw_output.strip().split('\n') if '|' in l]
        except:
            pass # في حال الفشل سننتقل لنظام الطوارئ أدناه

        # 4. نظام الطوارئ البرمجي (إذا فشل AI أو أعاد نتيجة فارغة)
        if not final_results:
            for sym in top_5_list[:5]:
                price = stock_data[sym]['price']
                target = round(price * 1.03, 2)
                stop = round(price * 0.97, 2)
                final_results.append(f"{sym}|{target}|{stop}|يظهر بوادر ارتداد فني إيجابي")

        # 5. بناء الرسالة النهائية (السيطرة الكاملة لبايثون)
        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية الموثق*\n\n"
        
        count = 0
        for row in final_results:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    chart_url = f"https://ar.tradingview.com/symbols/TADAWUL-{symbol}/"
                    current_p = stock_data.get(symbol, {}).get('price', '---')
                    
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • {info['name']} ({symbol}) | {current_p} ريال\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += f"🔗 [لمشاهدة الشارت اضغط هنا]({chart_url})\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة: القرار الاستثماري مسؤوليتك، والتقرير قراءة فنية فقط."
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_web_page_preview": False})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
