import os, requests, re, io, time

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def get_chart_urls(symbol):
    """الحصول على روابط بديلة للشارت"""
    return {
        'tradingview': f"https://www.tradingview.com/chart/?symbol=TADAWUL%3A{symbol}",
        'mubasher': f"https://www.mubasher.info/markets/TDWL/stocks/{symbol}"
    }

def get_company_info(symbol, info):
    """الحصول على معلومات إضافية عن الشركة من Gemini"""
    try:
        prompt = (
            f"أنت محلل سوق سعودي متخصص. الشركة: {info['name']} (رمز: {symbol})\n\n"
            f"أرجع المعلومات التالية بالضبط بهذا التنسيق:\n\n"
            f"EVENTS:\n"
            f"- [تاريخ] حدث\n"
            f"- [تاريخ] حدث\n"
            f"- [تاريخ] حدث\n\n"
            f"NEWS:\n"
            f"- خبر قصير\n"
            f"- خبر قصير\n"
            f"- خبر قصير\n\n"
            f"إذا لم تكن لديك معلومات حقيقية، أرجع:\n"
            f"EVENTS:\n- لا توجد أحداث مجدولة\n\n"
            f"NEWS:\n- لا توجد أخبار حديثة"
        )
        
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        
        if g_res.status_code == 200:
            response_text = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            
            # استخراج الأحداث والأخبار
            events = []
            news = []
            
            lines = response_text.strip().split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if 'EVENTS:' in line:
                    current_section = 'events'
                elif 'NEWS:' in line:
                    current_section = 'news'
                elif line.startswith('-') and line != '-':
                    clean_line = line[1:].strip()
                    if current_section == 'events' and len(events) < 3:
                        events.append(clean_line)
                    elif current_section == 'news' and len(news) < 3:
                        news.append(clean_line)
            
            return {
                'events': events if events else ['لا توجد أحداث مجدولة'],
                'news': news if news else ['لا توجد أخبار حديثة']
            }
    
    except Exception as e:
        print(f"  [WARNING] فشل جلب معلومات الشركة: {e}")
    
    return {
        'events': ['لا توجد أحداث مجدولة'],
        'news': ['لا توجد أخبار حديثة']
    }

def escape_markdown(text):
    """تنظيف النص للـ MarkdownV2"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def send_to_telegram(symbol, info, price, target, stop, analysis, index):
    """إرسال كل سهم في رسالة منفصلة مع روابط الشارت"""
    
    chart_urls = get_chart_urls(symbol)
    
    # الحصول على معلومات الشركة (الأحداث والأخبار)
    print(f"  جاري جلب معلومات الشركة...")
    company_data = get_company_info(symbol, info)
    
    # بناء الرسالة مع MarkdownV2
    name_escaped = escape_markdown(info['name'])
    market_escaped = escape_markdown(info['market'])
    analysis_escaped = escape_markdown(analysis)
    
    # بناء قائمة الأحداث
    events_text = ""
    for i, event in enumerate(company_data['events'][:3], 1):
        event_escaped = escape_markdown(event)
        events_text += f"{i}\\. {event_escaped}\n"
    
    # بناء قائمة الأخبار
    news_text = ""
    for i, news_item in enumerate(company_data['news'][:3], 1):
        news_escaped = escape_markdown(news_item)
        news_text += f"{i}\\. {news_escaped}\n"
    
    caption = (
        f"🦅 *قناص السوق السعودي \\(AI\\)* 🇸🇦\n\n"
        f"{EMOJIS[index]} • *{name_escaped}* \\({symbol}\\)\n"
        f"💰 السعر: `{price}` ريال\n"
        f"📈 التحليل الفني: {analysis_escaped}\n"
        f"🎯 الهدف: `{target}` \\| 🛡️ الوقف: `{stop}`\n\n"
        f"📍 {market_escaped}\n\n"
        f"📅 *الأحداث القادمة:*\n{events_text}\n"
        f"📰 *آخر الأخبار:*\n{news_text}\n"
        f"📊 [عرض الشارت على TradingView]({chart_urls['tradingview']})\n\n"
        f"⚠️ _هذا تحليل فني وليس توصية بيع أو شراء_"
    )

    try:
        print(f"[DEBUG] محاولة إرسال: {symbol} - {info['name']}")
        
        text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        res = requests.post(text_api, data={
            "chat_id": CHAT_ID,
            "text": caption,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False
        }, timeout=10)
        
        if res.status_code == 200:
            print(f"[SUCCESS] ✓ تم إرسال {symbol} بنجاح")
            return True
        else:
            print(f"[WARNING] فشل MarkdownV2: {res.status_code}")
            
            # محاولة بديلة بتنسيق بسيط
            events_simple = "\n".join([f"{i}. {e}" for i, e in enumerate(company_data['events'][:3], 1)])
            news_simple = "\n".join([f"{i}. {n}" for i, n in enumerate(company_data['news'][:3], 1)])
            
            simple_caption = (
                f"🦅 قناص السوق السعودي (AI) 🇸🇦\n\n"
                f"{EMOJIS[index]} • {info['name']} ({symbol})\n"
                f"💰 السعر: {price} ريال\n"
                f"📈 التحليل الفني: {analysis}\n"
                f"🎯 الهدف: {target} | 🛡️ الوقف: {stop}\n\n"
                f"📍 {info['market']}\n\n"
                f"📅 الأحداث القادمة:\n{events_simple}\n\n"
                f"📰 آخر الأخبار:\n{news_simple}\n\n"
                f"📊 عرض الشارت: {chart_urls['tradingview']}\n\n"
                f"⚠️ هذا تحليل فني وليس توصية بيع أو شراء"
            )
            
            res2 = requests.post(text_api, data={
                "chat_id": CHAT_ID,
                "text": simple_caption,
                "disable_web_page_preview": False
            }, timeout=10)
            
            if res2.status_code == 200:
                print(f"[SUCCESS] ✓ تم إرسال {symbol} بتنسيق بسيط")
                return True
            else:
                print(f"[ERROR] فشل الإرسال تماماً: {res2.text[:200]}")
        
    except Exception as e:
        print(f"[ERROR] استثناء أثناء الإرسال: {e}")
    
    return False

def extract_stock_symbol(line):
    """استخراج رمز السهم من السطر مع التحقق من السياق"""
    # البحث عن رمز مكون من 4 أرقام
    matches = re.findall(r'\b(\d{4})\b', line)
    
    # تصفية النتائج: استبعاد السنوات (2020-2030)
    valid_symbols = [m for m in matches if m not in [str(y) for y in range(2020, 2031)]]
    
    # إرجاع أول رمز صالح موجود في tadawul_map
    for symbol in valid_symbols:
        if symbol in tadawul_map:
            return symbol
    
    return None

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
            print("\n[ERROR] ⚠️ متغيرات البيئة غير مكتملة!")
            return
        print("  ✓ جميع المتغيرات موجودة")
        
        # تحميل ملف CSV
        print("\n[2] جاري تحميل بيانات CSV...")
        response = requests.get(URL, timeout=60)
        response.raise_for_status()
        print(f"  ✓ تم التحميل - الحجم: {len(response.text):,} حرف")
        
        csv_text = response.text.strip()
        if not csv_text:
            print("  [ERROR] ملف CSV فارغ!")
            return

        lines = csv_text.split('\n')
        print(f"  ✓ عدد الأسطر: {len(lines)}")
        print(f"  ✓ عدد الأسهم في قاعدة البيانات: {len(tadawul_map)}")
        
        # معالجة البيانات
        print("\n[3] جاري معالجة البيانات...")
        ai_input = ""
        stock_prices = {}
        top_list = []
        processed_count = 0

        for line in lines[1:]:  # تخطي الهيدر
            if not line.strip():
                continue
            
            # استخدام الدالة المحسّنة لاستخراج الرمز
            symbol = extract_stock_symbol(line)
            
            if symbol:
                # البحث عن السعر
                p_match = re.search(r'(\d+\.\d+)', line)
                if p_match:
                    price = p_match.group(1)
                    stock_prices[symbol] = price
                    if len(top_list) < 5:
                        top_list.append(symbol)
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"
                    processed_count += 1
                    
                    if processed_count <= 3:  # طباعة أول 3 فقط
                        print(f"  ✓ {symbol} - {tadawul_map[symbol]['name']} - {price} ريال")

        if processed_count > 3:
            print(f"  ... وتمت معالجة {processed_count - 3} سهم إضافي")
        
        print(f"\n  📊 إجمالي الأسهم المعالجة: {len(stock_prices)}")

        if not ai_input:
            print("\n[ERROR] ⚠️ لم يتم العثور على أسهم للتحليل!")
            print("  تحقق من:")
            print("  1. ملف companies.py موجود ويحتوي على tadawul_map")
            print("  2. رموز الأسهم في CSV تطابق الرموز في tadawul_map")
            print("  3. صيغة ملف CSV صحيحة")
            return

        # طلب التحليل من Gemini
        print("\n[4] جاري طلب التحليل من Gemini AI...")
        prompt = (
            f"أنت محلل سوق أسهم سعودي خبير. حلل البيانات التالية بعناية:\n\n{ai_input}\n\n"
            "اختر أفضل 3 أسهم بناءً على:\n"
            "- الزخم السعري والحجم\n"
            "- المؤشرات الفنية\n"
            "- نسب المخاطرة/العائد\n\n"
            "أرجع النتيجة بالضبط بهذا الشكل (سطر واحد لكل سهم، بدون ترقيم):\n"
            "SYMBOL|TARGET_PRICE|STOP_LOSS|BRIEF_ANALYSIS\n\n"
            "مثال:\n"
            "1234|45.50|42.30|اختراق مستوى مقاومة مع حجم تداول قوي\n"
            "5678|120.80|115.20|تشكيل نموذج فني إيجابي"
        )
        
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"  استجابة Gemini: {g_res.status_code}")

        final_results = []
        if g_res.status_code == 200:
            try:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"\n  📝 رد Gemini:")
                print("  " + "-" * 50)
                for line in raw_output.strip().split('\n')[:5]:  # طباعة أول 5 أسطر
                    print(f"  {line}")
                print("  " + "-" * 50)
                
                # استخراج النتائج
                final_results = [l.strip() for l in raw_output.strip().split('\n') 
                               if '|' in l and l.count('|') >= 3]
                print(f"\n  ✓ عدد النتائج المستخرجة: {len(final_results)}")
                
            except (KeyError, IndexError) as e:
                print(f"  [ERROR] خطأ في معالجة رد Gemini: {e}")

        # إذا فشل التحليل، استخدم البيانات الافتراضية
        if not final_results:
            print("\n[WARNING] ⚠️ استخدام البيانات الافتراضية...")
            for s in top_list[:3]:
                try:
                    p = float(stock_prices.get(s, 0))
                    if p > 0:
                        target = round(p * 1.03, 2)
                        stop = round(p * 0.97, 2)
                        final_results.append(f"{s}|{target}|{stop}|قيد المراقبة الفنية")
                        print(f"  + {s}: هدف {target} | وقف {stop}")
                except ValueError:
                    continue

        # إرسال النتائج مع فواصل زمنية
        print("\n[5] جاري إرسال التوصيات إلى Telegram...")
        print("  (مع فاصل زمني 2 ثانية بين كل رسالة لتجنب Rate Limiting)")
        
        sent_count = 0
        for i, row in enumerate(final_results[:3]):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                
                if info and symbol in stock_prices:
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
                        # إضافة فاصل زمني بين الرسائل (إلا الأخيرة)
                        if i < min(len(final_results), 3) - 1:
                            print("  ⏳ انتظار ثانيتين...")
                            time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"✅ انتهى التحليل بنجاح!")
        print(f"📊 تم إرسال {sent_count} من {len(final_results)} توصيات")
        print("=" * 60)

    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] ❌ خطأ في الاتصال بالشبكة: {e}")
    except Exception as e:
        print(f"\n[ERROR] ❌ خطأ غير متوقع: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_saudi_analyzer()
