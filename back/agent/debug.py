import os
import sys

print("\n--- 🕵️ DEBUGGING FOLDER STRUCTURE ---")
current_dir = os.getcwd()
print(f"1. You are running this command from: {current_dir}")

# Check if 'analytics' exists here
analytics_path = os.path.join(current_dir, "analytics")
services_path = os.path.join(current_dir, "services")

print(f"\n2. Looking for 'analytics' folder at: {analytics_path}")
if os.path.exists(analytics_path) and os.path.isdir(analytics_path):
    print("   ✅ FOUND! The folder exists here.")
    print(f"   Contents: {os.listdir(analytics_path)}")
else:
    print("   ❌ NOT FOUND here.")

# Check if it's accidentally inside services
analytics_in_services = os.path.join(services_path, "analytics")
if os.path.exists(analytics_in_services):
    print(f"\n⚠️ WARNING: I found 'analytics' inside 'services' instead! ({analytics_in_services})")
    print("   👉 FIX: You need to move the 'analytics' folder OUT of 'services' and into the root 'agent' folder.")

print("\n3. Checking 'services' folder:")
if os.path.exists(services_path):
    print(f"   Contents of services: {os.listdir(services_path)}")
else:
    print("   ❌ Services folder not found.")

print("\n--- END DEBUG ---\n")