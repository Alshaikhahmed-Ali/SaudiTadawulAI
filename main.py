import os, requests, re

# استيراد القاموس الذهبي الموثق
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def send_photo_with_text(photo_url, caption):
    """إرسال صورة الشارت مع النص التوضيحي أسفلها"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    try: requests.post(url, data=payload, timeout=30)
    except: pass

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
                    if len(top_list) < 5: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        prompt = f"Analyze stocks: {ai_input}. Return top 3 positive in format: SYMBOL|TARGET|STOP|ANALYSIS"
        
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
            for s in top_list[:3]: final_results.append(f"{s}|--- |--- |مراقبة فنية")

        # بناء وإرسال الصور مع التحليل
        for i, row in enumerate(final_results):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol, target, stop, analysis = parts[0].strip(), parts[1].strip(), parts[2].strip(), parts[3].strip()
                info = tadawul_map.get(symbol)
                if info:
                    # توليد رابط الصورة المباشر مع المؤشرات الفنية (حجم كبير)
                    # هذا الرابط يسحب صورة الشارت فقط بدون واجهة الموقع
                    chart_img_url = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days;148,8,15,6;84,15,8,6&s=big"
                    
                    caption = (
                        f"🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
                        f"{EMOJIS[i]} • *{info['name']}* ({symbol})\n"
                        f"💰 السعر: {stock_data[symbol]['price']} ريال\n"
                        f"📈 {analysis}\n"
                        f"🎯 هدف: {target} | 🛡️ وقف: {stop}\n\n"
                        f"📍 {info['market']}"
                    )
                    
                    # إرسال الصورة كرسالة مستقلة لكل شركة
                    send_photo_with_text(chart_img_url, caption)

    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
