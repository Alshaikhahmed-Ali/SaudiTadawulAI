import os, requests, re, io, time
from bs4 import BeautifulSoup
from datetime import datetime

try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

COMPANY_INFO_CACHE = {}

def get_chart_url(symbol):
    return f"https://www.tradingview.com/chart/?symbol=TADAWUL%3A{symbol}"

def scrape_argaam_news(symbol):
    news = []
    try:
        url = f"https://www.argaam.com/ar/company/news/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        print(f"    - جلب الأخبار من أرقام...")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            news_items = soup.find_all('div', class_=['article-title', 'news-item', 'title'], limit=5)
            for item in news_items[:3]:
                news_text = item.get_text(strip=True)
                if news_text and len(news_text) > 10:
                    news_text = news_text[:100] if len(news_text) > 100 else news_text
                    news.append(news_text)
            if news:
                print(f"    ✓ تم جلب {len(news)} خبر من أرقام")
    except Exception as e:
        print(f"    [WARNING] فشل جلب الأخبار من أرقام: {e}")
    return news

def scrape_tadawul_events(symbol):
    events = []
    try:
        url = f"https://www.saudiexchange.sa/wps/portal/saudiexchange/listing/company-profile-main/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        print(f"    - جلب الأحداث من تداول...")
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            date_elements = soup.find_all(['span', 'div', 'td'], class_=re.compile('date|event', re.I), limit=10)
            for elem in date_elements[:3]:
                event_text = elem.get_text(strip=True)
                if event_text and len(event_text) > 5:
                    events.append(event_text[:80])
            if events:
                print(f"    ✓ تم جلب {len(events)} حدث من تداول")
    except Exception as e:
        print(f"    [WARNING] فشل جلب الأحداث من تداول: {e}")
    return events

def get_company_info_from_gemini(symbol, info, news_context=""):
    try:
        if news_context:
            prompt = f"أنت محلل سوق سعودي. الشركة: {info['name']} (رمز: {symbol})\n\nلديك الأخبار التالية:\n{news_context}\n\nلخص أهم 3 أخبار بشكل مختصر وواضح (سطر واحد لكل خبر، بدون أرقام):\n- خبر مختصر\n- خبر مختصر\n- خبر مختصر"
        else:
            prompt = f"أنت محلل سوق سعودي. الشركة: {info['name']} (رمز: {symbol})\n\nاذكر 3 أحداث مالية نموذجية قد تهم المستثمرين (بدون تواريخ محددة):\n- حدث عام\n- حدث عام\n- حدث عام"
        g_res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}", json={"contents": [{"parts": [{"text": prompt}]}]}, headers={'Content-Type': 'application/json'}, timeout=15)
        if g_res.status_code == 200:
            response_text = g_res.json()['candidates'][0]['content']['parts'][0]['text']
            items = []
            for line in response_text.strip().split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    clean_line = line[1:].strip()
                    if clean_line:
                        items.append(clean_line)
            return items[:3] if items else []
    except Exception as e:
        print(f"    [WARNING] فشل تحليل Gemini: {e}")
    return []

def get_company_info(symbol, info):
    if symbol in COMPANY_INFO_CACHE:
        print(f"  ✓ استخدام البيانات من الذاكرة المؤقتة")
        return COMPANY_INFO_CACHE[symbol]
    print(f"  📡 جلب معلومات حقيقية عن {info['name']}...")
    news_list = scrape_argaam_news(symbol)
    events_list = scrape_tadawul_events(symbol)
    if not news_list:
        print(f"    - لم يتم العثور على أخبار، استخدام Gemini...")
        news_list = get_company_info_from_gemini(symbol, info, "")
    if not events_list:
        print(f"    - لم يتم العثور على أحداث...")
        events_list = []
    if not news_list:
        news_list = ['لا توجد أخبار حديثة متاحة']
    if not events_list:
        events_list = ['لا توجد أحداث مجدولة معلنة']
    result = {'events': events_list[:3], 'news': news_list[:3]}
    COMPANY_INFO_CACHE[symbol] = result
    return result

def escape_markdown_v2(text):
    text = text.replace('\\', '\\\\')
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def build_telegram_message(symbol, info, price, target, stop, analysis, index, company_data):
    chart_url = get_chart_url(symbol)
    events_text = ""
    for i, event in enumerate(company_data['events'], 1):
        events_text += f"{i}\\. {escape_markdown_v2(event)}\n"
    news_text = ""
    for i, news_item in enumerate(company_data['news'], 1):
        news_text += f"{i}\\. {escape_markdown_v2(news_item)}\n"
    message_v2 = f"🦅 *قناص السوق السعودي \\(AI\\)* 🇸🇦\n\n{EMOJIS[index]} • *{escape_markdown_v2(info['name'])}* \\({symbol}\\)\n💰 السعر: `{price}` ريال\n📈 التحليل الفني: {escape_markdown_v2(analysis)}\n🎯 الهدف: `{target}` \\| 🛡️ الوقف: `{stop}`\n\n📍 {escape_markdown_v2(info['market'])}\n\n📅 *الأحداث القادمة:*\n{events_text}\n📰 *آخر الأخبار:*\n{news_text}\n📊 [عرض الشارت]({chart_url})\n\n⚠️ _هذا تحليل فني وليس توصية بيع أو شراء_"
    events_simple = "\n".join([f"{i}. {e}" for i, e in enumerate(company_data['events'], 1)])
    news_simple = "\n".join([f"{i}. {n}" for i, n in enumerate(company_data['news'], 1)])
    message_simple = f"🦅 قناص السوق السعودي (AI) 🇸🇦\n\n{EMOJIS[index]} • {info['name']} ({symbol})\n💰 السعر: {price} ريال\n📈 التحليل الفني: {analysis}\n🎯 الهدف: {target} | 🛡️ الوقف: {stop}\n\n📍 {info['market']}\n\n📅 الأحداث القادمة:\n{events_simple}\n\n📰 آخر الأخبار:\n{news_simple}\n\n📊 عرض الشارت: {chart_url}\n\n⚠️ هذا تحليل فني وليس توصية بيع أو شراء"
    return message_v2, message_simple
    def send_telegram_message(message, parse_mode=None):
    text_api = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "disable_web_page_preview": False}
    if parse_mode:
        data["parse_mode"] = parse_mode
    try:
        response = requests.post(text_api, data=data, timeout=10)
        return response.status_code == 200, response
    except Exception as e:
        return False, str(e)

def send_to_telegram(symbol, info, price, target, stop, analysis, index, company_data):
    print(f"[DEBUG] إرسال: {symbol} - {info['name']}")
    message_v2, message_simple = build_telegram_message(symbol, info, price, target, stop, analysis, index, company_data)
    success, response = send_telegram_message(message_v2, "MarkdownV2")
    if success:
        print(f"[SUCCESS] ✓ تم إرسال {symbol} بنجاح (MarkdownV2)")
        return True
    print(f"[WARNING] فشل MarkdownV2، محاولة التنسيق البسيط...")
    success, response = send_telegram_message(message_simple, None)
    if success:
        print(f"[SUCCESS] ✓ تم إرسال {symbol} بنجاح (تنسيق بسيط)")
        return True
    else:
        print(f"[ERROR] فشل الإرسال تماماً: {response}")
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
        required_vars = {'GEMINI_KEY': GEMINI_KEY, 'TELEGRAM_TOKEN': TELEGRAM_TOKEN, 'CHAT_ID': CHAT_ID, 'CSV_URL': URL}
        for var_name, var_value in required_vars.items():
            status = '✓ موجود' if var_value else '✗ مفقود'
            print(f"  - {var_name}: {status}")
        if not all(required_vars.values()):
            print("\n[ERROR] ⚠️ متغيرات البيئة غير مكتملة!")
            return
        print("  ✓ جميع المتغيرات موجودة")
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
                    ai_input += f"ID:{symbol} Price:{price} Data:{line}\n"
        print(f"  ✓ تمت معالجة {len(stock_prices)} سهم")
        if len(stock_prices) > 0:
            print(f"  📊 عينة: {list(stock_prices.items())[:3]}")
        if not ai_input:
            print("\n[ERROR] ⚠️ لم يتم العثور على أسهم للتحليل!")
            return
        print("\n[4] جاري طلب التحليل من Gemini AI...")
        prompt = f"أنت محلل سوق أسهم سعودي خبير. حلل البيانات التالية:\n\n{ai_input}\n\nاختر أفضل 3 أسهم بناءً على المؤشرات الفنية.\n\nأرجع النتيجة بهذا الشكل بالضبط (بدون ترقيم):\nSYMBOL|TARGET_PRICE|STOP_LOSS|BRIEF_ANALYSIS\n\nمثال:\n1234|45.50|42.30|اختراق مستوى مقاومة مع حجم تداول قوي\n5678|120.80|115.20|تشكيل نموذج فني إيجابي"
        g_res = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_KEY}", json={"contents": [{"parts": [{"text": prompt}]}]}, headers={'Content-Type': 'application/json'}, timeout=30)
        print(f"  استجابة Gemini: {g_res.status_code}")
        final_results = []
        if g_res.status_code == 200:
            try:
                raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
                print(f"\n  📝 رد Gemini (أول 3 أسطر):")
                for line in raw_output.strip().split('\n')[:3]:
                    print(f"    {line}")
                final_results = [l.strip() for l in raw_output.strip().split('\n') if '|' in l and l.count('|') >= 3]
                print(f"  ✓ تم استخراج {len(final_results)} نتيجة")
            except (KeyError, IndexError) as e:
                print(f"  [ERROR] خطأ في معالجة رد Gemini: {e}")
        if not final_results:
            print("\n[WARNING] ⚠️ استخدام البيانات الافتراضية...")
            for s in top_list[:3]:
                try:
                    p = float(stock_prices.get(s, 0))
                    if p > 0:
                        target = round(p * 1.03, 2)
                        stop = round(p * 0.97, 2)
                        final_results.append(f"{s}|{target}|{stop}|قيد المراقبة الفنية")
                except ValueError:
                    continue
        print("\n[5] جاري جلب معلومات الشركات وإرسال التوصيات...")
        sent_count = 0
        for i, row in enumerate(final_results[:3]):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                info = tadawul_map.get(symbol)
                if info and symbol in stock_prices:
                    print(f"\n  [{i+1}/3] معالجة {symbol} - {info['name']}")
                    company_data = get_company_info(symbol, info)
                    success = send_to_telegram(symbol, info, stock_prices[symbol], parts[1].strip(), parts[2].strip(), parts[3].strip(), i, company_data)
                    if success:
                        sent_count += 1
                        if i < min(len(final_results), 3) - 1:
                            print("  ⏳ انتظار 3 ثواني...")
                            time.sleep(3)
        print("\n" + "=" * 60)
        print(f"✅ انتهى التحليل بنجاح!")
        print(f"📊 تم إرسال {sent_count} من {len(final_results)} توصيات")
        print(f"💾 تم حفظ {len(COMPANY_INFO_CACHE)} شركة في الذاكرة المؤقتة")
        print("=" * 60)
    except requests.exceptions.RequestException as e:
        print(f"\n[ERROR] ❌ خطأ في الاتصال بالشبكة: {e}")
    except Exception as e:
        print(f"\n[ERROR] ❌ خطأ غير متوقع: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_saudi_analyzer()
