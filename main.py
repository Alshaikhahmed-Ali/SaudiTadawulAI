import os, requests, re

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def send_to_telegram(symbol, info, price, target, stop, analysis, index):
    # رابط الصورة الفنية (مخفي)
    # أضفت امتداد وهمي .png في نهاية الرابط لإقناع تيليجرام بأنه صورة
    chart_img = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days&s=big&tdata=1#.png"
    
    # نضع الرابط في سبيس (مساحة) مخفية في بداية الرسالة
    # المشترك سيرى الصورة فوق النص ولن يرى الرابط
    hidden_link = f"[ ]({chart_img})"
    
    caption = (
        f"{hidden_link}🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{info['name']}* ({symbol})\n"
        f"💰 السعر الحالي: {price} ريال\n"
        f"📈 التحليل: {analysis}\n"
        f"🎯 الهدف: {target}\n"
        f"🛡️ الوقف: {stop}\n\n"
        f"📍 {info['market']}"
    )

    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": caption,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False # تفعيل المعاينة لإظهار الصورة
    }
    requests.post(api_url, data=payload)

def run_saudi_analyzer():
    try:
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text: return

        lines = csv_text.split('\n')[1:] # تخطي الرأس
        
        ai_input = ""
        stock_prices = {}
        top_list = []

        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    p_match = re.search(r'(\d+\.\d+)', line)
                    price = p_match.group(1) if p_match else "0"
                    stock_prices[symbol] = price
                    if len(top_list) < 5: top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        # طلب التحليل من جيميناي
        prompt = f"Analyze: {ai_input}. Return top 3 in format: SYMBOL|TARGET|STOP|ANALYSIS."
        
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

        # نظام الطوارئ (حساب الأرقام برمجياً)
        if not final_results:
            for s in top_list[:3]:
                p = float(stock_prices.get(s, 0))
                final_results.append(f"{s}|{round(p*1.03,2)}|{round(p*0.97,2)}|ارتداد فني متوقع")

        # إرسال الرسائل
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
