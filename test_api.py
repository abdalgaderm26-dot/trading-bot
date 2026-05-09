import os
from dotenv import load_dotenv
import ccxt

load_dotenv()

api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

try:
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    # Try fetching balance
    balance = exchange.fetch_balance()
    usdt_balance = balance.get('USDT', {}).get('free', 0)
    print(f"SUCCESS! Connection working. USDT Balance: {usdt_balance}")
except Exception as e:
    print(f"ERROR: {e}")
