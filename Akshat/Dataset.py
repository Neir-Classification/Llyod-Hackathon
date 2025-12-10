import json
import re
from typing import Dict, List, Any

class PolicyLimitsDatabase:
    """
    Structured database for policy limits with fast querying capabilities.
    Organizes insurance coverage data into indexed JSON format.
    """
    
    def __init__(self):
        self.data = self._initialize_data()
        
    def _initialize_data(self) -> Dict[str, Any]:
        """Initialize the complete policy limits database."""
        return {
            "metadata": {
                "last_updated": "August 2024",
                "provider": "Halifax Home Insurance",
                "underwriter": "Lloyds Bank General Insurance Limited"
            },
            "coverage_types": {
                "buildings_insurance": {
                    "description": "Covers the structure of your home and its outbuildings including roof, walls, windows, ceilings, and permanent fixtures",
                    "limits": {
                        "Bronze": {
                            "buildings": "Full rebuild cost",
                            "accidental_damage": "Not available",
                            "plants_in_garden": 1000,
                            "tracing_accessing_leak": 5000,
                            "blocked_drains": 1000,
                            "alternative_accommodation_owner": 100000,
                            "loss_of_rent_landlord": 100000,
                            "homeowner_legal_responsibility": 2000000,
                            "emergency_services_damage": "Full rebuild cost (trees/plants/shrubs: £1,000)"
                        },
                        "Silver": {
                            "buildings": "Full rebuild cost",
                            "accidental_damage": "Included",
                            "plants_in_garden": 1000,
                            "tracing_accessing_leak": 5000,
                            "blocked_drains": 1000,
                            "alternative_accommodation_owner": 100000,
                            "loss_of_rent_landlord": "Not available",
                            "homeowner_legal_responsibility": 2000000,
                            "emergency_services_damage": "Full rebuild cost (trees/plants/shrubs: £1,000)"
                        },
                        "Gold": {
                            "buildings": "Full rebuild cost",
                            "accidental_damage": "Included",
                            "plants_in_garden": 1000,
                            "tracing_accessing_leak": 5000,
                            "blocked_drains": 1000,
                            "alternative_accommodation_owner": 100000,
                            "loss_of_rent_landlord": "Not available",
                            "homeowner_legal_responsibility": 2000000,
                            "emergency_services_damage": "Full rebuild cost (trees/plants/shrubs: £1,000)"
                        }
                    }
                },
                "contents_insurance": {
                    "description": "Covers items in your home including furniture, clothing, electronics, carpets and curtains",
                    "limits": {
                        "Bronze": {
                            "contents_total": 50000,
                            "accidental_damage": "Not available",
                            "frozen_food_damage": 500,
                            "visitors_belongings": 500,
                            "alternative_accommodation": 25000,
                            "alternative_accommodation_additional": True,
                            "money": 500,
                            "documents": 2500,
                            "contents_in_outbuildings": 5000,
                            "contents_in_open": 1000,
                            "trees_plants": 1000,
                            "metered_water": 1000,
                            "personal_legal_responsibility": 2000000,
                            "personal_legal_responsibility_additional": True,
                            "employer_responsibility_domestic_staff": 10000000,
                            "employer_responsibility_additional": True,
                            "protection_for_tenants": 10000,
                            "protection_for_tenants_additional": True,
                            "tenant_home_improvements": 5000,
                            "tenant_home_improvements_additional": True,
                            "emergency_services_damage": "Contents sum insured (trees/plants/shrubs: £1,000)"
                        },
                        "Silver": {
                            "contents_total": 100000,
                            "accidental_damage": "Included",
                            "frozen_food_damage": 500,
                            "visitors_belongings": 500,
                            "alternative_accommodation": 25000,
                            "alternative_accommodation_additional": True,
                            "money": 500,
                            "documents": 2500,
                            "contents_in_outbuildings": 5000,
                            "contents_in_open": 1000,
                            "trees_plants": 1000,
                            "metered_water": 1000,
                            "personal_legal_responsibility": 2000000,
                            "personal_legal_responsibility_additional": True,
                            "employer_responsibility_domestic_staff": 10000000,
                            "employer_responsibility_additional": True,
                            "protection_for_tenants": 10000,
                            "protection_for_tenants_additional": True,
                            "tenant_home_improvements": 5000,
                            "tenant_home_improvements_additional": True,
                            "emergency_services_damage": "Contents sum insured (trees/plants/shrubs: £1,000)"
                        },
                        "Gold": {
                            "contents_total": 250000,
                            "accidental_damage": "Included",
                            "frozen_food_damage": 500,
                            "visitors_belongings": 500,
                            "alternative_accommodation": 25000,
                            "alternative_accommodation_additional": True,
                            "money": 500,
                            "documents": 2500,
                            "contents_in_outbuildings": 5000,
                            "contents_in_open": 1000,
                            "trees_plants": 1000,
                            "metered_water": 1000,
                            "personal_legal_responsibility": 2000000,
                            "personal_legal_responsibility_additional": True,
                            "employer_responsibility_domestic_staff": 10000000,
                            "employer_responsibility_additional": True,
                            "protection_for_tenants": 10000,
                            "protection_for_tenants_additional": True,
                            "tenant_home_improvements": 5000,
                            "tenant_home_improvements_additional": True,
                            "emergency_services_damage": "Contents sum insured (trees/plants/shrubs: £1,000)"
                        }
                    },
                    "specified_items": {
                        "description": "Items worth more than £2,000 each (excluding home appliances and non-antique furniture)",
                        "individual_item_limit": 40000,
                        "total_specified_item_limit": 100000,
                        "coverage": "In home and optionally when temporarily away",
                        "note": "Additional to overall contents cover limit"
                    }
                },
                "legal_expenses": {
                    "description": "Expert legal support for civil legal disputes including contract disputes, personal injury, and clinical negligence",
                    "limits": {
                        "Bronze": "Not available",
                        "Silver": 50000,
                        "Gold": 50000
                    }
                },
                "optional_cover": {
                    "away_from_home": {
                        "description": "Covers items like rings, watches, bikes, laptops when taken away from home",
                        "limits": {
                            "Bronze": {
                                "items_lost_stolen": {
                                    "min": 1000,
                                    "max": 25000,
                                    "customizable": True
                                },
                                "accidental_damage": "Not available",
                                "students_contents": 5000
                            },
                            "Silver": {
                                "items_lost_stolen": {
                                    "min": 1000,
                                    "max": 25000,
                                    "customizable": True
                                },
                                "accidental_damage": "Included",
                                "students_contents": 5000
                            },
                            "Gold": {
                                "items_lost_stolen": {
                                    "min": 1000,
                                    "max": 25000,
                                    "customizable": True
                                },
                                "accidental_damage": "Included",
                                "students_contents": 5000
                            }
                        }
                    },
                    "home_emergency": {
                        "description": "Emergency repairs including heating, plumbing, electrics, roofing, windows, doors and locks",
                        "limits": {
                            "Bronze": {
                                "total_cover": 1000,
                                "boiler_replacement": 500,
                                "uninhabitable_accommodation": 250
                            },
                            "Silver": {
                                "total_cover": 1000,
                                "boiler_replacement": 500,
                                "uninhabitable_accommodation": 250
                            },
                            "Gold": {
                                "total_cover": 1000,
                                "boiler_replacement": 500,
                                "uninhabitable_accommodation": 250
                            }
                        },
                        "note": "Limits are part of, not in addition to, overall Home Emergency cover limit"
                    }
                }
            },
            "restrictions": {
                "landlords": "Cannot choose Silver or Gold cover for Buildings insurance"
            }
        }
    
    def get_coverage_limit(self, coverage_type: str, tier: str, item: str) -> Any:
        """
        Fast query for specific coverage limit.
        
        Args:
            coverage_type: e.g., 'buildings_insurance', 'contents_insurance', 'legal_expenses'
            tier: 'Bronze', 'Silver', or 'Gold'
            item: specific coverage item name
            
        Returns:
            Coverage limit value or None if not found
        """
        try:
            return self.data["coverage_types"][coverage_type]["limits"][tier][item]
        except KeyError:
            return None
    
    def get_tier_comparison(self, coverage_type: str, item: str) -> Dict[str, Any]:
        """
        Compare a specific item across all tiers.
        
        Args:
            coverage_type: e.g., 'buildings_insurance', 'contents_insurance'
            item: specific coverage item name
            
        Returns:
            Dictionary with Bronze, Silver, Gold values
        """
        result = {}
        for tier in ["Bronze", "Silver", "Gold"]:
            result[tier] = self.get_coverage_limit(coverage_type, tier, item)
        return result
    
    def get_all_limits_for_tier(self, tier: str) -> Dict[str, Any]:
        """
        Get all coverage limits for a specific tier.
        
        Args:
            tier: 'Bronze', 'Silver', or 'Gold'
            
        Returns:
            Dictionary of all coverage types and their limits
        """
        result = {}
        for coverage_type, data in self.data["coverage_types"].items():
            if "limits" in data and tier in data["limits"]:
                result[coverage_type] = data["limits"][tier]
        return result
    
    def search_coverage(self, keyword: str) -> List[Dict[str, Any]]:
        """
        Search for coverage items matching a keyword.
        
        Args:
            keyword: Search term (case-insensitive)
            
        Returns:
            List of matching coverage items with their details
        """
        results = []
        keyword_lower = keyword.lower()
        
        def search_dict(d, path=""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                if keyword_lower in key.lower() or keyword_lower in str(value).lower():
                    results.append({
                        "path": current_path,
                        "key": key,
                        "value": value
                    })
                if isinstance(value, dict):
                    search_dict(value, current_path)
        
        search_dict(self.data["coverage_types"])
        return results
    
    def export_json(self, filepath: str = "policy_limits.json"):
        """Export the database to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"Data exported to {filepath}")
    
    def get_full_data(self) -> Dict[str, Any]:
        """Return the complete database."""
        return self.data


# Create and initialize the database
def main():
    db = PolicyLimitsDatabase()
    
    # Export to JSON file
    db.export_json("/Users/akshat/Documents/GitHub/Lyyod-Hackathon/Dataset/policy_limits.json")
    
    # Example queries
    print("\n=== Example Queries ===\n")
    
    # Query 1: Get contents coverage for Silver tier
    print("1. Contents total coverage for Silver:")
    print(f"   £{db.get_coverage_limit('contents_insurance', 'Silver', 'contents_total'):,}")
    
    # Query 2: Compare home emergency coverage across tiers
    print("\n2. Home Emergency total cover comparison:")
    comparison = db.get_tier_comparison('optional_cover', 'home_emergency')
    print(f"   {comparison}")
    
    # Query 3: Get all Bronze tier limits
    print("\n3. All Bronze tier coverages:")
    bronze_limits = db.get_all_limits_for_tier('Bronze')
    print(f"   Found {len(bronze_limits)} coverage types")
    
    # Query 4: Search for 'legal' related coverage
    print("\n4. Search results for 'legal':")
    legal_items = db.search_coverage('legal')
    for item in legal_items[:3]:
        print(f"   {item['path']}: {item['value']}")
    
    # Query 5: Get specified items info
    print("\n5. Specified items limits:")
    specified = db.data['coverage_types']['contents_insurance']['specified_items']
    print(f"   Individual limit: £{specified['individual_item_limit']:,}")
    print(f"   Total limit: £{specified['total_specified_item_limit']:,}")
    
    print("\n" + "="*50)
    print("Database created successfully!")
    print("JSON file saved to: Dataset/policy_limits.json")
    print("="*50)


if __name__ == "__main__":
    main()
