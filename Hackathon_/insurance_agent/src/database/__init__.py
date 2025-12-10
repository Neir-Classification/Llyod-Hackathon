"""Database module initialization."""
from .customer_db import CustomerDatabase, CustomerProfile, get_customer_db

# Try to import real customer database (requires pandas)
try:
    from .real_customer_db import RealCustomerDatabase, RealCustomerProfile, get_real_customer_db
    REAL_DB_AVAILABLE = True
except ImportError:
    REAL_DB_AVAILABLE = False
    RealCustomerDatabase = None
    RealCustomerProfile = None
    get_real_customer_db = None

__all__ = [
    "CustomerDatabase",
    "CustomerProfile", 
    "get_customer_db",
    "RealCustomerDatabase",
    "RealCustomerProfile",
    "get_real_customer_db",
    "REAL_DB_AVAILABLE"
]
