import socket

# Force IPv4 Resolution to fix Binance IP Restriction Mismatch via IPv6
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

import ccxt
import time
import os
from dotenv import load_dotenv

load_dotenv()

def test_api():
    print("Testing Binance API Keys (Forced IPv4)...")
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True
    })
    
    print("\n1. Testing Spot Balance...")
    try:
        spot_balance = exchange.fetch_balance(params={'type': 'spot'})
        spot_usdt = float(spot_balance.get("free", {}).get("USDT", 0.0))
        print(f"✅ Spot API OK! USDT Balance: {spot_usdt}")
    except Exception as e:
        print(f"❌ Spot API FAILED: {e}")

    print("\n2. Testing Futures (USD-M) Balance...")
    try:
        futures_balance = exchange.fetch_balance(params={'type': 'future'})
        futures_usdt = float(futures_balance.get("free", {}).get("USDT", 0.0))
        print(f"✅ Futures API OK! USDT Balance: {futures_usdt}")
    except Exception as e:
        print(f"❌ Futures API FAILED: {e}")

if __name__ == "__main__":
    test_api()
