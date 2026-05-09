import ccxt
import os
import time
from dotenv import load_dotenv
from database import Database

load_dotenv()

def force_close_all_futures():
    print("⚠️ بدء بروتوكول تصفية حساب العقود الآجلة (Futures Liquidation)...")
    
    try:
        exchange = ccxt.binance({
            "apiKey": os.getenv("BINANCE_API_KEY"),
            "secret": os.getenv("BINANCE_API_SECRET"),
            "enableRateLimit": True,
            "options": {"defaultType": "future"}
        })
        
        # 1. Close Open Positions
        positions = exchange.fetch_positions()
        for pos in positions:
            symbol = pos['symbol']
            contract_size = float(pos['contracts'])
            side = pos['side']
            
            if contract_size > 0:
                print(f"🚨 وجدنا صفقة فيوتشرز مفتوحة ({side}) للعملة {symbol} بحجم {contract_size}! جاري التصفية...")
                order_side = "sell" if side == "long" else "buy"
                
                try:
                    order = exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=order_side,
                        amount=contract_size,
                        params={'reduceOnly': True}
                    )
                    print(f"✅ تم تصفية الصفقة وإغلاق المشتت! النتيجة: {order['id']}")
                except Exception as e:
                    print(f"❌ فشل تصفية الصفقة {symbol} (ربما الحجم صغير جداً). الخطأ: {e}")
                    
        # 2. Cancel Open Orders
        try:
            exchange.cancel_all_orders()
            print("✅ تم إلغاء جميع الأوامر المعلقة (Limit/Stop).")
        except Exception as e:
            print(f"⚠️ ملاحظة حول الأوامر: {e}")

        # 3. Sweep Remaining Margin to Spot
        time.sleep(2)
        futures_balance = exchange.fetch_balance(params={'type': 'future'})
        futures_usdt = float(futures_balance.get("free", {}).get("USDT", 0.0))
        if futures_usdt > 1.0:
            print(f"🔄 جاري سحب الهامش المحرر ({futures_usdt:.2f} USDT) إلى الـ Spot...")
            exchange.transfer("USDT", futures_usdt, "umfuture", "spot")
            print("✅ اكتمل سحب جميع الأرصدة بنجاح!")
        else:
            print("✅ لا توجد أرصدة عالقة أو أن الرصيد المتبقي أقل من 1 USDT.")
            
        # 4. Clean Database
        db = Database()
        conn = db._get_connection()
        c = conn.cursor()
        c.execute("UPDATE trades SET status='CLOSED', close_reason='FUTURES_ABANDONED', closed_at=NOW() WHERE status='OPEN'")
        conn.commit()
        print("✅ تم تخليص قاعدة البيانات من أي صفقات عالقة بنجاح.")
        c.close()
        conn.close()

    except Exception as e:
        print(f"❌ خطأ عام أثناء التصفية: {e}")

if __name__ == "__main__":
    force_close_all_futures()
