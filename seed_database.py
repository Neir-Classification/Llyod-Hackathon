"""
Seed database with pseudo/random user data for testing.
Run: python3 seed_database.py
"""

import random
from datetime import datetime, timedelta
from database import (
    init_db, SessionLocal, User, Policy, Ticket, CallSummary, AdminIntervention
)

# Sample data
FIRST_NAMES = ["John", "Jane", "Michael", "Emily", "David", "Sarah", "Robert", "Lisa", "James", "Maria", 
               "William", "Jennifer", "Richard", "Patricia", "Thomas", "Linda", "Charles", "Barbara"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", 
              "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor"]

POLICY_TYPES = ["auto", "home", "health", "life"]
TICKET_CATEGORIES = ["claim", "billing", "coverage_question", "complaint", "policy_change"]
PRIORITIES = ["low", "medium", "high", "urgent"]
SENTIMENTS = ["positive", "neutral", "negative", "anxious", "distressed"]

CALL_TOPICS = [
    "Policy coverage inquiry",
    "Claim status update",
    "Billing question",
    "Coverage limit clarification",
    "Premium payment issue",
    "Policy renewal discussion",
    "Accident claim filing",
    "Coverage exclusions",
    "Deductible questions",
    "Adding dependents to policy"
]

TICKET_TITLES = [
    "Claim denied - need clarification",
    "Incorrect billing amount charged",
    "Unable to understand coverage limits",
    "Request to increase coverage",
    "Policy cancellation inquiry",
    "Accident claim processing delay",
    "Missing payment confirmation",
    "Need help with policy documents",
    "Coverage for pre-existing condition",
    "Deductible seems too high"
]

CALL_SUMMARIES = [
    "Customer inquired about their auto insurance coverage limits for collision damage. Explained comprehensive vs collision coverage. Customer satisfied with explanation.",
    "User called regarding a recent accident. Filed claim #CLM-{}, provided guidance on next steps. User seemed anxious but reassured after explanation.",
    "Billing inquiry - customer noticed premium increase. Explained annual review process and factors affecting premium. Resolved satisfactorily.",
    "Customer confused about what's covered under home insurance. Walked through policy document highlights. Recommended scheduling detailed policy review.",
    "User reported suspicious charge on credit card. Verified legitimate premium payment. Customer relieved after confirmation.",
    "Health insurance coverage question regarding specialist visits. Explained in-network vs out-of-network benefits. Customer understood.",
    "Life insurance beneficiary update request. Guided through process and required documentation. Customer appreciative of help.",
    "Customer frustrated about claim processing time. Explained typical timeline and current status. Escalated to claims department for expedited review.",
    "Policy renewal discussion. Reviewed coverage options and potential premium changes. Customer requested time to consider options.",
    "Customer in distress after house fire. Immediately filed claim, explained emergency housing coverage. Scheduled adjuster visit. Provided emotional support."
]


def generate_users(db, num_users=20, num_admins=3):
    """Generate random users and admin users."""
    users = []
    
    # Create admin users
    print("Creating admin users...")
    for i in range(num_admins):
        admin = User(
            email=f"admin{i+1}@insurance.com",
            username=f"admin{i+1}",
            hashed_password=User.hash_password("admin123"),
            full_name=f"Admin {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            phone=f"+1-555-{random.randint(1000, 9999)}",
            is_active=True,
            is_admin=True
        )
        db.add(admin)
        users.append(admin)
    
    # Create regular users
    print(f"Creating {num_users} regular users...")
    for i in range(num_users):
        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        user = User(
            email=f"{first_name.lower()}.{last_name.lower()}{i}@email.com",
            username=f"{first_name.lower()}{last_name.lower()}{i}",
            hashed_password=User.hash_password("password123"),
            full_name=f"{first_name} {last_name}",
            phone=f"+1-555-{random.randint(1000, 9999)}",
            is_active=True,
            is_admin=False
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    print(f"✅ Created {len(users)} users ({num_admins} admins, {num_users} regular)")
    return users


def generate_policies(db, users):
    """Generate random policies for users."""
    policies = []
    regular_users = [u for u in users if not u.is_admin]
    
    print("Creating policies...")
    for user in regular_users:
        # Each user gets 1-3 policies
        num_policies = random.randint(1, 3)
        for _ in range(num_policies):
            policy_type = random.choice(POLICY_TYPES)
            start_date = datetime.now() - timedelta(days=random.randint(30, 730))
            
            policy = Policy(
                user_id=user.id,
                policy_number=f"POL-{policy_type.upper()}-{random.randint(100000, 999999)}",
                policy_type=policy_type,
                status="active" if random.random() > 0.1 else "expired",
                premium_amount=random.uniform(50, 500),
                coverage_amount=random.uniform(50000, 1000000),
                deductible=random.choice([250, 500, 1000, 2500, 5000]),
                start_date=start_date,
                end_date=start_date + timedelta(days=365),
                policy_details={
                    "payment_method": random.choice(["credit_card", "bank_transfer", "check"]),
                    "payment_frequency": random.choice(["monthly", "quarterly", "annual"]),
                    "has_autopay": random.choice([True, False])
                }
            )
            db.add(policy)
            policies.append(policy)
    
    db.commit()
    print(f"✅ Created {len(policies)} policies")
    return policies


def generate_tickets(db, users, policies):
    """Generate random support tickets."""
    tickets = []
    regular_users = [u for u in users if not u.is_admin]
    admins = [u for u in users if u.is_admin]
    
    print("Creating tickets...")
    for user in regular_users:
        # 30% chance of having tickets
        if random.random() > 0.3:
            continue
        
        user_policies = [p for p in policies if p.user_id == user.id]
        num_tickets = random.randint(1, 4)
        
        for i in range(num_tickets):
            created_date = datetime.now() - timedelta(days=random.randint(1, 180))
            status = random.choice(["open", "open", "in_progress", "resolved", "closed", "closed"])
            
            ticket = Ticket(
                user_id=user.id,
                policy_id=random.choice(user_policies).id if user_policies else None,
                ticket_number=f"TKT-{random.randint(100000, 999999)}",
                title=random.choice(TICKET_TITLES),
                description=f"User reported: {random.choice(TICKET_TITLES)}. Details provided via phone call.",
                category=random.choice(TICKET_CATEGORIES),
                priority=random.choice(PRIORITIES),
                status=status,
                resolution="Issue resolved satisfactorily" if status in ["resolved", "closed"] else None,
                created_at=created_date,
                resolved_at=created_date + timedelta(days=random.randint(1, 14)) if status in ["resolved", "closed"] else None,
                assigned_admin_id=random.choice(admins).id if random.random() > 0.3 else None
            )
            db.add(ticket)
            tickets.append(ticket)
    
    db.commit()
    print(f"✅ Created {len(tickets)} tickets")
    return tickets


def generate_call_summaries(db, users):
    """Generate random call history."""
    call_summaries = []
    regular_users = [u for u in users if not u.is_admin]
    
    print("Creating call summaries...")
    for user in regular_users:
        # Each user has 2-8 call history records
        num_calls = random.randint(2, 8)
        
        for i in range(num_calls):
            call_date = datetime.now() - timedelta(days=random.randint(1, 365))
            sentiment = random.choice(SENTIMENTS)
            summary_template = random.choice(CALL_SUMMARIES)
            
            # Generate conversation transcript
            conversation = [
                {"role": "user", "content": "Hello, I need help with my insurance policy."},
                {"role": "assistant", "content": "Of course! I'd be happy to help. What questions do you have?"},
                {"role": "user", "content": f"I wanted to ask about {random.choice(CALL_TOPICS).lower()}."},
                {"role": "assistant", "content": "Let me look that up for you. Based on your policy..."},
            ]
            
            call_summary = CallSummary(
                user_id=user.id,
                call_date=call_date,
                duration_seconds=random.randint(120, 1800),
                topic=random.choice(CALL_TOPICS),
                summary=summary_template.format(random.randint(1000, 9999)),
                sentiment=sentiment,
                key_points=[
                    "Discussed policy coverage",
                    "Clarified terms and conditions",
                    "Provided next steps"
                ] if random.random() > 0.5 else None,
                action_items=[
                    "Follow up in 3 days",
                    "Send policy documents via email"
                ] if random.random() > 0.7 else None,
                requires_followup=random.choice([True, False]),
                conversation_transcript=conversation
            )
            db.add(call_summary)
            call_summaries.append(call_summary)
    
    db.commit()
    print(f"✅ Created {len(call_summaries)} call summaries")
    return call_summaries


def generate_interventions(db, users):
    """Generate admin intervention records."""
    interventions = []
    regular_users = [u for u in users if not u.is_admin]
    admins = [u for u in users if u.is_admin]
    
    print("Creating admin interventions...")
    # Small percentage of users need intervention
    intervention_users = random.sample(regular_users, k=min(5, len(regular_users)))
    
    for user in intervention_users:
        intervention = AdminIntervention(
            user_id=user.id,
            admin_id=random.choice(admins).id,
            trigger_reason=random.choice([
                "Complex legal question beyond AI scope",
                "User expressed high distress level",
                "Claim dispute requiring human judgment",
                "Potential fraud detection",
                "Policy exception request",
                "Escalated complaint"
            ]),
            ai_confidence_score=random.uniform(0.2, 0.5),
            conversation_context=[
                {"role": "user", "content": "I really need to speak with someone about this issue"},
                {"role": "assistant", "content": "I understand this is important. Let me connect you with a specialist."}
            ],
            status=random.choice(["pending", "active", "resolved", "resolved"]),
            admin_notes="Handled personally, issue resolved" if random.random() > 0.5 else None,
            created_at=datetime.now() - timedelta(days=random.randint(1, 30)),
            resolved_at=datetime.now() - timedelta(days=random.randint(0, 15)) if random.random() > 0.3 else None
        )
        db.add(intervention)
        interventions.append(intervention)
    
    db.commit()
    print(f"✅ Created {len(interventions)} admin interventions")
    return interventions


def main():
    print("🌱 SEEDING DATABASE WITH PSEUDO DATA")
    print("="*70 + "\n")
    
    # Initialize database
    print("Initializing database...")
    init_db()
    print("✅ Database initialized\n")
    
    # Create session
    db = SessionLocal()
    
    try:
        # Generate data
        users = generate_users(db, num_users=20, num_admins=3)
        print()
        
        policies = generate_policies(db, users)
        print()
        
        tickets = generate_tickets(db, users, policies)
        print()
        
        call_summaries = generate_call_summaries(db, users)
        print()
        
        interventions = generate_interventions(db, users)
        print()
        
        print("="*70)
        print("✅ DATABASE SEEDING COMPLETE!")
        print("="*70)
        print(f"\nCreated:")
        print(f"  👥 {len(users)} users (3 admins, {len(users)-3} customers)")
        print(f"  📋 {len(policies)} policies")
        print(f"  🎫 {len(tickets)} tickets")
        print(f"  📞 {len(call_summaries)} call summaries")
        print(f"  🚨 {len(interventions)} admin interventions")
        
        print(f"\n🔑 Test Credentials:")
        print(f"  Admin: admin1@insurance.com / admin123")
        print(f"  User: john.smith0@email.com / password123")
        
    except Exception as e:
        print(f"\n❌ Error seeding database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
