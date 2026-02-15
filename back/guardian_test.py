import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
PARENT_ID = "user_004"  # Sophia (Parent)
CHILD_ID = "user_001"   # You (Child)

def test_guardian_dashboard():
    print(f"🕵️‍♀️ PARENT ({PARENT_ID}) CHECKING DASHBOARD...\n")
    
    # The endpoint expects a query param 'user_id' for the *Guardian* # (In a real app, this would be taken from the Auth Token)
    url = f"{BASE_URL}/api/guardian/dashboard?user_id={PARENT_ID}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS! Dashboard Data Retrieved:\n")
            
            # 1. Check Ward Info
            print(f"👶 Ward (Child): {data.get('ward_id', 'Unknown')}")
            
            # 2. Check Emotion Summary
            summary = data.get('summary', {})
            print(f"📊 Today's Mood: {summary.get('dominant_emotion', 'N/A')}")
            
            # 3. Check Recent Alerts/Logs
            logs = data.get('recent_logs', [])
            print(f"\n📝 Recent Activity ({len(logs)} records):")
            for log in logs[:3]:  # Show top 3
                print(f"   - {log['timestamp']}: {log['emotion']} ({log['confidence']}%)")
                
            # 4. Check Weekly Stats (from mock data)
            stats = data.get('weekly_stats', [])
            print(f"\n📈 Weekly Trend ({len(stats)} days):")
            for day in stats:
                print(f"   - {day['date']}: {day['dominant_emotion']}")

        else:
            print(f"❌ FAILED: {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ CONNECTION ERROR: Is the server running? ({e})")

if __name__ == "__main__":
    test_guardian_dashboard()