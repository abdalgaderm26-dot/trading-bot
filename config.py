"""
===================================================================
  config.py - مركز الإعدادات الرئيسي لبوت التداول
  Central Configuration for AI Trading Bot
===================================================================
"""

import os
import logging
from dotenv import load_dotenv
from cryptography.fernet import Fernet

# تحميل متغيرات البيئة
load_dotenv()


class Config:
    """إعدادات النظام المركزية"""

    # ──────────────── Binance API ────────────────
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
    BINANCE_SANDBOX = os.getenv("BINANCE_SANDBOX", "true").lower() == "true"
    
    # ──────────────── Futures Trading (Professional) ────────────────
    ENABLE_FUTURES = False   # ⛔ SPOT فقط - الفيوتشرز خطر بدون خبرة كافية
    FUTURES_LEVERAGE = 3
    FUTURES_MARGIN_MODE = "isolated"
    FUTURES_SERVER_SL = os.getenv("FUTURES_SERVER_SL", "true").lower() == "true"
    FUTURES_SERVER_TP = os.getenv("FUTURES_SERVER_TP", "true").lower() == "true"
    FUTURES_MIN_SCORE = int(os.getenv("FUTURES_MIN_SCORE", "70"))  # درجة عالية جداً إذا تم تفعيل الفيوتشرز
    AUTO_TRANSFER_SPOT_TO_FUTURES = False  # ⛔ لا تحويل تلقائي لحماية رأس المال

    # ──────────────── Trading Pairs ────────────────
    # قائمة بأفضل وأقوى 35 عملة رقمية ذات سيولة عالية للتداول
    # قائمة بالعملات ذات التذبذب العالي جداً والمناسبة للاسكالبينج (Meme + AI + Layer1)
    TRADING_PAIRS = [
        "WIF/USDT", "1000FLOKI/USDT", "1000BONK/USDT", "1000SHIB/USDT", "DOGE/USDT",
        "FET/USDT", "RNDR/USDT", "WLD/USDT", "TAO/USDT",
        "SUI/USDT", "SEI/USDT", "APT/USDT", "OP/USDT", "ARB/USDT", "TIA/USDT",
        "INJ/USDT", "GALA/USDT", "ORDI/USDT", "1000SATS/USDT",
        "JTO/USDT", "PYTH/USDT", "STRK/USDT", "ONDO/USDT", "ENA/USDT", "NOT/USDT",
        "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "LINK/USDT",
        "1000PEPE/USDT", "MEME/USDT", "BOME/USDT", "TNSR/USDT", "W/USDT", "OM/USDT",
        "PENDLE/USDT", "FRONT/USDT", "CHZ/USDT", "AVAX/USDT", "NEAR/USDT", "RUNE/USDT",
        "LDO/USDT", "STX/USDT", "ADA/USDT", "TRX/USDT", "XRP/USDT", "DOT/USDT",
        "GALA/USDT", "FIL/USDT", "TON/USDT", "MEW/USDT"
    ]
    DEFAULT_PAIR = "OCEAN/USDT"
    TIMEFRAME = "5m"  # الإطار الزمني السريع للسكالبينج المومينتوم

    # ──────────────── Technical Analysis (Scalping) ────────────────
    RSI_PERIOD = 14
    RSI_BUY_MIN = 35       # شراء عند بداية التشبع البيعي السريع (35)
    RSI_BUY_MAX = 45       # لالتقاط الارتداد مبكراً
    RSI_SELL_MIN = 60      # بيع سريع عند الـ 60
    RSI_SELL_MAX = 70
    MA_FAST = 50            # المتوسط المتحرك السريع
    MA_SLOW = 200           # المتوسط المتحرك البطيء
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    VOLUME_MULTIPLIER = 1.5  # حجم التداول يجب أن يكون 1.5x المتوسط

    # ──────────────── AI Model ────────────────
    AI_SCORE_THRESHOLD = 75  # ⚡ لا تدخل إلا في أفضل فرصة ممكنة - ثقة 75%+
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "trade_model.pkl")
    TRAINING_DATA_SIZE = 500  # عدد الشموع للتدريب

    # ──────────────── Risk Management (ULTRA SAFE - لا خسارة) ────────────────
    RISK_PER_TRADE = 0.20    # ⚡ 20% فقط من الرصيد لكل صفقة - حماية 80% من رأس المال
    STOP_LOSS_PCT = 0.05     # ⚡ 5% وقف خسارة واسع - البوت لن يبيع بخسارة أصلاً (احتياطي طوارئ فقط)
    TAKE_PROFIT_MIN = 0.008  # ⚡ 0.8% هدف أول - يغطي العمولة + ربح صافي مضمون
    TAKE_PROFIT_MAX = 0.025  # ⚡ 2.5% سقف ربح - انتظار ربح أكبر
    CLOSE_ON_MIN_PROFIT = os.getenv("CLOSE_ON_MIN_PROFIT", "true").lower() == "true"
    MIN_PROFIT_CLOSE_PCT = float(os.getenv("MIN_PROFIT_CLOSE_PCT", "0.006"))  # ⚡ 0.6% ربح صافي أدنى - فوق العمولة بأمان
    # مراقبة السيولة العالية فقط
    PUMP_FOCUS_MODE = True  # تفعيل الهجوم السريع والتمركز (Sniper Pump) بشكل صارم جداً
    PUMP_MIN_3C_PCT = float(os.getenv("PUMP_MIN_3C_PCT", "0.008"))  # +0.8% كافية على إطار الخمس دقائق
    PUMP_MIN_5C_PCT = float(os.getenv("PUMP_MIN_5C_PCT", "0.012"))   # +1.2% خلال 5 شموع
    PUMP_VOLUME_RATIO_MIN = float(os.getenv("PUMP_VOLUME_RATIO_MIN", "1.5"))
    STEADY_UP_MIN_5C_PCT = float(os.getenv("STEADY_UP_MIN_5C_PCT", "0.006"))  # +0.6%
    STEADY_UP_MIN_GREEN_CANDLES = int(os.getenv("STEADY_UP_MIN_GREEN_CANDLES", "3"))
    PUMP_SCORE_BONUS = int(os.getenv("PUMP_SCORE_BONUS", "35"))       # رفع المكافأة جداً للدخول في الارتفاع المؤكد
    STEADY_SCORE_BONUS = int(os.getenv("STEADY_SCORE_BONUS", "25"))
    PUMP_QUICK_EXIT_PCT = float(os.getenv("PUMP_QUICK_EXIT_PCT", "0.003")) # 0.3% للربح السريع
    # إغلاق الصفقة الخاسرة فوراً عند الوصول لوقف الخسارة العادي لتجنب التعلق.
    EXIT_LOSS_ONLY_ON_HIGH_RISK = os.getenv("EXIT_LOSS_ONLY_ON_HIGH_RISK", "false").lower() == "true"
    HIGH_RISK_LOSS_PCT = float(os.getenv("HIGH_RISK_LOSS_PCT", "0.015"))  # 1.5% هبوط كحد أقصى للتدخل الطارئ
    # بعد إغلاق الصفقة: تحويل عائد العملات غير USDT تلقائيًا إلى USDT.
    AUTO_CONVERT_PROCEEDS_TO_USDT = os.getenv("AUTO_CONVERT_PROCEEDS_TO_USDT", "true").lower() == "true"
    AUTO_CONVERT_MIN_USDT_VALUE = float(os.getenv("AUTO_CONVERT_MIN_USDT_VALUE", "5.0"))
    AUTO_CONVERT_BUFFER_RATIO = float(os.getenv("AUTO_CONVERT_BUFFER_RATIO", "0.995"))
    DAILY_LOSS_LIMIT = 0.02  # ⚡ إذا خسر 2% - يتوقف فوراً
    MAX_OPEN_TRADES = 1      # ⚡ صفقة واحدة فقط
    ORDER_COOLDOWN = 300     # ⚡ 5 دقائق انتظار بين الصفقات لقراءة السوق جيداً
    MAX_CAPITAL_PER_TRADE = float(os.getenv("MAX_CAPITAL_PER_TRADE", "0.20"))  # ⚡ أقصى 20% من الرصيد
    MIN_TRADE_NOTIONAL = 5.0      # أقل قيمة صفقة لتفادي رفض NOTIONAL
    BALANCE_CACHE_TTL = 8         # كاش للرصيد بالثواني
    ORDER_BOOK_CACHE_SECONDS = 20  # كاش تحليل دفتر الأوامر

    # Spot inventory trading:
    # allows SELL signal to use existing base-asset balance (e.g. sell LTC in LTC/USDT)
    SPOT_INVENTORY_SELL_ENABLED = os.getenv("SPOT_INVENTORY_SELL_ENABLED", "true").lower() == "true"
    SPOT_INVENTORY_SELL_RATIO = float(os.getenv("SPOT_INVENTORY_SELL_RATIO", "0.35"))

    # Optional wallet sync: move quote assets from Funding wallet to Spot wallet.
    AUTO_TRANSFER_FUNDING_TO_SPOT = os.getenv("AUTO_TRANSFER_FUNDING_TO_SPOT", "false").lower() == "true"
    FUNDING_TRANSFER_ASSETS = [
        asset.strip().upper()
        for asset in os.getenv("FUNDING_TRANSFER_ASSETS", "BNB").split(",")
        if asset.strip()
    ]
    FUNDING_TRANSFER_MIN_FREE = float(os.getenv("FUNDING_TRANSFER_MIN_FREE", "0.00001"))

    # تحليل العملات الموجودة في الرصيد وإضافتها تلقائياً للأزواج
    SCAN_BALANCE_COINS = os.getenv("SCAN_BALANCE_COINS", "true").lower() == "true"
    BALANCE_QUOTE_ASSET = os.getenv("BALANCE_QUOTE_ASSET", "USDT").upper()
    BALANCE_QUOTE_ASSETS = [
        asset.strip().upper()
        for asset in os.getenv("BALANCE_QUOTE_ASSETS", "USDT,BNB,LTC").split(",")
        if asset.strip()
    ]
    BALANCE_COIN_MIN_TOTAL = float(os.getenv("BALANCE_COIN_MIN_TOTAL", "0.0"))
    MAX_BALANCE_SCAN_PAIRS = int(os.getenv("MAX_BALANCE_SCAN_PAIRS", "20"))

    # ──────────────── Telegram ────────────────
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # ──────────────── MySQL Database (Supports Railway MySQL) ────────────────
    DB_HOST = os.getenv("MYSQLHOST", os.getenv("DB_HOST", "localhost"))
    DB_PORT = int(os.getenv("MYSQLPORT", os.getenv("DB_PORT", "3306")))
    DB_USER = os.getenv("MYSQLUSER", os.getenv("DB_USER", "root"))
    DB_PASSWORD = os.getenv("MYSQLPASSWORD", os.getenv("DB_PASSWORD", ""))
    DB_NAME = os.getenv("MYSQLDATABASE", os.getenv("DB_NAME", "trading_bot"))

    # ──────────────── Encryption ────────────────
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "")

    # ──────────────── Bot Settings ────────────────
    TRADING_INTERVAL = 5    # دورة كل 5 ثوانٍ - سرعة قصوى للسكالبينج
    LOG_LEVEL = logging.INFO
    LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "bot.log")

    # ──────────────── Dashboard (Supports Railway PORT) ────────────────
    DASHBOARD_HOST = "0.0.0.0"
    DASHBOARD_PORT = int(os.getenv("PORT", "8000"))
    DASHBOARD_ACCESS_TOKEN = os.getenv("DASHBOARD_ACCESS_TOKEN", "")

    @classmethod
    def generate_encryption_key(cls):
        """توليد مفتاح تشفير جديد"""
        key = Fernet.generate_key()
        print(f"🔑 New Encryption Key: {key.decode()}")
        print("   قم بنسخ هذا المفتاح وضعه في ملف .env")
        return key

    @classmethod
    def encrypt_value(cls, value: str) -> str:
        """تشفير قيمة"""
        if not cls.ENCRYPTION_KEY:
            return value
        f = Fernet(cls.ENCRYPTION_KEY.encode())
        return f.encrypt(value.encode()).decode()

    @classmethod
    def decrypt_value(cls, encrypted_value: str) -> str:
        """فك تشفير قيمة"""
        if not cls.ENCRYPTION_KEY:
            return encrypted_value
        f = Fernet(cls.ENCRYPTION_KEY.encode())
        return f.decrypt(encrypted_value.encode()).decode()

    @classmethod
    def validate(cls):
        """التحقق من صحة الإعدادات الأساسية"""
        errors = []
        warnings = []
        if not cls.BINANCE_API_KEY:
            errors.append("❌ BINANCE_API_KEY غير محدد")
        if not cls.BINANCE_API_SECRET:
            errors.append("❌ BINANCE_API_SECRET غير محدد")
        if not cls.TELEGRAM_BOT_TOKEN:
            warnings.append("⚠️ TELEGRAM_BOT_TOKEN غير محدد (التنبيهات لن تعمل)")
        for w in warnings:
            print(w)
        if errors:
            for e in errors:
                print(e)
            return False
        print("✅ الإعدادات الأساسية صحيحة")
        return True


# ──────────────── Logging Setup ────────────────
def setup_logging():
    """إعداد نظام السجلات"""
    log_dir = os.path.dirname(Config.LOG_FILE)
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(Config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )
    # تقليل سجلات المكتبات الخارجية
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

    return logging.getLogger("TradingBot")
