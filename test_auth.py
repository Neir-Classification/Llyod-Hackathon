"""
Quick test script for authentication endpoints.
Run backend first: python3 main.py or uvicorn main:app --reload
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_login():
    """Test login endpoint."""
    print("\n📝 Testing Login...")
    response = requests.post(f"{BASE_URL}/login", json={
        "email": "michael.johnson0@email.com",
        "password": "password123"
    })
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Login successful!")
        print(f"   User: {data['user']['full_name']} ({data['user']['email']})")
        print(f"   Token: {data['access_token'][:50]}...")
        return data['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   {response.text}")
        return None


def test_get_me(token):
    """Test /me endpoint."""
    print("\n👤 Testing Get Current User...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if response.status_code == 200:
        user = response.json()
        print("✅ User info retrieved!")
        print(f"   {user['full_name']} - {user['email']}")
        print(f"   Admin: {user['is_admin']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   {response.text}")


def test_get_policies(token):
    """Test /me/policies endpoint."""
    print("\n📋 Testing Get User Policies...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me/policies", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        policies = data['policies']
        print(f"✅ Found {len(policies)} policies!")
        for p in policies:
            print(f"   - {p['policy_type'].upper()}: {p['policy_number']} (${p['premium_amount']:.2f}/mo)")
    else:
        print(f"❌ Failed: {response.status_code}")


def test_get_tickets(token):
    """Test /me/tickets endpoint."""
    print("\n🎫 Testing Get User Tickets...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me/tickets", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        tickets = data['tickets']
        print(f"✅ Found {len(tickets)} tickets!")
        for t in tickets:
            print(f"   - {t['ticket_number']}: {t['title']} [{t['status']}]")
    else:
        print(f"❌ Failed: {response.status_code}")


def test_get_call_history(token):
    """Test /me/call-history endpoint."""
    print("\n📞 Testing Get Call History...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/me/call-history", headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        calls = data['call_history']
        print(f"✅ Found {len(calls)} call records!")
        for c in calls[:3]:  # Show first 3
            print(f"   - {c['topic']} ({c['sentiment']}) - {c['duration_seconds']}s")
    else:
        print(f"❌ Failed: {response.status_code}")


def test_admin_login():
    """Test admin login."""
    print("\n👑 Testing Admin Login...")
    response = requests.post(f"{BASE_URL}/login", json={
        "email": "admin1@insurance.com",
        "password": "admin123"
    })
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Admin login successful!")
        print(f"   Admin: {data['user']['full_name']}")
        print(f"   Is Admin: {data['user']['is_admin']}")
        return data['access_token']
    else:
        print(f"❌ Admin login failed: {response.status_code}")
        return None


def main():
    print("="*70)
    print("🧪 AUTHENTICATION ENDPOINTS TEST")
    print("="*70)
    print("\n⚠️  Make sure backend is running: python3 main.py")
    print("    or: uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    
    # Test regular user
    token = test_login()
    if token:
        test_get_me(token)
        test_get_policies(token)
        test_get_tickets(token)
        test_get_call_history(token)
    
    # Test admin user
    admin_token = test_admin_login()
    
    print("\n" + "="*70)
    print("✅ TESTS COMPLETE!")
    print("="*70)


if __name__ == "__main__":
    main()
