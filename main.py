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
    """إرسال كل سهم في رسالة منفصلة بصورة شارت احترافية من Market-In-Out"""
    
    # بناء رابط الصورة المباشر من محرك Market-In-Out مع المؤشرات الفنية المتقدمة
    # المؤشرات: 132(RSI), 46(Bollinger), 61(Moving Average)
    chart_img = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days&s=big&tdata=1"
    
    # تنسيق نص الرسالة (بدون أي روابط خارجية لضمان الخصوصية)
    caption = (
        f"🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{info['name']}* ({symbol})\n"
        f"💰 السعر الحالي: {price} ريال\n"
        f"📈 التحليل الفني: {analysis}\n"
        f"🎯 الهدف المرصود: {target}\n"
        f"🛡️ وقف الخسارة: {stop}\n\n"
        f"📍 التصنيف: {info['market']}"
    )

    # إرسال الصورة كرسالة أساسية (Photo) لضمان ظهورها بحجم كبير
    photo_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": chart_img,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    
    res = requests.post(photo_api, data=payload, timeout=30)
    
    # نظام الأمان: إذا تعذر إرسال الصورة (لأسباب تقنية في الخادم)، نرسل النص فوراً
    if res.status_code != 200:
        text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(text_api, data={"chat_id": CHAT_ID, "text": caption, "parse_mode": "Markdown"})

def run_saudi_analyzer():
    try:
        # 1. جلب البيانات اللحظية
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
                    p_match = re.search(r'(\d+\.\d+)', line)
                    price = p_match.group(1) if p_match else "---"
                    stock_prices[symbol] = price
                    if len(top_list) < 5: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        # 2. طلب التحليل الفني المركز
        prompt = f"""
        Analyze these Saudi stocks. Return top 3 positive ones.
        Format: SYMBOL|TARGET|STOP|ANALYSIS
        Rules: Target +3%, Stop -2% based on Price. No intros.
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

        # 3. نظام الطوارئ في حال الفراغ
        if not final_results:
            for s in top_list[:3]:
                p = stock_prices.get(s, "0")
                target = round(float(p)*1.03, 2) if p != "0" else "---"
                stop = round(float(p)*0.97, 2) if p != "0" else "---"
                final_results.append(f"{s}|{target}|{stop}|ارتداد فني متوقع من القاع")

        # 4. توزيع الرسائل (كل سهم بطاقة مستقلة)
        for i, row in enumerate(final_results):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info:
                    send_to_telegram(symbol, info, stock_prices.get(symbol, "---"), parts[1], parts[2], parts[3], i)

    except Exception as e:
        print(f"حدث خطأ: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
