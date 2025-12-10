"""
Agent tools for the Insurance AI Agent.
Implements the "hands" of the agent - functions it can call.
"""
from typing import Dict, Any, Optional, List
from langchain.tools import tool
from pydantic import BaseModel, Field

from src.knowledge.retriever import PolicyRetriever
from src.database.customer_db import get_customer_db

# Try to import real customer database
try:
    from src.database.real_customer_db import get_real_customer_db, RealCustomerProfile
    REAL_DB_AVAILABLE = True
except ImportError:
    REAL_DB_AVAILABLE = False


# ============================================================================
# Tool Input Schemas
# ============================================================================

class PolicySearchInput(BaseModel):
    """Input schema for policy search tool."""
    query: str = Field(description="The search query about insurance coverage, exclusions, or policy details")
    topic: Optional[str] = Field(default=None, description="Optional topic filter: water, mold, theft, fire, wind, liability, jewelry, rental, tree, coverage, exclusion, claim, endorsement")


class CustomerLookupInput(BaseModel):
    """Input schema for customer lookup tool."""
    identifier: str = Field(description="Customer identifier: policy number (e.g., HO-2024-001234), phone number, or name")


class EndorsementCheckInput(BaseModel):
    """Input schema for endorsement check tool."""
    customer_identifier: str = Field(description="Customer policy number or name")
    endorsement_name: str = Field(description="Name of the endorsement to check (e.g., 'Water Backup', 'Scheduled Personal Property', 'Identity Theft')")


class CoverageCalculatorInput(BaseModel):
    """Input schema for coverage calculator tool."""
    coverage_amount: float = Field(description="The claimed damage or loss amount in dollars")
    deductible: float = Field(description="The policy deductible amount")
    coverage_limit: Optional[float] = Field(default=None, description="Maximum coverage limit if applicable")
    depreciation_percent: Optional[float] = Field(default=0, description="Depreciation percentage for ACV calculations (0-100)")


class ClarificationInput(BaseModel):
    """Input schema for asking clarifying questions."""
    question: str = Field(description="The clarifying question to ask the customer")
    reason: str = Field(description="Internal reason why this clarification is needed")


# ============================================================================
# Tool Implementations
# ============================================================================

@tool("search_policy_documents", args_schema=PolicySearchInput)
def search_policy_documents(query: str, topic: Optional[str] = None) -> str:
    """
    Search the insurance policy knowledge base for relevant information.
    Use this tool to find coverage details, exclusions, conditions, and policy clauses.
    Always cite the source when using information from search results.
    
    Args:
        query: What to search for in policy documents
        topic: Optional topic to filter results (water, mold, theft, etc.)
    
    Returns:
        Relevant policy excerpts with citations
    """
    retriever = PolicyRetriever()
    
    if topic:
        results = retriever.search_by_topic(topic, query, k=4)
    else:
        results = retriever.search(query, k=4)
    
    if not results:
        return "No relevant policy information found for this query. Consider rephrasing or searching for related terms."
    
    # Format results with citations
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(
            f"[Citation {i}]\n"
            f"Source: {result.citation}\n"
            f"Topics: {', '.join(result.topics)}\n"
            f"Content:\n{result.content}\n"
        )
    
    return "\n---\n".join(formatted)


@tool("get_customer_profile", args_schema=CustomerLookupInput)
def get_customer_profile(identifier: str) -> str:
    """
    Look up a customer's profile and policy information.
    Use this to identify who is calling and what coverage they have.
    
    Args:
        identifier: Policy number, phone number, or customer name
    
    Returns:
        Customer profile summary including coverage, endorsements, and claims history
    """
    # Try real database first (hackathon dataset)
    if REAL_DB_AVAILABLE:
        try:
            real_db = get_real_customer_db()
            customer = real_db.search(identifier)
            
            if customer and isinstance(customer, RealCustomerProfile):
                # Format real customer profile
                covers = []
                if customer.has_buildings_cover:
                    covers.append(f"Buildings (£{customer.buildings_sum_insured:,}, excess £{customer.buildings_excess})")
                if customer.has_contents_cover:
                    covers.append(f"Contents (£{customer.contents_sum_insured:,}, excess £{customer.contents_excess})")
                if customer.has_home_emergency_cover:
                    covers.append("Home Emergency")
                if customer.has_legal_cover:
                    covers.append("Legal Expenses")
                if customer.has_away_from_home_cover:
                    covers.append("Away from Home")
                if customer.has_accidental_damage_contents or customer.has_accidental_damage_buildings:
                    covers.append("Accidental Damage")
                if customer.has_pedal_cycles_cover:
                    covers.append("Pedal Cycles")
                if customer.has_personal_belongings_cover:
                    covers.append("Personal Belongings")
                if customer.has_student_belongings_cover:
                    covers.append("Student Belongings")
                if customer.has_specified_items:
                    covers.append("Specified Items")
                
                return f"""
Customer Profile (Dataset):
===========================
Name: {customer.full_name}
Policy ID: {customer.policy_id}
Client ID: {customer.client_id}
Email: {customer.email}
Telephone: {customer.telephone or 'Not provided'}

Property:
- Type: {customer.property_type}
- Address: {customer.risk_address}, {customer.risk_postcode}
- Bedrooms: {customer.num_bedrooms}, Bathrooms: {customer.num_bathrooms}

Policy Details:
- Status: {customer.status}
- Tier: {customer.tier}
- Product: {customer.product}
- Policy Start: {customer.policy_start}
- Next Renewal: {customer.policy_end}
- Auto Renewal: {'Yes' if customer.auto_renewal else 'No'}

Coverage: {', '.join(covers) if covers else 'None'}

Coverage Limits:
- Buildings Sum Insured: £{customer.buildings_sum_insured:,}
- Contents Sum Insured: £{customer.contents_sum_insured:,}
- Personal Belongings Limit: £{customer.personal_belongings_limit:,}
- Single Article Limit: £{customer.single_article_limit:,}
- High Risk Items Limit: £{customer.high_risk_items_limit:,}
- Home Emergency Limit: £{customer.home_emergency_limit:,}
- Legal Expenses Limit: £{customer.legal_expenses_limit:,}

Excess:
- Buildings: £{customer.buildings_excess}
- Contents: £{customer.contents_excess}

Premium:
- Annual (inc IPT): £{customer.annual_premium_incl_ipt:.2f}
- Payment: {customer.payment_frequency} ({customer.payment_type})
- Total Due: £{customer.total_premium_due:.2f}

Claims History:
- Total Claims: {customer.total_claims}
- Buildings Claims: {customer.buildings_claims}
- Contents Claims: {customer.contents_claims}
- Policy Tenure: {customer.policy_tenure} year(s)
"""
        except Exception as e:
            print(f"Real DB error: {e}")
    
    # Fall back to mock database
    db = get_customer_db()
    customer = db.search(identifier)
    
    if not customer:
        return f"Customer not found with identifier: {identifier}. Please verify the policy number or ask for correct information."
    
    # Format profile
    scheduled_items_text = ""
    if customer.scheduled_items:
        items = [f"  - {item['description']}: ${item['value']:,}" for item in customer.scheduled_items]
        scheduled_items_text = f"\nScheduled Items:\n" + "\n".join(items)
    
    claims_text = "None"
    if customer.claims_history:
        claims = [f"  - {c['date']}: {c['type']} (${c['amount_paid']:,}, {c['status']})" for c in customer.claims_history]
        claims_text = "\n" + "\n".join(claims)
    
    return f"""
Customer Profile:
================
Name: {customer.full_name}
Policy Number: {customer.policy_number}
Policy Type: {customer.policy_type}
Address: {customer.full_address}

Coverage Limits:
- Dwelling: ${customer.coverage.get('dwelling', 0):,}
- Personal Property: ${customer.coverage.get('personal_property', 0):,}
- Liability: ${customer.coverage.get('liability', 0):,}
- Medical Payments: ${customer.coverage.get('medical_payments', 0):,}

Deductible: ${customer.deductible:,}
Annual Premium: ${customer.premium_annual:,}

Endorsements: {', '.join(customer.endorsements) if customer.endorsements else 'None'}
{scheduled_items_text}

Policy Period: {customer.policy_start_date} to {customer.policy_end_date}

Claims History: {claims_text}
"""


@tool("check_customer_endorsement", args_schema=EndorsementCheckInput)
def check_customer_endorsement(customer_identifier: str, endorsement_name: str) -> str:
    """
    Check if a customer has a specific endorsement or add-on coverage.
    Common endorsements: Water Backup, Scheduled Personal Property, Identity Theft, Home Business.
    For real dataset customers: Home Emergency, Legal Expenses, Away from Home, Accidental Damage, etc.
    
    Args:
        customer_identifier: Policy number or customer name
        endorsement_name: The endorsement to check for
    
    Returns:
        Whether the customer has the endorsement and list of all their endorsements
    """
    # Try real database first
    if REAL_DB_AVAILABLE:
        try:
            real_db = get_real_customer_db()
            customer = real_db.search(customer_identifier)
            
            if customer and isinstance(customer, RealCustomerProfile):
                # Map endorsement names to coverage flags
                endorsement_map = {
                    "home emergency": customer.has_home_emergency_cover,
                    "legal": customer.has_legal_cover,
                    "legal expenses": customer.has_legal_cover,
                    "away from home": customer.has_away_from_home_cover,
                    "accidental damage": customer.has_accidental_damage_contents or customer.has_accidental_damage_buildings,
                    "accidental damage buildings": customer.has_accidental_damage_buildings,
                    "accidental damage contents": customer.has_accidental_damage_contents,
                    "pedal cycles": customer.has_pedal_cycles_cover,
                    "personal belongings": customer.has_personal_belongings_cover,
                    "student belongings": customer.has_student_belongings_cover,
                    "specified items": customer.has_specified_items,
                    "outbuildings": customer.has_outbuildings_cover,
                    "buildings": customer.has_buildings_cover,
                    "contents": customer.has_contents_cover
                }
                
                # Build list of active coverages
                active_coverages = []
                if customer.has_buildings_cover:
                    active_coverages.append("Buildings Cover")
                if customer.has_contents_cover:
                    active_coverages.append("Contents Cover")
                if customer.has_home_emergency_cover:
                    active_coverages.append("Home Emergency Cover")
                if customer.has_legal_cover:
                    active_coverages.append("Legal Expenses Cover")
                if customer.has_away_from_home_cover:
                    active_coverages.append("Away from Home Cover")
                if customer.has_accidental_damage_buildings:
                    active_coverages.append("Accidental Damage (Buildings)")
                if customer.has_accidental_damage_contents:
                    active_coverages.append("Accidental Damage (Contents)")
                if customer.has_pedal_cycles_cover:
                    active_coverages.append("Pedal Cycles Cover")
                if customer.has_personal_belongings_cover:
                    active_coverages.append("Personal Belongings Cover")
                if customer.has_student_belongings_cover:
                    active_coverages.append("Student Belongings Cover")
                if customer.has_specified_items:
                    active_coverages.append("Specified Items Cover")
                if customer.has_outbuildings_cover:
                    active_coverages.append("Outbuildings Cover")
                
                # Check for the requested endorsement
                endorsement_lower = endorsement_name.lower().strip()
                has_endorsement = endorsement_map.get(endorsement_lower, False)
                
                # Also check if any key matches partially
                if not has_endorsement:
                    for key, value in endorsement_map.items():
                        if endorsement_lower in key or key in endorsement_lower:
                            has_endorsement = value
                            break
                
                status = "HAS" if has_endorsement else "DOES NOT HAVE"
                
                return f"""
Coverage Check for {customer.full_name} (Policy: {customer.policy_id}):

Checking for: {endorsement_name}
Result: Customer {status} this coverage.
Tier: {customer.tier}

All active coverages on this policy:
{chr(10).join(f'  ✓ {c}' for c in active_coverages) if active_coverages else '  (No optional coverages)'}
"""
        except Exception as e:
            print(f"Real DB endorsement check error: {e}")
    
    # Fall back to mock database
    db = get_customer_db()
    result = db.check_endorsement(customer_identifier, endorsement_name)
    
    if not result["found"]:
        return result["error"]
    
    status = "HAS" if result["has_endorsement"] else "DOES NOT HAVE"
    
    return f"""
Endorsement Check for {result['customer_name']} (Policy: {result['policy_number']}):

Checking for: {endorsement_name}
Result: Customer {status} this endorsement.

All endorsements on this policy:
{chr(10).join(f'  ✓ {e}' for e in result['all_endorsements']) if result['all_endorsements'] else '  (No endorsements)'}
"""


@tool("calculate_coverage", args_schema=CoverageCalculatorInput)
def calculate_coverage(
    coverage_amount: float,
    deductible: float,
    coverage_limit: Optional[float] = None,
    depreciation_percent: Optional[float] = 0
) -> str:
    """
    Calculate the estimated payout for a claim.
    
    Args:
        coverage_amount: The total claimed damage amount
        deductible: The policy deductible
        coverage_limit: Maximum coverage limit (if any)
        depreciation_percent: Depreciation for Actual Cash Value (0-100)
    
    Returns:
        Breakdown of the coverage calculation
    """
    # Apply depreciation if specified
    depreciated_value = coverage_amount * (1 - depreciation_percent / 100)
    
    # Apply deductible
    after_deductible = max(0, depreciated_value - deductible)
    
    # Apply coverage limit
    if coverage_limit and after_deductible > coverage_limit:
        final_payout = coverage_limit
        limit_applied = True
    else:
        final_payout = after_deductible
        limit_applied = False
    
    calculation = f"""
Coverage Calculation:
====================
Claimed Amount: ${coverage_amount:,.2f}
"""
    
    if depreciation_percent > 0:
        calculation += f"""
Depreciation ({depreciation_percent}%): -${coverage_amount * depreciation_percent / 100:,.2f}
Depreciated Value: ${depreciated_value:,.2f}
"""
    
    calculation += f"""
Deductible: -${deductible:,.2f}
After Deductible: ${after_deductible:,.2f}
"""
    
    if limit_applied:
        calculation += f"""
Coverage Limit Applied: ${coverage_limit:,.2f}
"""
    
    calculation += f"""
---
ESTIMATED PAYOUT: ${final_payout:,.2f}

Note: This is an estimate. Actual payout depends on claim investigation and adjuster assessment.
"""
    
    return calculation


# ============================================================================
# Tool Registry
# ============================================================================

def get_all_tools() -> List:
    """Get all available agent tools."""
    return [
        search_policy_documents,
        get_customer_profile,
        check_customer_endorsement,
        calculate_coverage,
    ]


def get_tool_descriptions() -> str:
    """Get formatted descriptions of all tools."""
    tools = get_all_tools()
    descriptions = []
    for tool in tools:
        descriptions.append(f"- {tool.name}: {tool.description}")
    return "\n".join(descriptions)


if __name__ == "__main__":
    # Test tools
    print("=== Testing Agent Tools ===\n")
    
    # Test policy search
    print("1. Policy Search:")
    result = search_policy_documents.invoke({"query": "sump pump water backup", "topic": "water"})
    print(result[:500], "...\n")
    
    # Test customer lookup
    print("\n2. Customer Lookup:")
    result = get_customer_profile.invoke({"identifier": "HO-2024-001234"})
    print(result)
    
    # Test endorsement check
    print("\n3. Endorsement Check:")
    result = check_customer_endorsement.invoke({
        "customer_identifier": "HO-2024-001234",
        "endorsement_name": "Water Backup"
    })
    print(result)
    
    # Test calculator
    print("\n4. Coverage Calculator:")
    result = calculate_coverage.invoke({
        "coverage_amount": 5000,
        "deductible": 1000,
        "depreciation_percent": 20
    })
    print(result)
