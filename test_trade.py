"""
سكريبت تجريبي: تحقق من الرصيد وتنفيذ صفقة صغيرة
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import ccxt

# اتصال مباشر
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True
})

print("=" * 50)
print("🔍 فحص الرصيد والصفقة التجريبية")
print("=" * 50)

# 1. جلب الرصيد
try:
    balance = exchange.fetch_balance()
    usdt = float(balance['free'].get('USDT', 0))
    print(f"\n💰 رصيد USDT المتاح: {usdt:.2f}")
    
    # عرض كل العملات اللي فيها رصيد
    print("\n📊 جميع الأرصدة:")
    for coin, amount in balance['free'].items():
        if float(amount) > 0:
            print(f"   {coin}: {float(amount):.8f}")
    
    print(f"\n📐 حجم المخاطرة (1%): {usdt * 0.01:.2f} USDT")
    
except Exception as e:
    print(f"❌ خطأ في جلب الرصيد: {e}")
    usdt = 0

# 2. فحص الحد الأدنى للتداول
if usdt > 0:
    try:
        ticker = exchange.fetch_ticker('BTC/USDT')
        btc_price = ticker['last']
        print(f"\n📈 سعر BTC الحالي: {btc_price:.2f}")
        
        # حساب أقل كمية BTC ممكنة
        # الحد الأدنى في Binance عادة 10 USDT
        min_amount = 10 / btc_price  # أقل كمية
        risk_amount = usdt * 0.01    # 1% من الرصيد
        trade_amount = risk_amount / btc_price
        
        print(f"   أقل صفقة ممكنة: {min_amount:.8f} BTC ({10:.2f} USDT)")
        print(f"   حجم صفقة 1% مخاطرة: {trade_amount:.8f} BTC ({risk_amount:.2f} USDT)")
        
        if risk_amount < 10:
            print(f"\n⚠️ رصيدك ({usdt:.2f} USDT) منخفض!")
            print(f"   الحد الأدنى للصفقة في Binance: 10 USDT")
            print(f"   تحتاج رصيد 1000 USDT على الأقل لصفقة 1% = 10 USDT")
            
            if usdt >= 10:
                print(f"\n🔄 يمكن تنفيذ صفقة بالحد الأدنى (10 USDT)...")
                print(f"   هل تريد المتابعة؟ (سيتم الشراء بـ 10 USDT)")
            else:
                print(f"\n❌ الرصيد أقل من 10 USDT - لا يمكن التداول")
        else:
            print(f"\n✅ الرصيد كافٍ للتداول!")
            
    except Exception as e:
        print(f"❌ خطأ: {e}")
else:
    print("\n❌ لا يوجد رصيد USDT")

print("\n" + "=" * 50)
