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
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text: return

        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        ai_input = ""
        stock_data = {}
        top_list = []

        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    p_match = re.search(r'(\d+\.\d+)', line)
                    price = p_match.group(1) if p_match else "---"
                    stock_data[symbol] = {"price": price, "line": line}
                    if len(top_list) < 7: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        # طلب التحليل الفني
        prompt = f"Analyze stocks: {ai_input}. Return top 5 in format: SYMBOL|TARGET|STOP|ANALYSIS"
        
        final_results = []
        try:
            g_res = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                headers={'Content-Type': 'application/json'}, timeout=30
            )
            if g_res.status_code == 200:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                final_results = [l for l in raw_output.strip().split('\n') if '|' in l]
        except: pass

        if not final_results:
            for s in top_list[:5]: final_results.append(f"{s}|--- |--- |يظهر بوادر ارتداد فني")

        # بناء الرسالة مع روابط الشارتات الفنية
        report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تحليل فني متقدم مع الشارتات والمؤشرات*\n\n"
        
        count = 0
        for row in final_results:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    # رابط الشارت المتقدم من TradingView (للمعاينة البصرية)
                    tv_chart = f"https://ar.tradingview.com/symbols/TADAWUL-{symbol}/"
                    
                    # رابط الفلتر مع المؤشرات الفنية (الرابط الذي زودتني به تم تطويعه لكل سهم)
                    filter_url = f"https://alfa.marketinout.com/screener/run?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days;&s=big"
                    
                    report += f"### {info['market']}\n"
                    report += f"{EMOJIS[count]} • *{info['name']}* ({symbol}) | {stock_data[symbol]['price']} ريال\n"
                    report += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    report += f"📊 [فتح الشارت الفني المباشر 📈]({tv_chart})\n"
                    report += f"🔍 [تحليل المؤشرات التفصيلي (RSI/MACD)]({filter_url})\n"
                    report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        report += "\n🔴 ملاحظة: التقرير قراءة فنية وليس توصية استثمارية."
        
        # إرسال الرسالة مع تفعيل المعاينة (Web Page Preview) لتظهر صورة الشارت تلقائياً
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_web_page_preview": False})

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
