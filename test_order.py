import asyncio
from binance_client import BinanceClient
from execution_engine import ExecutionEngine
from database import Database
from config import Config

class MockRisk:
    def can_open_trade(self, pair): return {"allowed": True, "reason": ""}
    def calculate_dynamic_position(self, price, score): return {"amount": 5.0 / price, "stop_loss": price*0.99, "take_profit": price*1.01}

client = BinanceClient()
db = Database()
print("Balance:", client.get_usdt_balance())

# Try creating an order with $5
ticker = client.fetch_ticker("FTM/USDT")
price = ticker["last"]
amount = 10.0 / price  # Trying to buy $10 worth of FTM

print(f"Attempting to buy 10 USDT worth of FTM/USDT at {price}. Amount: {amount}")
order = client.create_market_order("FTM/USDT", "BUY", amount)

if order:
    print("Success:", order.get("id"))
else:
    print("Failed to create order.")
