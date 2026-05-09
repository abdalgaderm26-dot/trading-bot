import socket

_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import ccxt
import time
import os
from dotenv import load_dotenv

load_dotenv()

def prepare_money():
    print("🔄 جاري تجربة تجهيز الأموال أوتوماتيكياً...")
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    # 1. Transfer Funding -> Spot
    print("\n[1] نقل أموال محفظة التمويل إلى المحفظة الفورية...")
    try:
        funding_balance = exchange.sapiPostAssetGetFundingAsset()
        for item in funding_balance:
            amount = float(item.get("free", 0.0))
            asset = item.get("asset")
            if amount > 0:
                print(f"  - تحويل {amount} {asset} من Funding إلى Spot...")
                try:
                    exchange.transfer(asset, amount, "funding", "spot")
                except Exception as e:
                    print(f"    ❌ خطأ في نقل {asset}: {e}")
    except Exception as e:
         print(f"❌ خطأ في قراءة Funding: {e}")

    # 2. Redeem Simple Earn
    print("\n[2] استرجاع الأرصدة المحجوزة في أرباح بينانس (Simple Earn)...")
    try:
        positions = exchange.sapiGetSimpleEarnFlexiblePosition()
        rows = positions.get("rows", [])
        if not rows:
            print("  لا توجد أرصدة محجوزة في الأرباح المرنة.")
        for pos in rows:
            asset = pos.get("asset")
            product_id = pos.get("productId")
            amount = float(pos.get("totalAmount", 0.0))
            if amount > 0:
                print(f"  - استرجاع {amount} {asset} من أرباح بينانس...")
                try:
                    exchange.sapiPostSimpleEarnFlexibleRedeem({
                        "productId": product_id,
                        "redeemAll": True,
                    })
                    print("    ✅ تم استرجاع الكمية لـ Spot المحفظة الفورية.")
                except Exception as e:
                    print(f"    ❌ خطأ في الاسترجاع: {e}")
    except Exception as e:
        print(f"❌ خطأ في قراءة أرصدة Simple Earn: {e}")

if __name__ == "__main__":
    prepare_money()
