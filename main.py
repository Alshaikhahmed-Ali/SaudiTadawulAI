import os, requests, re

# استيراد القاموس الذي تم بناؤه ميكانيكياً من ملفك
try: 
    from companies import tadawul_map
except ImportError: 
    tadawul_map = {}

# إعدادات الربط والبيئة
GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
URL = os.environ.get("CSV_URL")

# خريطة أرقام الإيموجي للترقيم الجمالي
EMOJI_NUMS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

def run_saudi_analyzer():
    try:
        # 1. جلب البيانات اللحظية من الفلتر
        response = requests.get(URL, timeout=60)
        csv_text = response.text.strip()
        if not csv_text or len(csv_text) < 10: 
            return

        # 2. تجهيز البيانات (نرسل الرموز فقط للذكاء الاصطناعي لمنعه من التخمين)
        lines = csv_text.split('\n')
        if "Symbol" in lines[0]: lines = lines[1:]
        
        ai_input_data = ""
        for line in lines:
            match = re.search(r'(\d{4})', line)
            if match:
                symbol = match.group(1)
                if symbol in tadawul_map:
                    # نرسل الرمز والمعطيات الفنية فقط؛ "الاسم" يبقى مخفياً عن AI في هذه المرحلة
                    ai_input_data += f"ID:{symbol} | الفنيات:{line}\n"

        if not ai_input_data:
            return

        # 3. برومبت "المحلل التقني الصامت" (يحلل الأرقام فقط)
        prompt = f"""
        حلل هذه الأسهم السعودية فنياً بناءً على المعطيات المرفقة.
        اختر أفضل 10 فرص إيجابية فقط.
        يجب أن يكون ردك بصيغة: الرمز|الهدف|الوقف|التحليل_الموجز
        ممنوع كتابة أي أسماء شركات، اكتفِ بالرمز فقط.
        
        المعطيات:
        {ai_input_data}
        """

        # طلب التحليل من جيميناي
        g_res = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            headers={'Content-Type': 'application/json'}, timeout=120
        )

        if g_res.status_code != 200:
            return
            
        raw_output = g_res.json()['candidates'][0]['content']['parts'][0]['text']

        # 4. بناء الرسالة النهائية (بايثون هو من يضع الاسم من ملفك والترقيم)
        final_message = "🦅🇸🇦 **قناص السوق السعودي (AI)** 🇸🇦🦅\n*تقرير الفرص اللحظية الموثق*\n\n"
        
        count = 0
        lines_output = raw_output.strip().split('\n')
        
        for row in lines_output:
            parts = row.split('|')
            if len(parts) >= 4 and count < 10:
                symbol = parts[0].strip()
                target = parts[1].strip()
                stop = parts[2].strip()
                analysis = parts[3].strip()
                
                # جلب البيانات الصحيحة من القاموس (هنا نضمن عدم التخمين)
                info = tadawul_map.get(symbol)
                if info:
                    emoji = EMOJI_NUMS[count]
                    final_message += f"### {info['market']}\n"
                    final_message += f"{emoji} • {info['name']} ({symbol})\n"
                    final_message += f"📈 {analysis}\n🎯 هدف: {target} | 🛡️ وقف: {stop}\n"
                    final_message += "ــــــــــــــــــــــــــــــــــــــــــــــــ\n"
                    count += 1

        final_message += "\n🔴 ملاحظة هامة: هذه الرسالة ليست توصية بيع أو شراء. فالقرار الاستثماري مسؤوليتك، والتقرير هذا قراءة فنية فقط.\n✦✦✦"
        
        # 5. إرسال التقرير النهائي لتيليجرام
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={"chat_id": CHAT_ID, "text": final_message, "parse_mode": "Markdown"})

    except Exception as e:
        print(f"حدث خطأ: {e}")

if __name__ == "__main__":
    run_saudi_analyzer()
