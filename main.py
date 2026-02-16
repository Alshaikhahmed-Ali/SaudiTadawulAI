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
    """محاولة إرسال صورة، وإذا فشلت نرسل نصاً لضمان وصول المعلومة"""
    chart_img = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days&s=big"
    caption = (
        f"🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{info['name']}* ({symbol})\n"
        f"💰 السعر: {price} ريال\n"
        f"📈 {analysis}\n"
        f"🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
        f"📍 {info['market']}"
    )

    # محاولة إرسال صورة
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    res = requests.post(photo_url, data={"chat_id": CHAT_ID, "photo": chart_img, "caption": caption, "parse_mode": "Markdown"})
    
    # إذا فشل إرسال الصورة، نرسل نصاً عادياً فوراً كبديل
    if res.status_code != 200:
        text_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        fallback_text = caption + f"\n🔗 [مشاهدة الشارت المباشر](https://ar.tradingview.com/symbols/TADAWUL-{symbol}/)"
        requests.post(text_url, data={"chat_id": CHAT_ID, "text": fallback_text, "parse_mode": "Markdown"})

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
                    stock_data[symbol] = price
                    if len(top_list) < 5: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        prompt = f"Analyze: {ai_input}. Return top 3 in format: SYMBOL|TARGET|STOP|ANALYSIS. No intro."
        
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=30
        )

        final_results = []
        if g_res.status_code == 200:
            raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            final_results = [l for l in raw_output.strip().split('\n') if '|' in l]

        # إذا لم نجد نتائج من AI، نستخدم قائمة الطوارئ
        if not final_results:
            for s in top_list[:3]: final_results.append(f"{s}|--- |--- |مراقبة فنية دقيقة")

        for i, row in enumerate(final_results):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info:
                    send_to_telegram(symbol, info, stock_data.get(symbol, "---"), parts[1], parts[2], parts[3], i)

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
