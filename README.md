# 🤖 AI Trading Bot - نظام التداول الذكي

نظام تداول ذكي متكامل يعمل مع Binance، يستخدم التحليل الفني والذكاء الاصطناعي لاتخاذ قرارات تداول دقيقة.

---

## 📁 هيكل المشروع

```
bot/
├── main.py                 # الملف الرئيسي - نقطة الدخول
├── config.py               # إعدادات النظام المركزية
├── database.py             # قاعدة بيانات MySQL
├── binance_client.py       # عميل Binance (CCXT)
├── technical_analysis.py   # التحليل الفني
├── ai_model.py             # نموذج الذكاء الاصطناعي
├── strategy_engine.py      # محرك الاستراتيجية
├── risk_manager.py         # إدارة المخاطر
├── execution_engine.py     # محرك التنفيذ
├── alerts.py               # نظام التنبيهات
├── telegram_bot.py         # بوت Telegram
├── dashboard/
│   ├── app.py              # FastAPI Backend
│   └── templates/
│       └── index.html      # لوحة التحكم
├── .env.example            # نموذج متغيرات البيئة
├── requirements.txt        # المكتبات المطلوبة
├── run.bat                 # سكربت التشغيل (Windows)
└── README.md               # هذا الملف
```

---

## ⚡ التشغيل السريع

### 1. المتطلبات
- **Python 3.10+**
- **MySQL** (XAMPP أو مستقل)
- **مفاتيح Binance API** (من [binance.com](https://www.binance.com/en/my/settings/api-management))
- **بوت Telegram** (من [@BotFather](https://t.me/BotFather))

### 2. الإعداد

```bash
# نسخ ملف الإعدادات
cp .env.example .env

# تعديل .env وإضافة المفاتيح
notepad .env

# تثبيت المكتبات
pip install -r requirements.txt
```

### 3. تعديل `.env`

```env
BINANCE_API_KEY=مفتاحك_هنا
BINANCE_API_SECRET=سرك_هنا
BINANCE_SANDBOX=true          # true للاختبار، false للتداول الحقيقي

TELEGRAM_BOT_TOKEN=توكن_البوت
TELEGRAM_CHAT_ID=معرف_المحادثة

DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=trading_bot
```

### 4. التشغيل

```bash
# الطريقة 1: بنقرة واحدة
run.bat

# الطريقة 2: يدوياً
python main.py
```

### 5. الوصول
- **لوحة التحكم**: http://localhost:8000
- **بوت Telegram**: أرسل `/start` للبوت

---

## 📊 أوامر Telegram

| الأمر | الوظيفة |
|-------|---------|
| `/start` | تشغيل البوت |
| `/stop` | إيقاف البوت |
| `/status` | حالة البوت |
| `/balance` | عرض الرصيد |
| `/profit` | الأرباح والخسائر |
| `/trades` | الصفقات المفتوحة |
| `/history` | سجل آخر 10 صفقات |
| `/buy [عملة]` | شراء يدوي |
| `/sell [عملة]` | بيع يدوي |
| `/stats` | إحصائيات شاملة |

---

## 🧠 كيف يعمل البوت؟

```
كل 60 ثانية:
  1. جلب بيانات السوق (OHLCV) لكل عملة
  2. التحليل الفني (RSI, MA50/200, MACD, Volume)
  3. تحليل متقدم (اتجاه، دعم/مقاومة، اختراقات)
  4. تقييم AI (درجة 0-100)
  5. قرار الاستراتيجية (شراء/بيع/انتظار)
  6. التحقق من إدارة المخاطر
  7. تنفيذ الصفقة + وقف خسارة + جني أرباح
  8. مراقبة الصفقات المفتوحة
  9. تنبيه Telegram + تحديث قاعدة البيانات
```

## 🛡️ إدارة المخاطر

- **المخاطرة**: 1% من رأس المال لكل صفقة
- **وقف الخسارة**: 1.5%
- **جني الأرباح**: 3% - 5%
- **حد يومي**: إيقاف عند خسارة 5% يومياً
- **أقصى صفقات**: 3 صفقات مفتوحة

---

## ⚠️ تحذيرات مهمة

> **⚠️ استخدم Testnet أولاً**: ابدأ دائماً بـ `BINANCE_SANDBOX=true`

> **⚠️ لا تفعّل السحب**: عند إنشاء API Key، لا تفعّل صلاحية Withdraw

> **⚠️ استخدم IP Whitelist**: حدد عنوان IP في إعدادات API

> **⚠️ هذا ليس ضمان ربح**: التداول يحمل مخاطر. لا تستثمر أكثر مما يمكنك تحمل خسارته.
