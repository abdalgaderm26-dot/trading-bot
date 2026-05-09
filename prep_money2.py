import socket

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

def sweep_dust():
    print("🧹 جاري تحويل كل فتات العملات إلى BNB ثم إلى USDT...")
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    try:
        # Get dust eligible assets
        balances = exchange.fetch_balance()
        dust_assets = []
        for currency, data in balances.get("total", {}).items():
            amount = float(data)
            if amount > 0 and currency not in ["USDT", "BNB"]:
                dust_assets.append(currency)
        
        if dust_assets:
            print(f"  - تم العثور على {len(dust_assets)} عملة صغيرة لتحويلها...")
            # Binance allows max 15 assets per request, let's chunk it.
            def chunks(lst, n):
                for i in range(0, len(lst), n):
                    yield lst[i:i + n]
                    
            for chunk in chunks(dust_assets, 10):
                print(f"  - تحويل الدفعة: {', '.join(chunk)}")
                try:
                    res = exchange.sapiPostAssetDust({'asset': chunk})
                    print("    ✅ نجاح.")
                except Exception as e:
                    print(f"    ❌ خطأ في هذه الدفعة: {e}")
        else:
             print("  لا توجد عملات صغيرة (فتات) للتحويل.")
             
        # Now we have BNB, let's sell it to USDT
        balances = exchange.fetch_balance()
        bnb_balance = float(balances.get("free", {}).get("BNB", 0.0))
        if bnb_balance > 0.005:  # Binance minimum notional for BNB/USDT is ~5 USDT
            print(f"\n🪙 الرصيد الحالي من BNB هو {bnb_balance}. جاري بيعه للحصول على USDT...")
            try:
                order = exchange.create_market_sell_order("BNB/USDT", bnb_balance)
                print("  ✅ تم بيع الـ BNB بنجاح!")
            except Exception as e:
                print(f"  ❌ فشل في بيع الـ BNB: {e}")
        else:
            print(f"\n🪙 رصيد الـ BNB الحالي {bnb_balance} وهو أقل من الحد الأدنى للبيع المباشر (يحتاج تقريباً 0.009).")
        
        # Finally Transfer USDT to UM-Futures
        balances = exchange.fetch_balance()
        spot_usdt = float(balances.get("free", {}).get("USDT", 0.0))
        if spot_usdt > 0:
            print(f"\n🔄 تحويل {spot_usdt} USDT إلى العقود الآجلة (Futures)...")
            try:
                exchange.transfer("USDT", spot_usdt, "spot", "umfuture")
                print("  ✅ تم التحويل بنجاح! البوت جاهز تماماً.")
            except Exception as e:
                print(f"  ❌ فشل في نقل الـ USDT للفيوتشرز: {e}")
                
    except Exception as e:
         print(f"❌ خطأ عام: {e}")

if __name__ == "__main__":
    sweep_dust()
