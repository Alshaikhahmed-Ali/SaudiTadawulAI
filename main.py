import os, requests, re, io

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def send_to_telegram(symbol, info, price, target, stop, analysis, index):
    target_url = f"https://alfa.marketinout.com/chart/draw?symbol={symbol}.SA&indicator=132,7,2,days;46,7,3,days;61,7,days&s=big"
    
    caption = (
        f"🦅 **قناص السوق السعودي (AI)** 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{info['name']}* ({symbol})\n"
        f"💰 السعر: {price} ريال\n"
        f"📈 التحليل: {analysis}\n"
        f"🎯 هدف: {target} | 🛡️ وقف: {stop}\n\n"
        f"📍 {info['market']}"
    )

    try:
        img_response = requests.get(target_url, timeout=10)
        img_response.raise_for_status()
        
        photo_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', io.BytesIO(img_response.content), 'image/png')}
        
        res = requests.post(photo_api, data={
            "chat_id": CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown"
        }, files=files, timeout=10)
        
        if res.status_code == 200:
            return True
            
    except Exception as e:
        print(f"فشل إرسال الصورة: {e}")
    
    try:
        text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        message_with_link = f"{caption}\n\n[🔗 عرض الشارت]({target_url})"
        
        requests.post(text_api, data={
            "chat_id": CHAT_ID,
            "text": message_with_link,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }, timeout=10)
        
    except Exception as e:
        print(f"فشل إرسال الرسالة: {e}")

def run_saudi_analyzer():
    try:
        if not all([GEMINI_KEY, TELEGRAM_TOKEN, CHAT_ID, URL]):
            print("خطأ: متغيرات البيئة غير مكتملة")
            return
            
        response = requests.get(URL, timeout=60)
        response.raise_for_status()
        
        csv_text = response.text.strip()
        if not csv_text:
            print("تحذير: ملف CSV فارغ")
            return

        lines = csv_text.split('\n')[1:]
        
        ai_input = ""
        stock_prices = {}
        top_list = []

        for line in lines:
            if not line.strip():
                continue
                
            match = re.search(r'\b(\d{4})\b', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    p_match = re.search(r'(\d+\.\d+)', line)
                    if p_match:
                        price = p_match.group(1)
                        stock_prices[symbol] = price
                        if len(top_list) < 5:
                            top_list.append(symbol)
                        ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"

        if not ai_input:
            print("تحذير: لم يتم العثور على أسهم للتحليل")
            return

        prompt = (
            f"أنت محلل سوق أسهم سعودي خبير. حلل البيانات التالية:\n\n{ai_input}\n\n"
            "اختر أفضل 3 أسهم وأرجع النتيجة بالضبط بهذا الشكل (سطر واحد لكل سهم):\n"
            "SYMBOL|TARGET_PRICE|STOP_LOSS|BRIEF_ANALYSIS\n"
            "مثال: 1234|45.50|42.30|اختراق مستوى مقاومة مع حجم تداول قوي"
        )
        
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        g_res.raise_for_status()

        final_results = []
        if g_res.status_code == 200:
            try:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                final_results = [l.strip() for l in raw_output.strip().split('\n') if '|' in l and l.count('|') >= 3]
            except (KeyError, IndexError) as e:
                print(f"خطأ في معالجة رد Gemini: {e}")

        if not final_results:
            print("تحذير: استخدام البيانات الافتراضية")
            for s in top_list[:3]:
                try:
                    p = float(stock_prices.get(s, 0))
                    if p > 0:
                        final_results.append(f"{s}|{round(p*1.03,2)}|{round(p*0.97,2)}|قيد المراقبة الفنية")
                except ValueError:
                    continue

        sent_count = 0
        for i, row in enumerate(final_results[:3]):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info and symbol in stock_prices:
                    send_to_telegram(
                        symbol, 
                        info, 
                        stock_prices[symbol], 
                        parts[1].strip(), 
                        parts[2].strip(), 
                        parts[3].strip(), 
                        i
                    )
                    sent_count += 1
        
        print(f"✓ تم إرسال {sent_count} توصيات بنجاح")

    except requests.exceptions.RequestException as e:
        print(f"خطأ في الاتصال بالشبكة: {e}")
    except Exception as e:
        print(f"خطأ غير متوقع: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_saudi_analyzer()
