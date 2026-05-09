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

def find_my_money():
    print("🔍 جاري فحص جميع العملات في جميع المحافظ للعثور على رصيدك...")
    
    # Spot Client
    spot_exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    # Futures Client
    futures_exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "future"}
    })

    print("\n--- 💼 المحفظة الفورية (Spot) ---")
    try:
        spot_balance = spot_exchange.fetch_balance()
        found_spot = False
        for currency, data in spot_balance.get("total", {}).items():
            if data and float(data) > 0:
                print(f"  💰 {currency}: {float(data)}")
                found_spot = True
        if not found_spot:
            print("  لا توجد أي عملات في هذه المحفظة.")
    except Exception as e:
        print(f"❌ خطأ: {e}")

    print("\n--- 📈 العقود الآجلة (Futures USD-M) ---")
    try:
        futures_balance = futures_exchange.fetch_balance()
        found_futures = False
        for currency, data in futures_balance.get("total", {}).items():
            if data and float(data) > 0:
                print(f"  💰 {currency}: {float(data)}")
                found_futures = True
        if not found_futures:
            print("  لا توجد أي عملات في هذه المحفظة.")
    except Exception as e:
        print(f"❌ خطأ: {e}")

    print("\n--- 🏦 محفظة التمويل (Funding) ---")
    try:
        funding_balance = spot_exchange.sapiPostAssetGetFundingAsset()
        found_funding = False
        for item in funding_balance:
            amount = float(item.get("free", 0.0)) + float(item.get("locked", 0.0)) + float(item.get("freeze", 0.0))
            if amount > 0:
                asset = item.get("asset")
                print(f"  💰 {asset}: {amount}")
                found_funding = True
        if not found_funding:
            print("  لا توجد أي عملات في هذه المحفظة.")
    except Exception as e:
        print(f"❌ خطأ: {e}")

if __name__ == "__main__":
    find_my_money()
