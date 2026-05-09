import os
from dotenv import load_dotenv
import ccxt

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

print("Connecting to Binance to check ALL balances...\n")

try:
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    balance = exchange.fetch_balance()
    
    print("-" * 30)
    print("SPOT WALLET BALANCES (> 0):")
    for currency, amount in balance['free'].items():
        if amount > 0:
            print(f"- {currency}: {amount} (Free/Available)")
    
    for currency, amount in balance['used'].items():
        if amount > 0:
            print(f"- {currency}: {amount} (Used/Locked in Orders)")

    print("-" * 30)
    
except Exception as e:
    print(f"Error fetching balance: {e}")
