"""
Test ticket creation functionality
"""

import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

# Test credentials (from seed data)
TEST_EMAIL = "john.smith@email.com"
TEST_PASSWORD = "password123"

def login():
    """Login and get auth token"""
    response = requests.post(
        f"{BASE_URL}/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Logged in as {data['user']['full_name']}")
        return data['access_token']
    else:
        print(f"✗ Login failed: {response.text}")
        return None

def test_ticket_query(token, query):
    """Test a query that should create a ticket"""
    print(f"\n📝 Testing query: '{query}'")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/rag-query",
        headers=headers,
        json={
            "query": query,
            "tone": "neutral",
            "k": 2,
            "conversation_history": [],
            "auto_detect_empathy": True,
            "include_explainability": True,
            "enable_safety_checks": True
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Response received")
        print(f"  Response: {data['response'][:100]}...")
        
        if data.get('ticket_created'):
            ticket = data['ticket_created']
            print(f"\n🎫 TICKET CREATED!")
            print(f"  Number: {ticket['ticket_number']}")
            print(f"  Title: {ticket['title']}")
            print(f"  Category: {ticket['category']}")
            print(f"  Priority: {ticket['priority']}")
            print(f"  Status: {ticket['status']}")
        else:
            print(f"  No ticket created (as expected for non-ticket queries)")
    else:
        print(f"✗ Query failed: {response.text}")

def main():
    print("=" * 60)
    print("Testing Ticket Creation Functionality")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        return
    
    # Test queries that SHOULD create tickets
    print("\n" + "=" * 60)
    print("Testing TICKET-WORTHY queries:")
    print("=" * 60)
    
    ticket_queries = [
        "I need to file a claim for a car accident that happened yesterday",
        "I want to apply for insurance claim for my damaged roof",
        "Can I file a claim? My car was hit in the parking lot",
        "I'd like to request a policy change to increase my coverage",
        "I have a billing issue with my last payment"
    ]
    
    for query in ticket_queries:
        test_ticket_query(token, query)
    
    # Test queries that should NOT create tickets
    print("\n" + "=" * 60)
    print("Testing NON-TICKET queries (for comparison):")
    print("=" * 60)
    
    info_queries = [
        "What does my policy cover?",
        "How much is my deductible?",
        "Can you explain collision coverage to me?"
    ]
    
    for query in info_queries:
        test_ticket_query(token, query)
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
