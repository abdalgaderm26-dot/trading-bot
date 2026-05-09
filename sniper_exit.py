import time
import os
import ccxt
import pandas as pd
from dotenv import load_dotenv
from database import Database

load_dotenv()

def calc_rsi(series, period=14):
    delta = series.diff()
    up, down = delta.copy(), delta.copy()
    up[up < 0] = 0
    down[down > 0] = 0
    roll_up1 = up.ewm(span=period).mean()
    roll_down1 = down.abs().ewm(span=period).mean()
    RS1 = roll_up1 / roll_down1
    RSI1 = 100.0 - (100.0 / (1.0 + RS1))
    return RSI1.iloc[-1]

def sniper_exit_open_trades():
    print("🎯 تهيئة قناص الخروج (Sniper Exit Protocol)...")
    
    db = Database()
    conn = db._get_connection()
    c = conn.cursor(dictionary=True)
    c.execute("SELECT id, symbol, quantity, entry_price FROM trades WHERE status='OPEN'")
    open_trades = c.fetchall()
    
    if not open_trades:
        print("✅ لا توجد صفقات مفتوحة ليتم قنصها للهروب!")
        return
        
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    print(f"👀 جاري مراقبة الحركة اللحظية لـ {len(open_trades)} صفقات مفتوحة لاقتناص أقرب قمة وصغيرة والهروب...")
    
    while True:
        try:
            for t in open_trades:
                trade_id = t["id"]
                pair = t["symbol"]
                amount = float(t["quantity"])
                entry = float(t["entry_price"])
                
                # Fetch 1m candles for microscopic momentum
                ohlcv = exchange.fetch_ohlcv(pair, timeframe='1m', limit=20)
                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                current_price = df['close'].iloc[-1]
                rsi = calc_rsi(df['close'], period=14)
                
                loss_pct = ((current_price - entry) / entry) * 100
                
                print(f"📊 {pair} | السعر: {current_price:.8f} | الخسارة: {loss_pct:.2f}% | قوة الشراء اللحظية RSI: {rsi:.1f}")
                
                # Sniper Rule: If RSI pushes above 60 (mini-pump) and then starts weakening, OR if loss exceeds a hard stop of -1.5% to prevent total ruin.
                # Assuming the user wants out NOW but on a slight uptick.
                
                if rsi > 55 or loss_pct > -0.2:
                    print(f"🔥 فرصة قنص! السعر صعد قليلاً أو الـ RSI قوي (انتهى الهبوط مؤقتاً). جاري الهروب الآن لعملة {pair}!")
                    
                    try:
                        order = exchange.create_order(symbol=pair, type="market", side="sell", amount=amount)
                        print(f"✅ تم الهروب بنجاح وتقليل الخسائر للأمر {order['id']}")
                        c.execute("UPDATE trades SET status='CLOSED', close_reason='SNIPER_EMERGENCY_EXIT', exit_price=%s, closed_at=NOW() WHERE id=%s", (current_price, trade_id))
                        conn.commit()
                        return # Exit script once done
                    except Exception as e:
                        print(f"❌ فشل التنفيذ. ربما الرصيد غير متاح: {e}")
                        c.execute("UPDATE trades SET status='CLOSED', close_reason='SNIPER_FAILED_ZERO_BAL', closed_at=NOW() WHERE id=%s", (trade_id,))
                        conn.commit()
                        return

            time.sleep(10) # check every 10 seconds
            
        except Exception as e:
            print(f"⚠️ خطأ أثناء المراقبة: {e}")
            time.sleep(5)

if __name__ == "__main__":
    sniper_exit_open_trades()
