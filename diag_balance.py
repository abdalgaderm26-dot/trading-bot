import socket

# Force IPv4 Resolution
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import ccxt
import os
from dotenv import load_dotenv

load_dotenv()

def verify_and_prepare():
    print("🔍 جاري فحص الرصيد في جميع المحافظ (Spot, Funding, Futures)...")
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    total_usdt = 0.0

    # 1. Check Funding
    funding_usdt = 0.0
    try:
        # ccxt binance funding balance
        funding_balance = exchange.sapiPostAssetGetFundingAsset({"asset": "USDT"})
        if funding_balance:
            funding_usdt = float(funding_balance[0].get("free", 0.0))
        print(f"🏦 محفظة التمويل (Funding): {funding_usdt:.2f} USDT")
        total_usdt += funding_usdt
    except Exception as e:
        print(f"❌ خطأ في فحص Funding: {e}")

    # 2. Check Spot
    spot_usdt = 0.0
    try:
        spot_balance = exchange.fetch_balance()
        spot_usdt = float(spot_balance.get("free", {}).get("USDT", 0.0))
        print(f"💼 المحفظة الفورية (Spot): {spot_usdt:.2f} USDT")
        total_usdt += spot_usdt
    except Exception as e:
        print(f"❌ خطأ في فحص Spot: {e}")

    # 3. Check Futures
    futures_usdt = 0.0
    try:
        # switch default type to future to get correct balances
        futures_exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_API_SECRET"),
            "enableRateLimit": True,
            "options": {"defaultType": "future"}
        })
        futures_balance = futures_exchange.fetch_balance()
        futures_usdt = float(futures_balance.get("free", {}).get("USDT", 0.0))
        print(f"📈 العقود الآجلة (Futures): {futures_usdt:.2f} USDT")
        total_usdt += futures_usdt
    except Exception as e:
        print(f"❌ خطأ في فحص Futures: {e}")

    print(f"\n💰 إجمالي الـ USDT المتاح: {total_usdt:.2f} USDT")

    if total_usdt == 0:
         print("⚠️ الحساب لا يحتوي على أي رصيد USDT حالياً.")
         return

    # Movement Logic
    print("\n🔄 جاري تجميع الأموال في العقود الآجلة (Futures)...")
    if funding_usdt > 0:
        try:
            print(f"  - تحويل {funding_usdt} من Funding إلى Spot...")
            exchange.transfer("USDT", funding_usdt, "funding", "spot")
            spot_usdt += funding_usdt
            funding_usdt = 0
            print("  ✅ تم.")
        except Exception as e:
            print(f"  ❌ فشل: {e}")
            
    if spot_usdt > 0:
        try:
            print(f"  - تحويل {spot_usdt} من Spot إلى Futures...")
            exchange.transfer("USDT", spot_usdt, "spot", "umfuture")
            futures_usdt += spot_usdt
            spot_usdt = 0
            print("  ✅ تم التحويل بنجاح! الرصيد جاهز في العقود الآجلة.")
        except BaseException as e:
            print(f"  ❌ فشل: {e}")

if __name__ == "__main__":
    verify_and_prepare()
