import ccxt
import time
import os
from dotenv import load_dotenv
from database import Database

load_dotenv()

def force_close_spot_trades():
    print("⚠️ بدء تفريغ الصفقات المفتوحة (Spot) قبل الانتقال للفيوتشرز...")
    
    # Connect directly to Spot Binance
    exchange = ccxt.binance({
        "apiKey": os.getenv("BINANCE_API_KEY"),
        "secret": os.getenv("BINANCE_API_SECRET"),
        "enableRateLimit": True,
        "options": {"defaultType": "spot"}
    })
    
    db = Database()
    conn = db._get_connection()
    c = conn.cursor(dictionary=True)
    
    c.execute("SELECT id, symbol, quantity FROM trades WHERE status='OPEN'")
    open_trades = c.fetchall()
    
    if not open_trades:
        print("✅ لا توجد صفقات مفتوحة. الجو جاهز للانتقال.")
        return
        
    for t in open_trades:
        trade_id = t["id"]
        pair = t["symbol"]
        amount = float(t["quantity"])
        
        print(f"📌 وجدنا صفقة مفتوحة للعملة {pair} بكمية {amount} جاري الإغلاق...")
        try:
            # Execute Market Sell
            order = exchange.create_order(
                symbol=pair, 
                type="market", 
                side="sell", 
                amount=amount
            )
            print(f"✅ تم بيع العملة {pair} بنجاح! الأوردر: {order['id']}")
            
            # Close in DB
            c.execute("UPDATE trades SET status='CLOSED', close_reason='FUTURES_MIGRATION', closed_at=NOW() WHERE id=%s", (trade_id,))
            conn.commit()
            
        except Exception as e:
            print(f"❌ فشل البيع للعملة {pair}... ربما تم بيعها يدوياً أو ليس لها رصيد. يتم إغلاقها في قاعدة البيانات فقط. الخطأ: {e}")
            c.execute("UPDATE trades SET status='CLOSED', close_reason='F_MIG_MANUAL', closed_at=NOW() WHERE id=%s", (trade_id,))
            conn.commit()
            
    c.close()
    conn.close()
    print("✅ جميع مهام التنظيف انتهت. يمكن الآن تشغيل البوت وضع الفيوتشرز.")

if __name__ == "__main__":
    force_close_spot_trades()
