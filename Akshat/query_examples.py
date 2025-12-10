"""
Quick examples for querying the policy limits database.
Fast query operations using the structured JSON data.
"""

import sys
sys.path.append('/Users/akshat/Documents/GitHub/Lyyod-Hackathon/Akshat')
from Dataset import PolicyLimitsDatabase

# Initialize database
db = PolicyLimitsDatabase()

print("=" * 60)
print("POLICY LIMITS DATABASE - QUERY EXAMPLES")
print("=" * 60)

# Query 1: Get specific coverage limit
print("\n1. What's the contents coverage for Gold tier?")
gold_contents = db.get_coverage_limit('contents_insurance', 'Gold', 'contents_total')
print(f"   Answer: £{gold_contents:,}")

# Query 2: Compare across all tiers
print("\n2. Compare legal expenses across all tiers:")
legal_comparison = db.get_tier_comparison('legal_expenses', 'limits')
for tier, value in legal_comparison.items():
    print(f"   {tier}: {value}")

# Query 3: Get all limits for a specific tier
print("\n3. What's covered under Bronze tier buildings insurance?")
bronze_buildings = db.get_coverage_limit('buildings_insurance', 'Bronze', 'buildings')
bronze_plants = db.get_coverage_limit('buildings_insurance', 'Bronze', 'plants_in_garden')
bronze_leak = db.get_coverage_limit('buildings_insurance', 'Bronze', 'tracing_accessing_leak')
print(f"   Buildings: {bronze_buildings}")
print(f"   Plants in garden: £{bronze_plants:,}")
print(f"   Tracing & accessing leak: £{bronze_leak:,}")

# Query 4: Home emergency coverage
print("\n4. Home emergency cover limits:")
for tier in ['Bronze', 'Silver', 'Gold']:
    limits = db.data['coverage_types']['optional_cover']['home_emergency']['limits'][tier]
    print(f"   {tier}:")
    print(f"      Total cover: £{limits['total_cover']:,}")
    print(f"      Boiler replacement: £{limits['boiler_replacement']:,}")
    print(f"      Uninhabitable accommodation: £{limits['uninhabitable_accommodation']:,}")

# Query 5: Specified items limits
print("\n5. What are the limits for specified items (valuable items)?")
specified = db.data['coverage_types']['contents_insurance']['specified_items']
print(f"   Individual item limit: £{specified['individual_item_limit']:,}")
print(f"   Total specified items limit: £{specified['total_specified_item_limit']:,}")
print(f"   Note: {specified['note']}")

# Query 6: Away from home coverage
print("\n6. Away from home coverage for Silver tier:")
away_silver = db.data['coverage_types']['optional_cover']['away_from_home']['limits']['Silver']
print(f"   Items lost/stolen: £{away_silver['items_lost_stolen']['min']:,} - £{away_silver['items_lost_stolen']['max']:,}")
print(f"   Accidental damage: {away_silver['accidental_damage']}")
print(f"   Students' contents: £{away_silver['students_contents']:,}")

# Query 7: Search functionality
print("\n7. Search for 'boiler' related coverage:")
boiler_results = db.search_coverage('boiler')
for result in boiler_results[:3]:
    print(f"   {result['path']}: {result['value']}")

# Query 8: Check restrictions
print("\n8. Are there any restrictions?")
restrictions = db.data['restrictions']
for key, value in restrictions.items():
    print(f"   {key}: {value}")

print("\n" + "=" * 60)
print("All queries completed successfully!")
print("=" * 60)
