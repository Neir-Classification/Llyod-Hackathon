"""
Real customer database using the hackathon Excel dataset.
Provides access to 125 real customer policy records.
"""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

from src.utils.config import DATASET_DIR


@dataclass
class RealCustomerProfile:
    """Customer profile from the hackathon dataset."""
    # Core identifiers
    policy_id: str
    client_id: str
    forename: str
    surname: str
    email: str
    telephone: Optional[str]
    
    # Address
    risk_address: str
    risk_postcode: str
    mail_address: str
    mail_postcode: str
    
    # Policy details
    product: str
    status: str
    brand: str
    tier: str
    policy_start: str
    policy_end: str
    inception: str
    auto_renewal: bool
    payment_frequency: str
    payment_type: str
    
    # Premium
    annual_premium_incl_ipt: float
    annual_premium_excl_ipt: float
    total_premium_due: float
    
    # Property info
    property_type: str
    num_bedrooms: int
    num_bathrooms: int
    
    # Coverage flags
    has_buildings_cover: bool
    has_contents_cover: bool
    has_home_emergency_cover: bool
    has_legal_cover: bool
    has_away_from_home_cover: bool
    has_accidental_damage_buildings: bool
    has_accidental_damage_contents: bool
    has_pedal_cycles_cover: bool
    has_personal_belongings_cover: bool
    has_outbuildings_cover: bool
    has_student_belongings_cover: bool
    has_specified_items: bool
    
    # Limits & excess
    buildings_excess: int
    contents_excess: int
    buildings_sum_insured: int
    contents_sum_insured: int
    personal_belongings_limit: int
    specified_items_limit: int
    high_risk_items_limit: int
    single_article_limit: int
    pedal_cycle_limit: int
    home_emergency_limit: int
    legal_expenses_limit: int
    
    # Claims
    total_claims: int
    buildings_claims: int
    contents_claims: int
    policy_tenure: int
    
    # Full raw data
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def full_name(self) -> str:
        return f"{self.forename} {self.surname}"
    
    def get_coverage_summary(self) -> Dict[str, Any]:
        """Get a summary of all coverages."""
        return {
            "buildings": {
                "covered": self.has_buildings_cover,
                "sum_insured": self.buildings_sum_insured,
                "excess": self.buildings_excess,
                "accidental_damage": self.has_accidental_damage_buildings,
                "outbuildings": self.has_outbuildings_cover
            },
            "contents": {
                "covered": self.has_contents_cover,
                "sum_insured": self.contents_sum_insured,
                "excess": self.contents_excess,
                "accidental_damage": self.has_accidental_damage_contents,
                "single_article_limit": self.single_article_limit
            },
            "optional_covers": {
                "home_emergency": self.has_home_emergency_cover,
                "legal_expenses": self.has_legal_cover,
                "away_from_home": self.has_away_from_home_cover,
                "personal_belongings": self.has_personal_belongings_cover,
                "pedal_cycles": self.has_pedal_cycles_cover,
                "student_belongings": self.has_student_belongings_cover,
                "specified_items": self.has_specified_items
            },
            "limits": {
                "personal_belongings": self.personal_belongings_limit,
                "pedal_cycles": self.pedal_cycle_limit,
                "specified_items": self.specified_items_limit,
                "high_risk_items": self.high_risk_items_limit,
                "home_emergency": self.home_emergency_limit,
                "legal_expenses": self.legal_expenses_limit
            }
        }
    
    def summary(self) -> str:
        """Get a human-readable summary of the customer profile."""
        covers = []
        if self.has_buildings_cover:
            covers.append(f"Buildings (£{self.buildings_sum_insured:,})")
        if self.has_contents_cover:
            covers.append(f"Contents (£{self.contents_sum_insured:,})")
        if self.has_home_emergency_cover:
            covers.append("Home Emergency")
        if self.has_legal_cover:
            covers.append("Legal Expenses")
        if self.has_away_from_home_cover:
            covers.append("Away from Home")
        if self.has_accidental_damage_contents or self.has_accidental_damage_buildings:
            covers.append("Accidental Damage")
        
        return f"""Customer: {self.full_name}
Policy ID: {self.policy_id}
Status: {self.status}
Tier: {self.tier}

Property: {self.property_type}
Address: {self.risk_address}, {self.risk_postcode}
Bedrooms: {self.num_bedrooms}, Bathrooms: {self.num_bathrooms}

Coverage: {', '.join(covers) if covers else 'None'}

Excess: Buildings £{self.buildings_excess}, Contents £{self.contents_excess}
Annual Premium: £{self.annual_premium_incl_ipt:.2f} (inc. IPT)
Payment: {self.payment_frequency} ({self.payment_type})

Claims History: {self.total_claims} total claims
Policy Tenure: {self.policy_tenure} year(s)"""


class RealCustomerDatabase:
    """
    Customer database using the hackathon Excel dataset.
    Contains 125 real customer policy records.
    """
    
    def __init__(self, excel_path: Optional[Path] = None):
        self.excel_path = excel_path or (DATASET_DIR / "3.1 Agentic AI Servicing Agent in Home Insurance_ai_hackathon_data.xlsx")
        self._df: Optional[pd.DataFrame] = None
        self._customers: Dict[str, RealCustomerProfile] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load customer data from Excel file."""
        if not self.excel_path.exists():
            print(f"Warning: Dataset not found: {self.excel_path}")
            return
        
        self._df = pd.read_excel(self.excel_path, sheet_name="data")
        print(f"Loaded {len(self._df)} customer records from dataset")
        
        # Index customers by various identifiers
        for _, row in self._df.iterrows():
            profile = self._row_to_profile(row)
            if profile:
                self._customers[profile.policy_id] = profile
                self._customers[profile.client_id] = profile
                if profile.email:
                    self._customers[profile.email.lower()] = profile
    
    def _row_to_profile(self, row: pd.Series) -> Optional[RealCustomerProfile]:
        """Convert a DataFrame row to a CustomerProfile."""
        try:
            # Helper to safely get values
            def safe_get(key, default=None):
                val = row.get(key, default)
                if pd.isna(val):
                    return default
                return val
            
            def safe_int(key, default=0):
                val = safe_get(key, default)
                try:
                    return int(val) if val is not None else default
                except (ValueError, TypeError):
                    return default
            
            def safe_float(key, default=0.0):
                val = safe_get(key, default)
                try:
                    return float(val) if val is not None else default
                except (ValueError, TypeError):
                    return default
            
            def safe_bool(key):
                val = safe_get(key, 0)
                return val == 1 or val == True or val == "1" or val == "Yes"
            
            return RealCustomerProfile(
                # Identifiers
                policy_id=str(safe_get('POLICY_ID', '')),
                client_id=str(safe_get('Client_ID', '')),
                forename=str(safe_get('FORENAME', '')),
                surname=str(safe_get('SURNAME', '')),
                email=str(safe_get('EMAIL_ADDRESS', '')),
                telephone=str(safe_get('TELEPHONE', '')) if safe_get('TELEPHONE') else None,
                
                # Address
                risk_address=str(safe_get('Risk_Address_1', '')),
                risk_postcode=str(safe_get('Risk_PostCode', '')),
                mail_address=str(safe_get('Mail_Address_1', '')),
                mail_postcode=str(safe_get('MAIL_POSTCODE', '')),
                
                # Policy details
                product=str(safe_get('Product', 'HAP')),
                status=str(safe_get('status_policy', '')),
                brand=str(safe_get('brand', '')),
                tier=str(safe_get('Tier', 'FLEX')),
                policy_start=str(safe_get('TermIncep', '')),
                policy_end=str(safe_get('NextRenewal', '')),
                inception=str(safe_get('INCEPTION', '')),
                auto_renewal=safe_bool('Auto_Renewal'),
                payment_frequency=str(safe_get('PAYMENT_FREQUENCY', '')),
                payment_type=str(safe_get('PaymentType', '')),
                
                # Premium
                annual_premium_incl_ipt=safe_float('ANNUAL_PREMIUM_INCL_IPT'),
                annual_premium_excl_ipt=safe_float('ANNUAL_PREMIUM_EXCL_IPT'),
                total_premium_due=safe_float('TOT_PREM_DUE'),
                
                # Property
                property_type=str(safe_get('riskPricingPropType', '')),
                num_bedrooms=safe_int('Prop_Beds'),
                num_bathrooms=safe_int('Prop_Num_Baths'),
                
                # Coverage flags
                has_buildings_cover=safe_bool('BldsMainCover'),
                has_contents_cover=safe_bool('ContentsMainCover'),
                has_home_emergency_cover=safe_bool('HomeEmergencyCover'),
                has_legal_cover=safe_bool('LegalCover'),
                has_away_from_home_cover=safe_bool('ContentsAwayFromHomeCover'),
                has_accidental_damage_buildings=safe_bool('BldsAccidentalDamageCover'),
                has_accidental_damage_contents=safe_bool('ContentsAccidentalDamageCover'),
                has_pedal_cycles_cover=safe_bool('ContentsPedalCyclesCover'),
                has_personal_belongings_cover=safe_bool('ContentsPersonalBelongingsCover'),
                has_outbuildings_cover=safe_bool('BldsOutBuildingsCover') or safe_bool('ContentsOutBuildingsCover'),
                has_student_belongings_cover=safe_bool('ContentsStudentBelongingsCover'),
                has_specified_items=safe_bool('SpecifiedItemsFlag'),
                
                # Limits & excess
                buildings_excess=safe_int('BldsExcess', 200),
                contents_excess=safe_int('ContentsExcess', 200),
                buildings_sum_insured=safe_int('BldsSumInsuredLimit', 550000),
                contents_sum_insured=safe_int('ContentsSumInsLimit', 75000),
                personal_belongings_limit=safe_int('PersBelongingsSumInsuredLimit'),
                specified_items_limit=safe_int('SpecItemsSumInsuredLimit'),
                high_risk_items_limit=safe_int('HighRiskItemsLimit', 5000),
                single_article_limit=safe_int('ContentsSingleArticleLimit', 2000),
                pedal_cycle_limit=safe_int('ContentsPedalCycleSumInsuredLimit'),
                home_emergency_limit=safe_int('HEC_Sum_Insured_Limit', 5000),
                legal_expenses_limit=safe_int('LEC_Sum_Insured_Limit', 50000),
                
                # Claims
                total_claims=safe_int('Tot_Num_Claims'),
                buildings_claims=safe_int('BuildingsClaims'),
                contents_claims=safe_int('ContentsClaims'),
                policy_tenure=safe_int('Policy_Tenure'),
                
                # Raw data for advanced queries
                raw_data=row.to_dict()
            )
        except Exception as e:
            print(f"Error parsing customer row: {e}")
            return None
    
    def get_by_policy_id(self, policy_id: str) -> Optional[RealCustomerProfile]:
        """Get customer by policy ID."""
        return self._customers.get(policy_id)
    
    def get_by_client_id(self, client_id: str) -> Optional[RealCustomerProfile]:
        """Get customer by client ID."""
        return self._customers.get(str(client_id))
    
    def get_by_email(self, email: str) -> Optional[RealCustomerProfile]:
        """Get customer by email."""
        return self._customers.get(email.lower())
    
    def get_by_name(self, name: str) -> List[RealCustomerProfile]:
        """Search customers by name (partial match)."""
        name_lower = name.lower()
        results = []
        seen_ids = set()
        
        for profile in self._customers.values():
            if profile.policy_id in seen_ids:
                continue
            
            full_name = profile.full_name.lower()
            if (name_lower in full_name or 
                name_lower in profile.forename.lower() or 
                name_lower in profile.surname.lower()):
                results.append(profile)
                seen_ids.add(profile.policy_id)
        
        return results
    
    def search(self, query: str) -> Optional[RealCustomerProfile]:
        """
        Search for a customer by any identifier.
        Tries: policy_id, client_id, email, name
        """
        # Direct lookup
        if query in self._customers:
            return self._customers[query]
        
        # Try email (case-insensitive)
        result = self.get_by_email(query)
        if result:
            return result
        
        # Try name search (return first match)
        results = self.get_by_name(query)
        if results:
            return results[0]
        
        return None
    
    def get_all_customers(self) -> List[RealCustomerProfile]:
        """Get all unique customer profiles."""
        seen_ids = set()
        customers = []
        for profile in self._customers.values():
            if profile.policy_id not in seen_ids:
                seen_ids.add(profile.policy_id)
                customers.append(profile)
        return customers
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the raw DataFrame for advanced queries."""
        return self._df if self._df is not None else pd.DataFrame()
    
    def check_coverage(self, policy_id: str, coverage_type: str) -> Dict[str, Any]:
        """Check if a customer has a specific coverage."""
        profile = self.get_by_policy_id(policy_id)
        if not profile:
            return {"found": False, "error": f"Policy not found: {policy_id}"}
        
        coverage_map = {
            "buildings": profile.has_buildings_cover,
            "contents": profile.has_contents_cover,
            "home_emergency": profile.has_home_emergency_cover,
            "legal": profile.has_legal_cover,
            "legal_expenses": profile.has_legal_cover,
            "away_from_home": profile.has_away_from_home_cover,
            "accidental_damage": profile.has_accidental_damage_contents or profile.has_accidental_damage_buildings,
            "accidental_damage_buildings": profile.has_accidental_damage_buildings,
            "accidental_damage_contents": profile.has_accidental_damage_contents,
            "pedal_cycles": profile.has_pedal_cycles_cover,
            "personal_belongings": profile.has_personal_belongings_cover,
            "student_belongings": profile.has_student_belongings_cover,
            "specified_items": profile.has_specified_items,
            "outbuildings": profile.has_outbuildings_cover
        }
        
        coverage_key = coverage_type.lower().replace(" ", "_").replace("-", "_")
        has_coverage = coverage_map.get(coverage_key, None)
        
        if has_coverage is None:
            return {
                "found": True,
                "customer_name": profile.full_name,
                "policy_id": profile.policy_id,
                "coverage_type": coverage_type,
                "error": f"Unknown coverage type: {coverage_type}",
                "available_types": list(coverage_map.keys())
            }
        
        return {
            "found": True,
            "customer_name": profile.full_name,
            "policy_id": profile.policy_id,
            "coverage_type": coverage_type,
            "has_coverage": has_coverage,
            "tier": profile.tier
        }


# Global instance
_real_db_instance: Optional[RealCustomerDatabase] = None


def get_real_customer_db() -> RealCustomerDatabase:
    """Get the global real customer database instance."""
    global _real_db_instance
    if _real_db_instance is None:
        _real_db_instance = RealCustomerDatabase()
    return _real_db_instance


if __name__ == "__main__":
    db = get_real_customer_db()
    
    print("=== Real Customer Database Test ===\n")
    
    customers = db.get_all_customers()
    print(f"Total customers: {len(customers)}\n")
    
    if customers:
        # Show first customer
        print("=== Sample Customer ===")
        print(customers[0].summary())
        
        # Show coverage details
        print("\n=== Coverage Summary ===")
        import json
        print(json.dumps(customers[0].get_coverage_summary(), indent=2))
