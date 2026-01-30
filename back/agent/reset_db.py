import sqlite3
import os

# Point this to your actual DB file
DB_PATH = os.path.join("data", "memory.db") 

def clean_zombies():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    try:
        # 1. Drop the zombie table
        cur.execute("DROP TABLE IF EXISTS daily_emotion_stats")
        print("✅ Deleted zombie table 'daily_emotion_stats'")
        
        # 2. Check what's left
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cur.fetchall()
        print("\nYour Active Tables:")
        for t in tables:
            print(f" - {t[0]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        con.commit()
        con.close()

if __name__ == "__main__":
    clean_zombies()