"""Test the dual-pipeline intent detection and quick responses."""

from main import detect_intent_fast, get_quick_response_text, QUICK_RESPONSES

def test_intents():
    """Test various user queries and their detected intents."""
    test_cases = [
        ("I had an accident and my car is damaged", "claim"),
        ("What does my policy cover?", "coverage"),
        ("How much do I pay monthly?", "payment"),
        ("I want to cancel my policy", "cancel"),
        ("Hello, I need help", "greeting"),
        ("I'm so confused about my policy", "distress"),
        ("What is the deductible?", "question"),
    ]
    
    print("=" * 70)
    print("DUAL-PIPELINE INTENT DETECTION TEST")
    print("=" * 70)
    
    for query, expected_intent in test_cases:
        intent, confidence = detect_intent_fast(query)
        quick_response = get_quick_response_text(intent, "neutral", query)
        
        status = "✅" if intent == expected_intent else "⚠️"
        print(f"\n{status} Query: '{query}'")
        print(f"   Intent: {intent} (expected: {expected_intent}) | Confidence: {confidence:.2f}")
        print(f"   Quick Response: {quick_response}")

def test_tone_variations():
    """Test how tone affects quick responses."""
    query = "I had an accident"
    tones = ["neutral", "angry", "anxious", "confused", "happy"]
    
    print("\n" + "=" * 70)
    print("TONE VARIATION TEST")
    print("=" * 70)
    print(f"Query: '{query}'")
    
    for tone in tones:
        intent, _ = detect_intent_fast(query)
        quick_response = get_quick_response_text(intent, tone, query)
        print(f"\n   [{tone.upper()}]: {quick_response}")

def show_all_quick_responses():
    """Display all pre-cached quick responses."""
    print("\n" + "=" * 70)
    print("ALL QUICK RESPONSES (PRE-CACHED)")
    print("=" * 70)
    
    for key, response in QUICK_RESPONSES.items():
        print(f"   {key}: {response}")

if __name__ == "__main__":
    test_intents()
    test_tone_variations()
    show_all_quick_responses()
    
    print("\n" + "=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
