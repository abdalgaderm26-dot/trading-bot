from database import Database
db = Database()
db.init_db()
conn = db._get_connection()
cursor = conn.cursor()
cursor.execute("UPDATE trades SET status='CLOSED' WHERE status='OPEN'")
conn.commit()
print("All open trades marked as CLOSED.")
