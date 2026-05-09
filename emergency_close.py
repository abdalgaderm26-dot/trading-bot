"""Emergency close all open spot trades NOW"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
import ccxt
import mysql.connector
from dotenv import load_dotenv
load_dotenv()

conn = mysql.connector.connect(host='localhost', user='root', password='', database='trading_bot')
c = conn.cursor(dictionary=True)
c.execute("SELECT id, symbol, quantity, entry_price FROM trades WHERE status='OPEN'")
trades = c.fetchall()

if not trades:
    print("[OK] No open trades")
else:
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    for t in trades:
        pair = t["symbol"]
        amount = float(t["quantity"])
        print(f"[CLOSING] {pair} amount={amount}")
        try:
            order = exchange.create_order(symbol=pair, type="market", side="sell", amount=amount)
            price = float(order.get("average", 0))
            entry = float(t["entry_price"])
            pnl = (price - entry) * amount
            pnl_pct = (price - entry) / entry * 100
            c.execute("UPDATE trades SET status='CLOSED', close_reason='EMERGENCY_EXIT', exit_price=%s, pnl=%s, pnl_pct=%s, closed_at=NOW() WHERE id=%s",
                      (price, pnl, pnl_pct, t["id"]))
            conn.commit()
            print(f"[DONE] Closed {pair} at {price} PnL={pnl:.4f} ({pnl_pct:.2f}%)")
        except Exception as e:
            print(f"[ERR] {pair}: {e}")
            c.execute("UPDATE trades SET status='CLOSED', close_reason='EMERGENCY_MANUAL', closed_at=NOW() WHERE id=%s", (t["id"],))
            conn.commit()
conn.close()
print("[COMPLETE]")
