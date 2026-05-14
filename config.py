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
    
    # ✅ تثبيت على Spot - لا يقرأ من البيئة لتجنب تحويل خاطئ لـ Futures
    ENABLE_FUTURES = False
    FUTURES_LEVERAGE = int(os.getenv("FUTURES_LEVERAGE", "3"))
    FUTURES_MARGIN_MODE = "isolated"
    FUTURES_SERVER_SL = os.getenv("FUTURES_SERVER_SL", "true").lower() == "true"
    FUTURES_SERVER_TP = os.getenv("FUTURES_SERVER_TP", "true").lower() == "true"
    FUTURES_MIN_SCORE = int(os.getenv("FUTURES_MIN_SCORE", "70"))
    AUTO_TRANSFER_SPOT_TO_FUTURES = os.getenv("AUTO_TRANSFER_SPOT_TO_FUTURES", "false").lower() == "true"

    # ──────────────── Trading Pairs (120+ عملة عالية السيولة) ────────────────
    # Blue Chips + Meme + AI + Layer1/2 + DeFi + Gaming + Infrastructure
    # ✅ أسماء Spot الصحيحة (بدون 1000 prefix الخاص بـ Futures)
    TRADING_PAIRS = [
        # ═══ Blue Chips (أقوى العملات وأعلى سيولة) ═══
        "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
        "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
        "TRX/USDT", "TON/USDT", "POL/USDT", "LTC/USDT", "BCH/USDT",
        "ATOM/USDT", "UNI/USDT", "FIL/USDT", "ETC/USDT", "HBAR/USDT",

        # ═══ Meme Coins (أسماء Spot الصحيحة!) ═══
        "PEPE/USDT", "SHIB/USDT", "FLOKI/USDT", "BONK/USDT",
        "WIF/USDT", "MEME/USDT", "BOME/USDT", "NOT/USDT",
        "PEOPLE/USDT", "TURBO/USDT", "LUNC/USDT",

        # ═══ AI & Data ═══
        "FET/USDT", "RENDER/USDT", "WLD/USDT", "TAO/USDT", "ARKM/USDT",
        "GRT/USDT",

        # ═══ Layer 1 ═══
        "SUI/USDT", "SEI/USDT", "APT/USDT", "NEAR/USDT", "INJ/USDT",
        "TIA/USDT", "FTM/USDT", "ALGO/USDT", "ICP/USDT", "VET/USDT",
        "EGLD/USDT", "KAVA/USDT", "FLOW/USDT", "MINA/USDT", "CFX/USDT",
        "KAS/USDT", "CELO/USDT", "ROSE/USDT",

        # ═══ Layer 2 & Scaling ═══
        "OP/USDT", "ARB/USDT", "STRK/USDT", "IMX/USDT", "MANTA/USDT",
        "SKL/USDT",

        # ═══ DeFi ═══
        "AAVE/USDT", "MKR/USDT", "CRV/USDT", "COMP/USDT", "SNX/USDT",
        "LDO/USDT", "PENDLE/USDT", "DYDX/USDT", "SUSHI/USDT",
        "1INCH/USDT", "RUNE/USDT", "JUP/USDT",
        "ONDO/USDT", "ENA/USDT",

        # ═══ Gaming & Metaverse ═══
        "GALA/USDT", "AXS/USDT", "SAND/USDT", "MANA/USDT", "ENJ/USDT",
        "PIXEL/USDT",

        # ═══ Infrastructure & Utility ═══
        "STX/USDT", "ORDI/USDT", "CHZ/USDT", "ENS/USDT",
        "W/USDT", "OM/USDT", "JTO/USDT", "PYTH/USDT",
        "ANKR/USDT", "BAND/USDT", "ZRO/USDT",
        "CKB/USDT", "THETA/USDT", "IOTA/USDT", "ZIL/USDT",
        "ONE/USDT", "HOT/USDT", "RSR/USDT",
        "MASK/USDT", "SSV/USDT", "GMX/USDT",
        "WOO/USDT", "BLUR/USDT", "ID/USDT",
    ]
    DEFAULT_PAIR = "BTC/USDT"
    TIMEFRAME = "15m"  # ✅ إطار 15 دقيقة - أوضح وأقل ضوضاء من 5m

    # ──────────────── Quick Scan (Trend Pullback Sniper) ────────────────
    QUICK_SCAN_TOP_N = 20          # فقط أفضل 20 عملة تحصل على تحليل عميق
    QUICK_SCAN_MIN_VOLUME_RATIO = 1.0  # حجم أعلى من المتوسط
    QUICK_SCAN_TREND_EMA = 20      # EMA20 لكشف الاتجاه السريع

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
    AI_SCORE_THRESHOLD = 65  # ✅ لا تدخل إلا بثقة AI عالية
    MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "trade_model.pkl")
    TRAINING_DATA_SIZE = 500  # عدد الشموع للتدريب

    # ──────────────── Risk Management (احترافي - يحسب العمولات) ────────────────
    # عمولة بينانس الحقيقية: 0.1% شراء + 0.1% بيع = 0.2% ذهاباً وإياباً
    EXCHANGE_FEE_PCT = 0.002  # 0.2% عمولة كاملة (شراء + بيع) - تُخصم من كل حساب ربح
    RISK_PER_TRADE = 0.15    # 15% من الرصيد لكل صفقة - حماية 85% من رأس المال
    STOP_LOSS_PCT = 0.015    # ✅ وقف خسارة عند -1.5% + خروج ذكي يحمي قبله
    TAKE_PROFIT_MIN = 0.010  # 1.0% هدف أول (صافي بعد العمولة = 0.8%)
    TAKE_PROFIT_MAX = 0.030  # 3.0% سقف ربح
    CLOSE_ON_MIN_PROFIT = True  # ✅ ثابت - لا يقرأ من البيئة
    MIN_PROFIT_CLOSE_PCT = 0.008  # ✅ 0.8% = ربح صافي 0.6% بعد العمولة (لا يقرأ من env!)
    # وضع القنص: يبحث عن عملات بداية صعود (وليس بعد الصعود)
    PUMP_FOCUS_MODE = False  # ✅ ثابت - معطل للأمان
    PUMP_MIN_3C_PCT = 0.008
    PUMP_MIN_5C_PCT = 0.012
    PUMP_VOLUME_RATIO_MIN = 1.5
    STEADY_UP_MIN_5C_PCT = 0.006
    STEADY_UP_MIN_GREEN_CANDLES = 3
    PUMP_SCORE_BONUS = 12   # ✅ ثابت 12 - لا يقرأ من env (كان 35 على Railway!)
    STEADY_SCORE_BONUS = 10  # ✅ ثابت 10
    PUMP_QUICK_EXIT_PCT = 0.008  # ✅ ثابت 0.8% - نفس MIN_PROFIT! (كان 0.3% على Railway = خسارة!)
    # وقف الخسارة الحقيقي: يبيع فوراً عند الوصول للحد
    EXIT_LOSS_ONLY_ON_HIGH_RISK = False  # ✅ معطل - وقف الخسارة يعمل دائماً
    HIGH_RISK_LOSS_PCT = 0.02  # ✅ ثابت 2%
    # تحويل تلقائي للعملات إلى USDT بعد الإغلاق
    AUTO_CONVERT_PROCEEDS_TO_USDT = os.getenv("AUTO_CONVERT_PROCEEDS_TO_USDT", "true").lower() == "true"
    AUTO_CONVERT_MIN_USDT_VALUE = float(os.getenv("AUTO_CONVERT_MIN_USDT_VALUE", "5.0"))
    AUTO_CONVERT_BUFFER_RATIO = float(os.getenv("AUTO_CONVERT_BUFFER_RATIO", "0.995"))
    DAILY_LOSS_LIMIT = 0.03  # إذا خسر 3% - يتوقف فوراً
    MAX_OPEN_TRADES = 3      # ✅ 3 صفقات لتنويع المخاطر
    ORDER_COOLDOWN = 180     # ✅ 3 دقائق بين الصفقات (يمنع إعادة الدخول السريع بعد وقف خسارة)
    MAX_CAPITAL_PER_TRADE = 0.15  # ✅ ثابت 15% - لا يقرأ من env! (Railway كان يضع 98%!)
    MIN_TRADE_NOTIONAL = 5.0
    BALANCE_CACHE_TTL = 8
    ORDER_BOOK_CACHE_SECONDS = 20

    # Spot inventory trading:
    # allows SELL signal to use existing base-asset balance (e.g. sell LTC in LTC/USDT)
    SPOT_INVENTORY_SELL_ENABLED = False  # ✅ معطل - لا نريد بيع في Spot Mode
    SPOT_INVENTORY_SELL_RATIO = 0.35

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
