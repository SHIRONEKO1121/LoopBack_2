
import requests
import time
import json

BASE_URL = "http://localhost:8000"

def test_grouping():
    print("\n--- 🧪 Testing AI Ticket Grouping ---")
    
    # 1. Create First Ticket (Base)
    t1 = {
        "query": "My wifi is not working, i cannot connect to the internet",
        "ai_draft": "Check router settings.",
        "status": "Pending"
    }
    r1 = requests.post(f"{BASE_URL}/tickets", json=t1)
    d1 = r1.json()
    print(f"Ticket 1 Created: {d1}")
    
    # 2. Create Second Ticket (Similar)
    print("Waiting for DB update...")
    time.sleep(1)
    t2 = {
        "query": "Internet connection is down, wifi shows no signal",
        "ai_draft": "Restart modem.",
        "status": "Pending"
    }
    r2 = requests.post(f"{BASE_URL}/tickets", json=t2)
    d2 = r2.json()
    print(f"Ticket 2 Created: {d2}")
    
    # 3. Create Third Ticket (Different)
    time.sleep(1)
    t3 = {
        "query": "My printer is jammed and flashing red light",
        "ai_draft": "Clear paper jam.",
        "status": "Pending"
    }
    r3 = requests.post(f"{BASE_URL}/tickets", json=t3)
    d3 = r3.json()
    print(f"Ticket 3 Created: {d3}")

    # Verify Logic
    g1 = d1.get('group_id')
    g2 = d2.get('group_id')
    g3 = d3.get('group_id')

    if g1 and g2 and g1 == g2:
        print("✅ PASS: Similar tickets grouped together.")
    else:
        print(f"❌ FAIL: Tickets 1 & 2 should be grouped. Got {g1} vs {g2}")

    if g3 and g1 != g3:
        print("✅ PASS: Different ticket has new group.")
    else:
        print(f"❌ FAIL: Ticket 3 wrongly grouped with Ticket 1. Got {g3} vs {g1}")

    # 4. Test Broadcast
    print("\n--- 📢 Testing Broadcast Solution ---")
    grp_id = g1
    print(f"Broadcasting to Group {grp_id} (Ticket ID: {d1.get('ticket_id')})...")
    
    res = requests.post(f"{BASE_URL}/broadcast", json={
        "ticket_id": d1.get('ticket_id'),
        "final_answer": "Global Wifi Fix Applied."
    })
    print(f"Broadcast Status: {res.json()}")
    
    # Verify updates
    all_tickets = requests.get(f"{BASE_URL}/tickets").json()
    
    t1_status = next(t for t in all_tickets if t['id'] == d1.get('ticket_id'))['status']
    t2_status = next(t for t in all_tickets if t['id'] == d2.get('ticket_id'))['status']
    t3_status = next(t for t in all_tickets if t['id'] == d3.get('ticket_id'))['status']
    
    if t1_status == "Resolved" and t2_status == "Resolved":
        print("✅ PASS: Both tickets in group Resolved.")
    else:
        print(f"❌ FAIL: Group broadcast failed. Statuses: T1={t1_status}, T2={t2_status}")

    if t3_status == "Pending":
         print("✅ PASS: Unrelated ticket remains Pending.")
    else:
         print("❌ FAIL: Unrelated ticket was swayed.")

if __name__ == "__main__":
    test_grouping()
