"""Debug script to check users in database."""
from database import SessionLocal, User
import bcrypt

db = SessionLocal()

print("\n📋 All Users in Database:")
print("="*70)

users = db.query(User).all()
for user in users:
    print(f"\n{'👑 ADMIN' if user.is_admin else '👤 USER'}: {user.full_name}")
    print(f"   Email: {user.email}")
    print(f"   Username: {user.username}")
    print(f"   Active: {user.is_active}")
    print(f"   Hashed Password: {user.hashed_password[:50]}...")
    
    # Test password verification
    if user.email == "john.smith0@email.com":
        print(f"\n   🔍 Testing password verification for this user:")
        test_password = "password123"
        try:
            result = user.verify_password(test_password)
            print(f"   verify_password('password123'): {result}")
            
            # Manual check
            manual_check = bcrypt.checkpw(
                test_password.encode('utf-8'),
                user.hashed_password.encode('utf-8')
            )
            print(f"   Manual bcrypt check: {manual_check}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

db.close()

print("\n" + "="*70)
