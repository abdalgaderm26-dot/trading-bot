import ccxt
import os
import time
from dotenv import load_dotenv

load_dotenv()

def revert_funds_to_spot():
    print("⚠️ بدء عملية قراءة الأرصدة وإعادة التحويل إلى الحساب الفوري (Spot)...")
    
    try:
        exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_API_SECRET"),
            "enableRateLimit": True
        })
        
        # 1. Fetch Futures Balance
        futures_balance = exchange.fetch_balance(params={'type': 'future'})
        futures_usdt = float(futures_balance.get("free", {}).get("USDT", 0.0))
        print(f"📈 الرصيد الحالي المتاح في الفيوتشرز: {futures_usdt:.2f} USDT")
        
        if futures_usdt > 1.0:
            transfer_amount = futures_usdt
            print(f"🔄 جاري تحويل {transfer_amount:.2f} USDT من Futures إلى Spot...")
            
            # Execute internal transfer
            # fromAccount='umfuture', toAccount='spot'
            result = exchange.transfer("USDT", transfer_amount, "umfuture", "spot")
            print(f"✅ تم الإرجاع بنجاح! رقم العملية: {result.get('id', 'N/A')}")
            
            # Verify new spot balance
            time.sleep(2)
            new_spot_balance = exchange.fetch_balance(params={'type': 'spot'})
            new_spot_usdt = float(new_spot_balance.get("free", {}).get("USDT", 0.0))
            print(f"🎉 الرصيد الجديد في السبوت أصبح: {new_spot_usdt:.2f} USDT. البوت سيعود للتداول الفوري!")
        else:
            print("✅ لا يوجد رصيد كافي للتحويل في الفيوتشرز، يبدو أنه تم تحويله يدوياً أو الرصيد صفر.")
                
    except Exception as e:
        print(f"❌ فشل عملية التحويل العكسي! الخطأ: {e}")

if __name__ == "__main__":
    revert_funds_to_spot()
