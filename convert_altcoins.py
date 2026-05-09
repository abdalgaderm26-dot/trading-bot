import os
import sys
import time
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import ccxt

exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True
})

print("==================================================")
print("🔄 محاولة تحويل كل العملات إلى USDT")
print("==================================================")

try:
    markets = exchange.load_markets()
    balance = exchange.fetch_balance()
    
    total_usdt_sold = 0
    converted_coins = []
    failed_coins = []
    earn_coins = []
    dust_coins = []

    for coin, amount in balance['free'].items():
        if coin == 'USDT' or float(amount) <= 0:
            continue
            
        # Assets starting with LD are Binance Simple Earn (locked/savings)
        if coin.startswith('LD'):
            earn_coins.append(coin)
            continue
            
        symbol = f"{coin}/USDT"
        
        # Check if the market exists
        if symbol not in markets:
            failed_coins.append((coin, "السوق غير متوفر"))
            continue
            
        try:
            # Fetch current price
            ticker = exchange.fetch_ticker(symbol)
            price = ticker['last']
            value_in_usdt = float(amount) * price
            
            # Binance minimum trade limit is typically 10 USDT
            if value_in_usdt < 10:
                dust_coins.append((coin, value_in_usdt))
                continue
                
            print(f"⏳ محاولة بيع {amount} {coin} (~{value_in_usdt:.2f} USDT)...")
            
            # Market sell
            order = exchange.create_market_sell_order(symbol, amount)
            print(f"✅ تم بيع {coin} بنجاح!")
            total_usdt_sold += value_in_usdt
            converted_coins.append(coin)
            time.sleep(1) # rate limit
            
        except Exception as e:
            failed_coins.append((coin, str(e)))

    print("\n" + "=" * 50)
    print("📊 ملخص عملية التحويل:")
    print("=" * 50)
    
    if converted_coins:
        print(f"✅ العملات التي تم تحويلها: {', '.join(converted_coins)}")
        print(f"💰 إجمالي USDT المكتسب: ~{total_usdt_sold:.2f} USDT")
    else:
        print("ℹ️ لم يتم تحويل أي عملات إلى USDT.")
        
    if earn_coins:
        print("\n⚠️ عملات Binance Earn (تحتاج سحب يدوي من التطبيق قبل البيع):")
        print(f"   {', '.join(earn_coins)}")
        
    if dust_coins:
        print("\n⚠️ عملات 'Dust' (أقل من الحد الأدنى 10 USDT، استخدم زر 'Convert to BNB' في التطبيق):")
        for c, v in dust_coins:
            print(f"   - {c}: قيمتها ~{v:.2f} USDT")
            
    if failed_coins:
        print("\n❌ عملات فشل تحويلها:")
        for c, err in failed_coins:
            print(f"   - {c}: {err}")

except Exception as e:
    print(f"❌ حدث خطأ رئيسي: {e}")

print("==================================================")
