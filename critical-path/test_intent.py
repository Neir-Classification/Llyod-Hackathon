"""Test the updated intent detection for serious situations."""
from main import detect_intent_fast, get_quick_response_text

test_cases = [
    "my house got burned down",
    "my car was stolen last night", 
    "I had a car accident",
    "someone broke into my house",
    "there was a flood in my basement",
    "I crashed my car and I'm hurt",
    "what is my coverage",
    "hello",
    "how do I file a claim",
    "my roof is damaged from the storm",
]

print("=" * 80)
print("INTENT DETECTION TEST")
print("=" * 80)

for query in test_cases:
    intent, confidence = detect_intent_fast(query)
    quick_response = get_quick_response_text(intent, "neutral", query)
    
    print(f"\nQuery: \"{query}\"")
    print(f"  Intent: {intent} (confidence: {confidence:.2f})")
    print(f"  Quick Response: \"{quick_response}\"")

print("\n" + "=" * 80)
