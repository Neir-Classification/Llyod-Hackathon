"""Direct test of JWT functionality."""
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"

# Create token
data = {"sub": 4}
expire = datetime.utcnow() + timedelta(minutes=1440)
data.update({"exp": expire})
token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

print(f"✅ Created token: {token[:50]}...")
print(f"   Payload: {data}")

# Decode token
try:
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    print(f"\n✅ Decoded successfully!")
    print(f"   Payload: {decoded}")
    print(f"   User ID: {decoded.get('sub')}")
except JWTError as e:
    print(f"\n❌ JWT Error: {e}")
except Exception as e:
    print(f"\n❌ Error: {e}")
