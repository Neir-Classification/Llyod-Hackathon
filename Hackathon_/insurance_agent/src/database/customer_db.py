"""
Customer database module for CRM-like functionality.
"""
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.utils.config import CUSTOMERS_DIR


@dataclass
class CustomerProfile:
    """Customer profile data structure."""
    id: str
    policy_number: str
    first_name: str
    last_name: str
    email: str
    phone: str
    address: Dict[str, str]
    policy_type: str
    coverage: Dict[str, int]
    deductible: int
    premium_annual: int
    endorsements: List[str]
    policy_start_date: str
    policy_end_date: str
    claims_history: List[Dict[str, Any]]
    scheduled_items: Optional[List[Dict[str, Any]]] = None
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self) -> str:
        addr = self.address
        return f"{addr['street']}, {addr['city']}, {addr['state']} {addr['zip']}"
    
    def has_endorsement(self, endorsement_name: str) -> bool:
        """Check if customer has a specific endorsement."""
        endorsement_lower = endorsement_name.lower()
        return any(
            endorsement_lower in e.lower() 
            for e in self.endorsements
        )
    
    def get_coverage_limit(self, coverage_type: str) -> Optional[int]:
        """Get a specific coverage limit."""
        return self.coverage.get(coverage_type)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "policy_number": self.policy_number,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.full_address,
            "policy_type": self.policy_type,
            "coverage": self.coverage,
            "deductible": self.deductible,
            "premium_annual": self.premium_annual,
            "endorsements": self.endorsements,
            "policy_start_date": self.policy_start_date,
            "policy_end_date": self.policy_end_date,
            "claims_history": self.claims_history,
            "scheduled_items": self.scheduled_items
        }
    
    def summary(self) -> str:
        """Get a brief summary of the customer profile."""
        return (
            f"Customer: {self.full_name}\n"
            f"Policy: {self.policy_number} ({self.policy_type})\n"
            f"Coverage: Dwelling ${self.coverage.get('dwelling', 'N/A'):,}, "
            f"Personal Property ${self.coverage.get('personal_property', 'N/A'):,}\n"
            f"Deductible: ${self.deductible:,}\n"
            f"Endorsements: {', '.join(self.endorsements) if self.endorsements else 'None'}\n"
            f"Claims History: {len(self.claims_history)} prior claim(s)"
        )


class CustomerDatabase:
    """
    Mock customer database for insurance CRM.
    In production, this would connect to a real database.
    """
    
    def __init__(self, data_file: Optional[Path] = None):
        self.data_file = data_file or CUSTOMERS_DIR / "customers.json"
        self._customers: Dict[str, CustomerProfile] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load customer data from JSON file."""
        if not self.data_file.exists():
            print(f"Warning: Customer data file not found: {self.data_file}")
            return
        
        with open(self.data_file, 'r') as f:
            data = json.load(f)
        
        for customer_data in data.get("customers", []):
            profile = CustomerProfile(
                id=customer_data["id"],
                policy_number=customer_data["policy_number"],
                first_name=customer_data["first_name"],
                last_name=customer_data["last_name"],
                email=customer_data["email"],
                phone=customer_data["phone"],
                address=customer_data["address"],
                policy_type=customer_data["policy_type"],
                coverage=customer_data["coverage"],
                deductible=customer_data["deductible"],
                premium_annual=customer_data["premium_annual"],
                endorsements=customer_data["endorsements"],
                policy_start_date=customer_data["policy_start_date"],
                policy_end_date=customer_data["policy_end_date"],
                claims_history=customer_data["claims_history"],
                scheduled_items=customer_data.get("scheduled_items")
            )
            self._customers[profile.id] = profile
            self._customers[profile.policy_number] = profile
            self._customers[profile.phone] = profile
    
    def get_by_id(self, customer_id: str) -> Optional[CustomerProfile]:
        """Get customer by ID."""
        return self._customers.get(customer_id)
    
    def get_by_policy_number(self, policy_number: str) -> Optional[CustomerProfile]:
        """Get customer by policy number."""
        return self._customers.get(policy_number)
    
    def get_by_phone(self, phone: str) -> Optional[CustomerProfile]:
        """Get customer by phone number."""
        # Normalize phone number
        phone_normalized = ''.join(filter(str.isdigit, phone))
        for profile in self._customers.values():
            profile_phone = ''.join(filter(str.isdigit, profile.phone))
            if phone_normalized == profile_phone or phone_normalized[-10:] == profile_phone[-10:]:
                return profile
        return None
    
    def get_by_name(self, name: str) -> Optional[CustomerProfile]:
        """Get customer by name (fuzzy match)."""
        name_lower = name.lower()
        for profile in self._customers.values():
            if (name_lower in profile.full_name.lower() or
                name_lower == profile.first_name.lower() or
                name_lower == profile.last_name.lower()):
                return profile
        return None
    
    def search(self, query: str) -> Optional[CustomerProfile]:
        """
        Search for customer by any identifier.
        Tries: ID, policy number, phone, name
        """
        # Try direct lookups first
        result = self._customers.get(query)
        if result:
            return result
        
        # Try phone
        result = self.get_by_phone(query)
        if result:
            return result
        
        # Try name
        result = self.get_by_name(query)
        if result:
            return result
        
        return None
    
    def check_endorsement(
        self,
        customer_id: str,
        endorsement_name: str
    ) -> Dict[str, Any]:
        """Check if a customer has a specific endorsement."""
        profile = self.search(customer_id)
        if not profile:
            return {
                "found": False,
                "error": f"Customer not found: {customer_id}"
            }
        
        has_endorsement = profile.has_endorsement(endorsement_name)
        return {
            "found": True,
            "customer_name": profile.full_name,
            "policy_number": profile.policy_number,
            "endorsement_name": endorsement_name,
            "has_endorsement": has_endorsement,
            "all_endorsements": profile.endorsements
        }
    
    def get_all_customers(self) -> List[CustomerProfile]:
        """Get all unique customer profiles."""
        seen_ids = set()
        customers = []
        for profile in self._customers.values():
            if profile.id not in seen_ids:
                seen_ids.add(profile.id)
                customers.append(profile)
        return customers


# Global database instance
_db_instance: Optional[CustomerDatabase] = None


def get_customer_db() -> CustomerDatabase:
    """Get the global customer database instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = CustomerDatabase()
    return _db_instance


if __name__ == "__main__":
    # Test the database
    db = get_customer_db()
    
    print("=== Customer Database Test ===\n")
    
    # List all customers
    print("All Customers:")
    for customer in db.get_all_customers():
        print(f"  - {customer.full_name} ({customer.policy_number})")
    
    # Test lookups
    print("\n\nTest Lookups:")
    
    # By policy number
    customer = db.get_by_policy_number("HO-2024-001234")
    if customer:
        print(f"\nBy Policy Number:\n{customer.summary()}")
    
    # Check endorsement
    result = db.check_endorsement("HO-2024-001234", "Water Backup")
    print(f"\nEndorsement Check: {result}")
    
    result = db.check_endorsement("HO-2024-009012", "Water Backup")
    print(f"Endorsement Check: {result}")
