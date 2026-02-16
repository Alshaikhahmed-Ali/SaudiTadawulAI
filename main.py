import os, requests, re

# استيراد القاموس الذهبي الموثق
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def send_to_telegram(symbol, info, price, target, stop, analysis, index):
    """إرسال كل سهم في رسالة منفصلة (صورة شارت + بيانات)"""
    # رابط الصورة المباشر (يُستخدم فقط للسحب البرمجي ولا يظهر للمشترك)
    chart_img = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days&s=big"
    
    # بناء نص الرسالة (بدون روابط خارجية)
    caption = (
        f"🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{info['name']}* ({symbol})\n"
        f"💰 السعر الحالي: {price} ريال\n"
        f"📈 التحليل: {analysis}\n"
        f"🎯 الهدف القادم: {target}\n"
        f"🛡️ وقف الخسارة: {stop}\n\n"
        f"📍 التصنيف: {info['market']}"
    )

    # إرسال الصورة كرسالة مستقلة
    photo_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    res = requests.post(photo_api, data={"chat_id": CHAT_ID, "photo": chart_img, "caption": caption, "parse_mode": "Markdown"})
    
    # نظام الأمان: إذا تعذر إرسال الصورة، نرسل البيانات كنص فوراً
    if res.status_code != 200:
        text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(text_api, data={"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"})

def run_saudi_analyzer():
    try:
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text: return

        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        ai_input = ""
        stock_prices = {}
        top_list = []

        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    # استخراج السعر الحالي بدقة
                    p_match = re.search(r'(\d+\.\d+)', line)
                    price = p_match.group(1) if p_match else "---"
                    stock_prices[symbol] = price
                    if len(top_list) < 5: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        # برومبت يفرض استخراج أرقام حقيقية للأهداف والوقف
        prompt = f"""
        Analyze these Saudi stocks. Return top 3 positive ones.
        Output format: SYMBOL|TARGET|STOP|ANALYSIS
        Strict Rules: Use numbers for Target/Stop (CurrentPrice +3% / -2%). No company names.
        Data: {ai_input}
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=30
        )

        final_results = []
        if g_res.status_code == 200:
            raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            final_results = [l for l in raw_output.strip().split('\n') if '|' in l]

        # إذا لم نجد نتائج، نستخدم القائمة البرمجية لضمان عدم الفراغ
        if not final_results:
            for s in top_list[:3]:
                p = stock_prices.get(s, "0")
                target = round(float(p)*1.03, 2) if p != "0" else "---"
                stop = round(float(p)*0.97, 2) if p != "0" else "---"
                final_results.append(f"{s}|{target}|{stop}|ارتداد فني من مناطق دعم")

        # إرسال كل نتيجة في رسالة منفصلة
        for i, row in enumerate(final_results):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info:
                    send_to_telegram(symbol, info, stock_prices.get(symbol, "---"), parts[1], parts[2], parts[3], i)

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
