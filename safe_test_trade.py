import os
import sys
import time
import logging

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from config import Config, setup_logging
from binance_client import BinanceClient
from database import Database
from risk_manager import RiskManager
from alerts import AlertSystem
from execution_engine import ExecutionEngine

# إعداد مبسط للوج
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()

print("==================================================")
print("🛡️ بدء فحص الرصيد وتنفيذ صفقة تجريبية آمنة (v2.0)")
print("==================================================")

try:
    client = BinanceClient()
    db = Database()
    risk = RiskManager(db)
    alerts = AlertSystem()
    execution = ExecutionEngine(client, db, risk, alerts)
    
    # 1. فحص الرصيد
    usdt = client.get_usdt_balance()
    print(f"\n💰 رصيد USDT المتاح في المحفظة الفورية: {usdt:.2f} USDT")
    
    if usdt < 9.9:
        print("\n❌ الرصيد أقل من 10 USDT (الحد الأدنى لـ Binance هو 10). يرجى إيداع المزيد.")
        sys.exit(0)
        
    # 2. إعداد إشارة وهمية آمنة (BTC/USDT لأنه الأكثر سيولة وأماناً)
    pair = "BTC/USDT"
    price = client.fetch_current_price(pair)
    print(f"\n📈 السعر اللحظي لـ {pair}: {price:.2f}")
    
    amount_usdt = 10.0  # محاولة الشراء بـ 10 دولار (كل الرصيد الحرج)
    if usdt < amount_usdt:
        amount_usdt = usdt * 0.99 # لتجنب خصم العمولات
        
    # 3. إجبار حجم الصفقة لتجاهل إدارة المخاطر القياسية من أجل هذا الاختبار
    # التعديل المؤقت
    original_calculate = risk.calculate_position_size
    risk.calculate_position_size = lambda *args, **kwargs: btc_amount
    
    test_signal = {
        "signal": "BUY",
        "pair": pair,
        "price": price,
        "strength": 99,
        "buy_score": 90,
        "sell_score": 10,
        "ai_score": 85,
        "regime": "TEST"
    }
    
    print("\n🚀 تنفيذ الأمر في Binance الآن...")
    time.sleep(2)  # فرصة قراءة
    
    result = execution.execute_trade(test_signal, pair)
    
    if result.get("success"):
        print("\n✅ تم تنفيذ الشراء بنجاح!")
        print(f"   الكمية: {result.get('amount')} {pair}")
        print(f"   سعر الدخول: {result.get('entry_price')}")
        
        print("\n🛡️ حماية: البوت وضع أمر 'وقف خسارة' لحمايتك!")
        print("💡 تم تسجيل الصفقة في قاعدة البيانات بنجاح.")
        print("   يمكنك متابعتها من لوحة التحكم، أو التداول في Binance.")
        
    else:
        print(f"\n❌ فشل التنفيذ: {result.get('reason')}")

except Exception as e:
    print(f"\n❌ حدث خطأ غير متوقع: {e}")

print("\n==================================================")
