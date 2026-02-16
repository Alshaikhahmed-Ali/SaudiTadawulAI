import os, requests, re, time
from bs4 import BeautifulSoup

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
COMPANY_INFO_CACHE = {}

def get_chart_url(symbol):
    return "https://www.tradingview.com/chart/?symbol=TADAWUL%3A" + symbol

def scrape_tadawul_company_info(symbol):
    """جلب الأخبار والتواريخ المهمة من موقع تداول الرسمي"""
    news = []
    events = []
    
    try:
        url = "https://www.saudiexchange.sa/wps/portal/saudiexchange/hidden/company-profile-main/!ut/p/z1/04_Sj9CPykssy0xPLMnMz0vMAfIjo8ziTR3NDIw8LAz83d2MXA0C3SydAl1c3Q0NvE30w1EVGAQHmAIVBPga-xgEGbgbmOlHEaPfAAdwNCCsPwqvEndzdAVYnAhWgMcNXvpR6Tn5SZDwyCgpKbBSNVA1KElMSSwvzVEFujE5P7cgMa8yuDI3KR-oyNjAxEC_IDc0wiAzIDfcUVERAAAhGaQ!/dz/d5/L0lDUmlTUSEhL3dHa0FKRnNBLzROV3FpQSEhL2Fy/?symbol=" + symbol
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'ar,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        
        print("    - جلب البيانات من موقع تداول...")
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # محاولة استخراج الأخبار
            news_elements = soup.find_all(['div', 'li', 'tr', 'p'], class_=re.compile('news|article|announcement', re.I), limit=10)
            news_elements += soup.find_all(['a', 'span'], string=re.compile('إعلان|خبر|تقرير|إفصاح', re.I), limit=10)
            
            for elem in news_elements[:5]:
                text = elem.get_text(strip=True)
                if text and len(text) > 15 and len(text) < 200:
                    # تنظيف النص
                    text = re.sub(r'\s+', ' ', text)
                    if text not in news:
                        news.append(text)
                        if len(news) >= 3:
                            break
            
            # محاولة استخراج التواريخ والأحداث
            date_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}'
            date_elements = soup.find_all(['div', 'td', 'span', 'li'], string=re.compile(date_pattern))
            
            for elem in date_elements[:10]:
                text = elem.get_text(strip=True)
                parent_text = elem.parent.get_text(strip=True) if elem.parent else ""
                
                # البحث عن سياق الحدث
                if any(keyword in parent_text for keyword in ['اجتماع', 'جمعية', 'توزيع', 'أرباح', 'نتائج', 'إعلان']):
                    event_text = parent_text[:120]
                    event_text = re.sub(r'\s+', ' ', event_text)
                    if event_text and event_text not in events:
                        events.append(event_text)
                        if len(events) >= 3:
                            break
            
            # البحث عن جدول التواريخ المهمة
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[:5]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        row_text = ' - '.join([cell.get_text(strip=True) for cell in cells])
                        if re.search(date_pattern, row_text) and len(row_text) > 10:
                            row_text = re.sub(r'\s+', ' ', row_text)[:100]
                            if row_text not in events:
                                events.append(row_text)
                                if len(events) >= 3:
                                    break
            
            if news:
                print("    ✓ تم جلب " + str(len(news)) + " خبر من تداول")
            if events:
                print("    ✓ تم جلب " + str(len(events)) + " حدث من تداول")
        
        else:
            print("    [WARNING] فشل الوصول لموقع تداول: " + str(response.status_code))
    
    except Exception as e:
        print("    [WARNING] خطأ في جلب البيانات من تداول: " + str(e))
    
    return {'news': news, 'events': events}

def get_company_info_from_gemini(symbol, info, scraped_data):
    """استخدام Gemini لتلخيص أو توليد معلومات إضافية"""
    try:
        if scraped_data['news'] or scraped_data['events']:
            # إذا كان لدينا بيانات حقيقية، نطلب من Gemini تلخيصها فقط
            news_text = "\n".join(scraped_data['news']) if scraped_data['news'] else "لا توجد أخبار"
            events_text = "\n".join(scraped_data['events']) if scraped_data['events'] else "لا توجد أحداث"
            
            prompt = "لديك البيانات التالية عن شركة " + info['name'] + ":\n\nالأخبار:\n" + news_text + "\n\nالأحداث:\n" + events_text + "\n\nلخص أهم 3 نقاط من الأخبار وأهم 3 تواريخ/أحداث بشكل واضح ومختصر (سطر واحد لكل نقطة).\n\nأرجع النتيجة بهذا التنسيق:\n\nNEWS:\n- خبر مختصر\n- خبر مختصر\n- خبر مختصر\n\nEVENTS:\n- حدث وتاريخه\n- حدث وتاريخه\n- حدث وتاريخه"
        else:
            # إذا لم نجد بيانات، نطلب من Gemini معلومات عامة
            prompt = "أنت محلل سوق سعودي. الشركة: " + info['name'] + " (رمز: " + symbol + ")\n\nاذكر:\n1. 3 أحداث مالية نموذجية قد تهم المستثمرين\n2. 3 أنواع أخبار عامة قد تصدر عن الشركة\n\nNEWS:\n- نوع خبر محتمل\n- نوع خبر محتمل\n- نوع خبر محتمل\n\nEVENTS:\n- نوع حدث محتمل\n- نوع حدث محتمل\n- نوع حدث محتمل"
        
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + GEMINI_KEY
        g_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}, headers={'Content-Type': 'application/json'}, timeout=15)
        
        if g_res.status_code == 200:
            response_text = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            
            events = []
            news = []
            current_section = None
            
            for line in response_text.strip().split('\n'):
                line = line.strip()
                if 'EVENTS:' in line or 'الأحداث' in line:
                    current_section = 'events'
                elif 'NEWS:' in line or 'الأخبار' in line:
                    current_section = 'news'
                elif line.startswith('-') or line.startswith('•'):
                    clean_line = line.lstrip('-•').strip()
                    if clean_line:
                        if current_section == 'events' and len(events) < 3:
                            events.append(clean_line)
                        elif current_section == 'news' and len(news) < 3:
                            news.append(clean_line)
            
            return {'events': events, 'news': news}
    
    except Exception as e:
        print("    [WARNING] فشل Gemini: " + str(e))
    
    return {'events': [], 'news': []}

def get_company_info(symbol, info):
    """جلب معلومات الشركة من موقع تداول أولاً، ثم Gemini للتلخيص"""
    if symbol in COMPANY_INFO_CACHE:
        print("  ✓ استخدام البيانات من الذاكرة المؤقتة")
        return COMPANY_INFO_CACHE[symbol]
    
    print("  📡 جلب معلومات عن " + info['name'] + "...")
    
    # 1. محاولة جلب البيانات الحقيقية من موقع تداول
    scraped_data = scrape_tadawul_company_info(symbol)
    
    # 2. استخدام Gemini للتلخيص أو التكملة
    gemini_data = get_company_info_from_gemini(symbol, info, scraped_data)
    
    # 3. دمج البيانات
    final_news = scraped_data['news'][:3] if scraped_data['news'] else gemini_data['news'][:3]
    final_events = scraped_data['events'][:3] if scraped_data['events'] else gemini_data['events'][:3]
    
    # التأكد من وجود بيانات
    if not final_news:
        final_news = ['لا توجد أخبار حديثة متاحة']
    if not final_events:
        final_events = ['لا توجد أحداث مجدولة معلنة']
    
    result = {'events': final_events[:3], 'news': final_news[:3]}
    COMPANY_INFO_CACHE[symbol] = result
    
    return result

def escape_markdown_v2(text):
    text = text.replace('\\', '\\\\')
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text

def build_telegram_message(symbol, info, price, target, stop, analysis, index, company_data):
    chart_url = get_chart_url(symbol)
    
    events_text = ""
    for i, event in enumerate(company_data['events'][:3], 1):
        events_text += str(i) + "\\. " + escape_markdown_v2(event) + "\n"
    
    news_text = ""
    for i, news_item in enumerate(company_data['news'][:3], 1):
        news_text += str(i) + "\\. " + escape_markdown_v2(news_item) + "\n"
    
    message_v2 = (
        "🦅 *قناص السوق السعودي \\(AI\\)* 🇸🇦\n\n" +
        EMOJIS[index] + " • *" + escape_markdown_v2(info['name']) + "* \\(" + symbol + "\\)\n" +
        "💰 السعر: `" + price + "` ريال\n" +
        "📈 التحليل الفني: " + escape_markdown_v2(analysis) + "\n" +
        "🎯 الهدف: `" + target + "` \\| 🛡️ الوقف: `" + stop + "`\n\n" +
        "📍 " + escape_markdown_v2(info['market']) + "\n\n" +
        "📅 *الأحداث القادمة:*\n" + events_text + "\n" +
        "📰 *آخر الأخبار:*\n" + news_text + "\n" +
        "📊 [عرض الشارت على TradingView](" + chart_url + ")\n\n" +
        "⚠️ _هذا تحليل فني وليس توصية بيع أو شراء_"
    )
    
    events_simple = "\n".join([str(i) + ". " + e for i, e in enumerate(company_data['events'][:3], 1)])
    news_simple = "\n".join([str(i) + ". " + n for i, n in enumerate(company_data['news'][:3], 1)])
    
    message_simple = (
        "🦅 قناص السوق السعودي (AI) 🇸🇦\n\n" +
        EMOJIS[index] + " • " + info['name'] + " (" + symbol + ")\n" +
        "💰 السعر: " + price + " ريال\n" +
        "📈 التحليل الفني: " + analysis + "\n" +
        "🎯 الهدف: " + target + " | 🛡️ الوقف: " + stop + "\n\n" +
        "📍 " + info['market'] + "\n\n" +
        "📅 الأحداث القادمة:\n" + events_simple + "\n\n" +
        "📰 آخر الأخبار:\n" + news_simple + "\n\n" +
        "📊 عرض الشارت: " + chart_url + "\n\n" +
        "⚠️ هذا تحليل فني وليس توصية بيع أو شراء"
    )
    
    return message_v2, message_simple

def send_telegram_message(message, parse_mode=None):
    text_api = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": False}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        response = requests.post(text_api, data=data, timeout=10)
        return response.status_code == 200, response
    except Exception as e:
        return False, str(e)

def send_to_telegram(symbol, info, price, target, stop, analysis, index, company_data):
    print("[DEBUG] إرسال: " + symbol + " - " + info['name'])
    message_v2, message_simple = build_telegram_message(symbol, info, price, target, stop, analysis, index, company_data)
    success, response = send_telegram_message(message_v2, "MarkdownV2")
    if success:
        print("[SUCCESS] ✓ تم إرسال " + symbol + " بنجاح")
        return True
    print("[WARNING] فشل MarkdownV2، محاولة التنسيق البسيط...")
    success, response = send_telegram_message(message_simple, None)
    if success:
        print("[SUCCESS] ✓ تم إرسال " + symbol + " بنجاح")
        return True
    else:
        print("[ERROR] فشل الإرسال")
        return False

def extract_stock_symbol(line):
    matches = re.findall(r'\b(\d{4})\b', line)
    valid_symbols = [m for m in matches if m not in [str(y) for y in range(2020, 2031)]]
    for symbol in valid_symbols:
        if symbol in tadawul_map:
            return symbol
    return None

def run_saudi_analyzer():
    print("=" * 60)
    print("🚀 بدء تشغيل محلل السوق السعودي")
    print("=" * 60)
    try:
        print("\n[1] التحقق من المتغيرات البيئية...")
        if not all([GEMINI_KEY, TELEGRAM_TOKEN, CHAT_ID, URL]):
            print("[ERROR] متغيرات البيئة غير مكتملة!")
            return
        print("  ✓ جميع المتغيرات موجودة")
        
        print("\n[2] جاري تحميل CSV...")
        response = requests.get(URL, timeout=60)
        response.raise_for_status()
        csv_text = response.text.strip()
        if not csv_text:
            return
        lines = csv_text.split('\n')
        print("  ✓ تم التحميل")
        
        print("\n[3] جاري معالجة البيانات...")
        ai_input = ""
        stock_prices = {}
        top_list = []
        
        for line in lines[1:]:
            if not line.strip():
                continue
            symbol = extract_stock_symbol(line)
            if symbol:
                p_match = re.search(r'(\d+\.\d+)', line)
                if p_match:
                    price = p_match.group(1)
                    stock_prices[symbol] = price
                    if len(top_list) < 5:
                        top_list.append(symbol)
                    ai_input += "السهم: " + tadawul_map[symbol]['name'] + " (" + symbol + ") - السعر: " + price + " ريال\nالبيانات: " + line + "\n\n"
        
        print("  ✓ معالجة " + str(len(stock_prices)) + " سهم")
        
        if not ai_input:
            return
        
        print("\n[4] جاري طلب التحليل...")
        prompt = "أنت محلل فني سعودي خبير.\n\nالبيانات:\n" + ai_input + "\n\nاختر أفضل 3 أسهم بناءً على التحليل الفني.\n\nالتنسيق:\nSYMBOL|TARGET|STOP|ANALYSIS\n\nمثال:\n1120|88.50|82.00|اختراق مقاومة 85 ريال بحجم قوي"
        
        api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + GEMINI_KEY
        g_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}, headers={'Content-Type': 'application/json'}, timeout=30)
        
        final_results = []
        if g_res.status_code == 200:
            try:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                print("  ✓ رد Gemini:")
                for line in raw_output.strip().split('\n')[:3]:
                    print("    " + line)
                final_results = [l.strip() for l in raw_output.strip().split('\n') if '|' in l and l.count('|') >= 3]
            except:
                pass
        
        if not final_results:
            for s in top_list[:3]:
                p = float(stock_prices.get(s, 0))
                if p > 0:
                    final_results.append(s + "|" + str(round(p*1.03,2)) + "|" + str(round(p*0.97,2)) + "|قيد المراقبة الفنية")
        
        print("\n[5] جاري إرسال التوصيات...")
        sent_count = 0
        for i, row in enumerate(final_results[:3]):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info and symbol in stock_prices:
                    company_data = get_company_info(symbol, info)
                    success = send_to_telegram(symbol, info, stock_prices[symbol], parts[1].strip(), parts[2].strip(), parts[3].strip(), i, company_data)
                    if success:
                        sent_count += 1
                        if i < 2:
                            time.sleep(3)
        
        print("\n✅ تم إرسال " + str(sent_count) + " توصيات")
    
    except Exception as e:
        print("[ERROR] " + str(e))

if __name__ == "__main__":
    run_saudi_analyzer()
