import sqlite3
import os
from datetime import datetime

# Path to your database
DB_PATH = os.path.join("data", "memory.db")

def check_database():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("\n" + "="*50)
    print("📊 RECENT EMOTION LOGS (Last 10)")
    print("="*50)
    
    try:
        cur.execute("""
            SELECT id, user_id, emotion, confidence, timestamp 
            FROM emotion_logs 
            ORDER BY id DESC LIMIT 10
        """)
        logs = cur.fetchall()
        
        if not logs:
            print("No data found in emotion_logs table.")
        else:
            print(f"{'ID':<4} | {'User':<10} | {'Emotion':<10} | {'Conf':<6} | {'Time'}")
            print("-" * 55)
            for row in logs:
                # Convert timestamp to readable time
                readable_time = datetime.fromtimestamp(row[4]).strftime('%H:%M:%S')
                print(f"{row[0]:<4} | {row[1]:<10} | {row[2]:<10} | {row[3]:<6.2f} | {readable_time}")

    except sqlite3.OperationalError as e:
        print(f"❌ Error reading emotion_logs: {e}")

    print("\n" + "="*50)
    print("📅 DAILY SUMMARIES")
    print("="*50)

    try:
        cur.execute("SELECT day, emotion, count FROM emotion_daily ORDER BY day DESC, count DESC LIMIT 10")
        summaries = cur.fetchall()
        if not summaries:
            print("No data found in emotion_daily table.")
        else:
            print(f"{'Day':<12} | {'Emotion':<10} | {'Count':<5}")
            print("-" * 35)
            for row in summaries:
                print(f"{row[0]:<12} | {row[1]:<10} | {row[2]:<5}")

    except sqlite3.OperationalError as e:
        print(f"❌ Error reading emotion_daily: {e}")

    conn.close()

if __name__ == "__main__":
    check_database()