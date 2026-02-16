import os, requests, re

# استيراد القاموس الذهبي
try: from companies import tadawul_map
except ImportError: tadawul_map = {}

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

# خريطة أرقام الإيموجي
EMOJI_NUMS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def run_saudi_analyzer():
    try:
        # 1. جلب البيانات
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text or len(csv_text) < 10: return

        # 2. تحضير البيانات لـ AI (نرسل الرموز فقط والبيانات الفنية)
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]

        analysis_input = ""
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    # نرسل الرمز والبيانات الفنية فقط - لا نرسل الاسم لـ AI لنمنعه من الهلوسة
                    analysis_input += f"Symbol: {symbol} | Data: {line}\n"

        if not analysis_input: return

        # 3. طلب التحليل من AI بتنسيق خاص (رمز|هدف|وقف|تحليل)
        prompt = f"""
        Analyze these Saudi stocks. Return ONLY the positive stocks.
        For each positive stock, use this EXACT format:
        SYMBOL|TARGET|STOP|ANALYSIS
        
        Rules:
        - No company names.
        - No headers or intro text.
        - One stock per line.
        - Analyze based on the technical data provided:
        {analysis_input}
        """

        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        if g_res.status_code != 200: return
        
        raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']
        
        # 4. بناء الرسالة النهائية برمجياً (هنا نضمن دقة الأسماء والترقيم)
        final_report = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية*\n\n"
        
        count = 0
        for row in raw_output.strip().split('\n'):
            parts = row.split('|')
            if len(parts) >= 4:
                symbol = parts[0].strip()
                target = parts[1].strip()
                stop = parts[2].strip()
                analysis = parts[3].strip()
                
                # جلب البيانات الصحيحة من ملفك يقيناً
                info = tadawul_map.get(symbol)
                if info and count < 10:
                    emoji = EMOJI_NUMS[count]
                    # استخراج السعر الحالي من النص (بافتراض أنه الرقم العشري الأول)
                    price_match = re.search(r'\d+\.\d+', analysis_input)
                    price = price_match.group(0) if price_match else "---"
                    
                    final_report += f"### {info['market']}\n"
                    final_report += f"{emoji} • {info['name']} ({symbol}) | السعر التقريبي\n"
                    final_report += f"📈 {analysis} | 🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    final_report += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        final_report += "\n🔴 ملاحظة: هذه الرسالة ليست توصية. القرار الاستثماري مسؤوليتك، والتقرير قراءة فنية فقط."
        
        # إرسال لتيليجرام
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": final_report, "parse_mode": "Markdown"})

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
