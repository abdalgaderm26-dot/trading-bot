"""reset_db.py - Clear all trading history tables for a fresh start"""
import mysql.connector, sys
sys.stdout.reconfigure(encoding='utf-8')
from config import Config

def reset_database():
    conn = mysql.connector.connect(
        host=Config.DB_HOST, port=Config.DB_PORT,
        user=Config.DB_USER, password=Config.DB_PASSWORD,
        database=Config.DB_NAME
    )
    c = conn.cursor()
    c.execute("SET FOREIGN_KEY_CHECKS = 0")
    for table in ["trades", "bot_stats", "trade_signals", "daily_summary"]:
        try:
            c.execute(f"TRUNCATE TABLE `{table}`")
            print(f"[OK] Cleared: {table}")
        except Exception:
            print(f"[SKIP] Table not found: {table}")
    c.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    c.close()
    conn.close()
    print("[DONE] Database reset complete. Bot starts fresh!")

if __name__ == "__main__":
    reset_database()
