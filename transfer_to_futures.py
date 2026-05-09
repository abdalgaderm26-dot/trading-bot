import ccxt
import time
import os
from dotenv import load_dotenv

load_dotenv()

def transfer_funds():
    print("⚠️ بدء عملية قراءة الأرصدة والتحويل إلى حساب العقود الآجلة (Futures)...")
    
    try:
        exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_API_SECRET"),
            "enableRateLimit": True
        })
        
        # 1. Fetch Spot Balance
        spot_balance = exchange.fetch_balance(params={'type': 'spot'})
        spot_usdt = float(spot_balance.get("free", {}).get("USDT", 0.0))
        print(f"💼 الرصيد المتاح في المحفظة العادية (Spot): {spot_usdt:.2f} USDT")
        
        # 2. Fetch Futures Balance
        futures_balance = exchange.fetch_balance(params={'type': 'future'})
        futures_usdt = float(futures_balance.get("free", {}).get("USDT", 0.0))
        print(f"📈 الرصيد الحالي في محفظة العقود الآجلة (Futures): {futures_usdt:.2f} USDT")
        
        if spot_usdt > 1.0:
            transfer_amount = spot_usdt
            print(f"🔄 جاري تحويل {transfer_amount:.2f} USDT من Spot إلى Futures...")
            
            # Execute internal transfer
            # fromAccount='spot', toAccount='umfuture' (USD-M Futures)
            result = exchange.transfer("USDT", transfer_amount, "spot", "umfuture")
            print(f"✅ تم التحويل بنجاح! رقم العملية: {result.get('id', 'N/A')}")
            
            # Verify new futures balance
            time.sleep(2)
            new_futures_balance = exchange.fetch_balance(params={'type': 'future'})
            new_futures_usdt = float(new_futures_balance.get("free", {}).get("USDT", 0.0))
            print(f"🎉 الرصيد الجديد في الفيوتشرز أصبح: {new_futures_usdt:.2f} USDT. البوت جاهز للعمل!")
        else:
            if futures_usdt > 0:
                print("✅ يوجد رصيد بالفعل في الفيوتشرز، ولا يوجد رصيد إضافي في السبوت لنقله.")
            else:
                print("❌ لا يوجد رصيد USDT كافي في كلا المحفظتين لبدء التداول!")
                
    except Exception as e:
        print(f"❌ فشل عملية التحويل! الخطأ: {e}")
        print("💡 ملاحظة: قد تحتاج إلى تفعيل صلاحية 'Enable Futures' أو 'Enable Internal Transfer' لمفتاح الـ API في بينانس.")

if __name__ == "__main__":
    transfer_funds()
