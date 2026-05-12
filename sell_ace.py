"""بيع ACE وتحويلها لـ USDT"""
import socket
_orig = socket.getaddrinfo
def _ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4

import ccxt, os, sys
from dotenv import load_dotenv
load_dotenv()

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

exchange = ccxt.binance({
    "apiKey": os.getenv("BINANCE_API_KEY"),
    "secret": os.getenv("BINANCE_API_SECRET"),
    "enableRateLimit": True,
})

# جلب رصيد ACE
balance = exchange.fetch_balance()
ace_free = float(balance.get("ACE", {}).get("free", 0))
print(f"💰 رصيد ACE: {ace_free}")

if ace_free <= 0:
    print("❌ لا يوجد رصيد ACE للبيع")
    exit()

# جلب السعر الحالي
ticker = exchange.fetch_ticker("ACE/USDT")
price = float(ticker["last"])
value = ace_free * price
print(f"📊 السعر الحالي: ${price}")
print(f"💵 القيمة التقريبية: ${value:.2f}")

# تطبيع الكمية حسب قواعد Binance
market = exchange.market("ACE/USDT")
amount = exchange.amount_to_precision("ACE/USDT", ace_free * 0.999)  # buffer صغير
amount = float(amount)

if amount * price < 5:
    print(f"❌ القيمة أقل من الحد الأدنى ($5): ${amount * price:.2f}")
    exit()

print(f"🔄 جاري بيع {amount} ACE...")
order = exchange.create_market_sell_order("ACE/USDT", amount)
filled = float(order.get("filled", 0))
avg_price = float(order.get("average", price))
total_usdt = filled * avg_price
print(f"✅ تم البيع بنجاح!")
print(f"   الكمية: {filled} ACE")
print(f"   السعر: ${avg_price}")
print(f"   المبلغ: ${total_usdt:.2f} USDT")

# عرض الرصيد الجديد
new_balance = exchange.fetch_balance()
new_usdt = float(new_balance.get("USDT", {}).get("free", 0))
print(f"\n💰 رصيد USDT الجديد: ${new_usdt:.2f}")
