import os, requests, re, io

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def send_to_telegram(symbol, info, price, target, stop, analysis, index):
    print(f"[DEBUG] محاولة إرسال: {symbol} - {info['name']}")
    
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
        print(f"[DEBUG] جاري تحميل الصورة من: {target_url}")
        img_response = requests.get(target_url, timeout=10)
        img_response.raise_for_status()
        print(f"[DEBUG] تم تحميل الصورة بنجاح - الحجم: {len(img_response.content)} بايت")
        
        photo_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', io.BytesIO(img_response.content), 'image/png')}
        
        res = requests.post(photo_api, data={
            "chat_id": CHAT_ID,
            "caption": caption,
            "parse_mode": "Markdown"
        }, files=files, timeout=10)
        
        print(f"[DEBUG] استجابة Telegram (صورة): {res.status_code} - {res.text[:200]}")
        
        if res.status_code == 200:
            print(f"[SUCCESS] تم إرسال {symbol} بنجاح مع صورة")
            return True
            
    except Exception as e:
        print(f"[ERROR] فشل إرسال الصورة: {e}")
    
    try:
        print(f"[DEBUG] محاولة إرسال رسالة نصية بديلة")
        text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        message_with_link = f"{caption}\n\n[🔗 عرض الشارت]({target_url})"
        
        res = requests.post(text_api, data={
            "chat_id": CHAT_ID,
            "text": message_with_link,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False
        }, timeout=10)
        
        print(f"[DEBUG] استجابة Telegram (نص): {res.status_code} - {res.text[:200]}")
        
        if res.status_code == 200:
            print(f"[SUCCESS] تم إرسال {symbol} بنجاح كنص")
            return True
        
    except Exception as e:
        print(f"[ERROR] فشل إرسال الرسالة: {e}")
    
    return False

def run_saudi_analyzer():
    print("=" * 60)
    print("بدء تشغيل محلل السوق السعودي")
    print("=" * 60)
    
    try:
        # التحقق من المتغيرات البيئية
        print("\n[1] التحقق من المتغيرات البيئية...")
        print(f"  - GEMINI_KEY: {'✓ موجود' if GEMINI_KEY else '✗ مفقود'}")
        print(f"  - TELEGRAM_TOKEN: {'✓ موجود' if TELEGRAM_TOKEN else '✗ مفقود'}")
        print(f"  - CHAT_ID: {CHAT_ID if CHAT_ID else '✗ مفقود'}")
        print(f"  - CSV_URL: {'✓ موجود' if URL else '✗ مفقود'}")
        
        if not all([GEMINI_KEY, TELEGRAM_TOKEN, CHAT_ID, URL]):
            print("\n[ERROR] متغيرات البيئة غير مكتملة!")
            return
        
        # تحميل ملف CSV
        print("\n[2] جاري تحميل بيانات CSV...")
        response = requests.get(URL, timeout=60)
        response.raise_for_status()
        print(f"  ✓ تم التحميل بنجاح - الحجم: {len(response.text)} حرف")
        
        csv_text = response.text.strip()
        if not csv_text:
            print("[ERROR] ملف CSV فارغ!")
            return

        lines = csv_text.split('\n')
        print(f"  ✓ عدد الأسطر: {len(lines)}")
        print(f"  ✓ عدد الأسهم في tadawul_map: {len(tadawul_map)}")
        
        # معالجة البيانات
        print("\n[3] جاري معالجة البيانات...")
        ai_input = ""
        stock_prices = {}
        top_list = []

        for idx, line in enumerate(lines[1:], 1):
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
                        print(f"  ✓ معالج: {symbol} - {tadawul_map[symbol]['name']} - السعر: {price}")

        print(f"\n  📊 إجمالي الأسهم المعالجة: {len(stock_prices)}")
        print(f"  📊 الأسهم في القائمة المختصرة: {top_list}")

        if not ai_input:
            print("\n[ERROR] لم يتم العثور على أسهم للتحليل!")
            print("  تحقق من:")
            print("  1. ملف companies.py موجود ويحتوي على tadawul_map")
            print("  2. رموز الأسهم في CSV تطابق الرموز في tadawul_map")
            return

        # طلب التحليل من Gemini
        print("\n[4] جاري طلب التحليل من Gemini AI...")
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
        
        print(f"  استجابة Gemini: {g_res.status_code}")
        
        if g_res.status_code != 200:
            print(f"[ERROR] فشل طلب Gemini: {g_res.text[:500]}")

        final_results = []
        if g_res.status_code == 200:
            try:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"\n  رد Gemini الخام:\n{raw_output}\n")
                final_results = [l.strip() for l in raw_output.strip().split('\n') if '|' in l and l.count('|') >= 3]
                print(f"  ✓ عدد النتائج المستخرجة: {len(final_results)}")
            except (KeyError, IndexError) as e:
                print(f"[ERROR] خطأ في معالجة رد Gemini: {e}")
                print(f"  الرد الكامل: {g_res.text[:500]}")

        # إذا فشل التحليل، استخدم البيانات الافتراضية
        if not final_results:
            print("\n[WARNING] استخدام البيانات الافتراضية...")
            for s in top_list[:3]:
                try:
                    p = float(stock_prices.get(s, 0))
                    if p > 0:
                        final_results.append(f"{s}|{round(p*1.03,2)}|{round(p*0.97,2)}|قيد المراقبة الفنية")
                        print(f"  + إضافة افتراضي: {s}")
                except ValueError:
                    continue

        print(f"\n  📋 النتائج النهائية للإرسال: {len(final_results)}")

        # إرسال النتائج
        print("\n[5] جاري إرسال الرسائل إلى Telegram...")
        sent_count = 0
        for i, row in enumerate(final_results[:3]):
            print(f"\n  --- معالجة النتيجة #{i+1} ---")
            print(f"  البيانات: {row}")
            
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                
                if not info:
                    print(f"  [SKIP] لم يتم العثور على معلومات {symbol} في tadawul_map")
                    continue
                    
                if symbol not in stock_prices:
                    print(f"  [SKIP] لم يتم العثور على سعر {symbol}")
                    continue
                
                success = send_to_telegram(
                    symbol, 
                    info, 
                    stock_prices[symbol], 
                    parts[1].strip(), 
                    parts[2].strip(), 
                    parts[3].strip(), 
                    i
                )
                
                if success:
                    sent_count += 1
            else:
                print(f"  [SKIP] تنسيق غير صحيح - عدد الأجزاء: {len(parts)}")
        
        print("\n" + "=" * 60)
        print(f"✓ انتهى التحليل - تم إرسال {sent_count} من {len(final_results)} توصيات")
        print("=" * 60)

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] خطأ في الاتصال بالشبكة: {e}")
    except Exception as e:
        print(f"\n[ERROR] خطأ غير متوقع: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_saudi_analyzer()
