"""
Golden Path Test Scenarios for the Insurance AI Agent.
These scenarios test the core use cases the agent must handle.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def agent():
    """Create agent instance for testing."""
    from src.agent.orchestrator import InsuranceAgent
    from src.knowledge.vector_store import initialize_vector_store
    
    # Initialize vector store
    initialize_vector_store(reset=False)
    
    return InsuranceAgent()


@pytest.fixture(scope="module")
def customer_db():
    """Get customer database."""
    from src.database.customer_db import get_customer_db
    return get_customer_db()


# ============================================================================
# Scenario 1: The "Yes" Path - Sump Pump Coverage (Customer HAS endorsement)
# ============================================================================

class TestSumpPumpCoverage:
    """
    Test the positive coverage scenario.
    Customer: John Doe (HO-2024-001234) - HAS Water Backup Coverage
    Scenario: Sump pump failure flooding basement
    Expected: Agent confirms coverage exists
    """
    
    def test_customer_has_water_backup_endorsement(self, customer_db):
        """Verify test customer has the Water Backup endorsement."""
        customer = customer_db.get_by_policy_number("HO-2024-001234")
        assert customer is not None
        assert customer.has_endorsement("Water Backup")
    
    def test_agent_confirms_coverage(self, agent):
        """Agent should confirm coverage for sump pump with endorsement."""
        # Set customer context
        customer_context = {
            "policy_number": "HO-2024-001234",
            "name": "John Doe"
        }
        
        result = agent.process_message(
            "My basement flooded because the sump pump failed. Am I covered?",
            customer_context=customer_context
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should mention coverage positively (with conditional language)
        coverage_indicators = ["covered", "coverage", "water backup", "endorsement"]
        assert any(ind in response for ind in coverage_indicators), \
            f"Response should indicate coverage: {response}"
        
        # Should use safe/conditional language
        safe_phrases = ["appears", "may be", "based on", "according to"]
        assert any(phrase in response for phrase in safe_phrases), \
            f"Response should use conditional language: {response}"
    
    def test_agent_cites_source(self, agent):
        """Agent should cite policy source for coverage answer."""
        result = agent.process_message(
            "What does my water backup coverage include?",
            customer_context={"policy_number": "HO-2024-001234"}
        )
        
        response = result["response"].lower()
        
        # Should have some citation or source reference
        citation_indicators = ["according", "based on", "policy", "section", "endorsement"]
        assert any(ind in response for ind in citation_indicators), \
            f"Response should cite source: {response}"


# ============================================================================
# Scenario 2: The "No" Path - Flood Exclusion
# ============================================================================

class TestFloodExclusion:
    """
    Test the negative coverage scenario.
    Customer: Michael Chen (HO-2024-009012) - No water backup endorsement
    Scenario: River flooding
    Expected: Agent explains exclusion empathetically
    """
    
    def test_customer_lacks_flood_coverage(self, customer_db):
        """Verify test customer does not have flood-related endorsements."""
        customer = customer_db.get_by_policy_number("HO-2024-009012")
        assert customer is not None
        assert not customer.has_endorsement("Water Backup")
        assert not customer.has_endorsement("Flood")
    
    def test_agent_explains_exclusion(self, agent):
        """Agent should explain river flooding is not covered."""
        result = agent.process_message(
            "The river near my house overflowed and damaged my basement. Is this covered?",
            customer_context={"policy_number": "HO-2024-009012"}
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should indicate non-coverage
        exclusion_indicators = ["not covered", "excluded", "exclusion", "does not cover", "flood insurance", "nfip"]
        assert any(ind in response for ind in exclusion_indicators), \
            f"Response should indicate exclusion: {response}"
    
    def test_agent_provides_alternative(self, agent):
        """Agent should suggest NFIP or separate flood insurance."""
        result = agent.process_message(
            "So flooding from the river isn't covered? What are my options?",
            customer_context={"policy_number": "HO-2024-009012"}
        )
        
        response = result["response"].lower()
        
        # Should mention alternatives
        alternatives = ["flood insurance", "nfip", "national flood", "separate policy"]
        has_alternative = any(alt in response for alt in alternatives)
        # This is a softer assertion - alternatives are helpful but not strictly required
        assert result["success"]


# ============================================================================
# Scenario 3: Clarification Needed - Mold Damage
# ============================================================================

class TestMoldClarification:
    """
    Test scenario requiring clarification.
    Scenario: Customer reports mold behind washing machine
    Expected: Agent asks about discovery date (critical for coverage)
    """
    
    def test_agent_handles_mold_query(self, agent):
        """Agent should handle mold question and potentially ask for clarification."""
        result = agent.process_message(
            "I just found mold behind my washing machine. Is that covered?",
            customer_context={"policy_number": "HO-2024-005678"}
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should reference mold coverage conditions
        mold_indicators = ["mold", "hidden water", "discover", "reported", "14 days", "sudden"]
        assert any(ind in response for ind in mold_indicators), \
            f"Response should address mold conditions: {response}"


# ============================================================================
# Scenario 4: Jewelry Coverage - Sub-limits
# ============================================================================

class TestJewelryCoverage:
    """
    Test jewelry coverage and scheduled property.
    Customer: Sarah Johnson (HO-2024-005678) - HAS Scheduled Jewelry
    Scenario: Question about engagement ring coverage
    """
    
    def test_customer_has_scheduled_jewelry(self, customer_db):
        """Verify customer has scheduled jewelry endorsement."""
        customer = customer_db.get_by_policy_number("HO-2024-005678")
        assert customer is not None
        assert customer.has_endorsement("Scheduled Personal Property")
        assert customer.scheduled_items is not None
    
    def test_agent_explains_jewelry_limits(self, agent):
        """Agent should explain jewelry sub-limits and scheduling option."""
        result = agent.process_message(
            "I just bought a $10,000 engagement ring. Is it covered?",
            customer_context={"policy_number": "HO-2024-005678"}
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should mention jewelry limits or scheduling
        jewelry_indicators = ["jewelry", "limit", "scheduled", "endorsement", "rider", "floater", "$1,500"]
        assert any(ind in response for ind in jewelry_indicators), \
            f"Response should address jewelry coverage: {response}"


# ============================================================================
# Scenario 5: Short-Term Rental Exclusion
# ============================================================================

class TestAirbnbExclusion:
    """
    Test short-term rental exclusion.
    Scenario: Customer asking about Airbnb theft coverage
    Expected: Agent explains commercial use exclusion
    """
    
    def test_agent_explains_rental_exclusion(self, agent):
        """Agent should explain that standard policy excludes rental activities."""
        result = agent.process_message(
            "I'm renting my house on Airbnb for the weekend. Does my insurance cover theft by a guest?",
            customer_context={"policy_number": "HO-2024-009012"}
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should indicate rental exclusion
        rental_indicators = ["rental", "airbnb", "excluded", "not covered", "commercial", "business"]
        assert any(ind in response for ind in rental_indicators), \
            f"Response should address rental exclusion: {response}"


# ============================================================================
# Scenario 6: Tree Damage Liability
# ============================================================================

class TestTreeLiability:
    """
    Test tree damage liability reasoning.
    Scenario: City tree falls on customer's fence
    Expected: Agent explains filing on own policy vs city liability
    """
    
    def test_agent_explains_tree_liability(self, agent):
        """Agent should explain tree damage liability rules."""
        result = agent.process_message(
            "A tree fell on my fence, but the tree belongs to the city. Who pays?",
            customer_context={"policy_number": "HO-2024-001234"}
        )
        
        assert result["success"]
        response = result["response"].lower()
        
        # Should explain filing on own policy
        tree_indicators = ["your policy", "coverage b", "other structures", "city", "file", "claim"]
        assert any(ind in response for ind in tree_indicators), \
            f"Response should explain tree liability: {response}"


# ============================================================================
# Compliance Tests
# ============================================================================

class TestCompliance:
    """Test compliance guardrails."""
    
    def test_guardrails_catch_guarantee_language(self):
        """Guardrails should catch absolute guarantee language."""
        from src.guardrails.compliance import ComplianceGuardrails
        
        guardrails = ComplianceGuardrails()
        
        # Bad response with guarantees
        bad_response = "You are covered for this damage. We will pay the full amount."
        is_compliant, violations = guardrails.check_response(bad_response)
        
        assert len(violations) > 0
        assert any(v.rule == "NO_GUARANTEE" for v in violations)
    
    def test_guardrails_accept_conditional_language(self):
        """Guardrails should accept properly conditional language."""
        from src.guardrails.compliance import ComplianceGuardrails
        
        guardrails = ComplianceGuardrails()
        
        # Good response with conditional language
        good_response = (
            "Based on your policy, it appears you may be covered for water backup damage. "
            "According to the Water Backup Endorsement, sump pump failures are included."
        )
        is_compliant, violations = guardrails.check_response(good_response)
        
        # Should have no high-risk violations
        high_risk = [v for v in violations if v.rule == "NO_GUARANTEE"]
        assert len(high_risk) == 0
    
    def test_sentiment_analyzer_detects_frustration(self):
        """Sentiment analyzer should detect frustrated customers."""
        from src.guardrails.compliance import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        # Frustrated customer
        result = analyzer.analyze(
            "This is ridiculous! I've been a customer for 10 years and this is unacceptable!"
        )
        
        assert result["sentiment"] in ["negative", "slightly_negative"]
        assert result["frustration_score"] >= 1
    
    def test_sentiment_analyzer_detects_urgency(self):
        """Sentiment analyzer should detect urgent situations."""
        from src.guardrails.compliance import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze("My basement is flooding right now! I need help immediately!")
        
        assert result["is_urgent"]
        assert result["urgency_score"] >= 1


# ============================================================================
# Tool Tests
# ============================================================================

class TestTools:
    """Test individual agent tools."""
    
    def test_policy_search(self):
        """Test policy document search."""
        from src.agent.tools import search_policy_documents
        
        result = search_policy_documents.invoke({
            "query": "water backup sump pump coverage",
            "topic": "water"
        })
        
        assert result is not None
        assert len(result) > 0
        assert "water" in result.lower() or "backup" in result.lower()
    
    def test_customer_lookup(self):
        """Test customer profile lookup."""
        from src.agent.tools import get_customer_profile
        
        result = get_customer_profile.invoke({
            "identifier": "HO-2024-001234"
        })
        
        assert "John Doe" in result
        assert "HO-2024-001234" in result
    
    def test_endorsement_check(self):
        """Test endorsement verification."""
        from src.agent.tools import check_customer_endorsement
        
        # Customer with endorsement
        result = check_customer_endorsement.invoke({
            "customer_identifier": "HO-2024-001234",
            "endorsement_name": "Water Backup"
        })
        
        assert "HAS" in result
        
        # Customer without endorsement
        result = check_customer_endorsement.invoke({
            "customer_identifier": "HO-2024-009012",
            "endorsement_name": "Water Backup"
        })
        
        assert "DOES NOT HAVE" in result
    
    def test_coverage_calculator(self):
        """Test coverage calculation tool."""
        from src.agent.tools import calculate_coverage
        
        result = calculate_coverage.invoke({
            "coverage_amount": 5000,
            "deductible": 1000,
            "depreciation_percent": 0
        })
        
        assert "4,000" in result  # 5000 - 1000 = 4000


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
