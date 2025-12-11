"""Test script for human handoff intent detection."""

import sys
sys.path.insert(0, '.')

from main import detect_intent_fast, get_quick_response_key, QUICK_RESPONSES

test_phrases = [
    "I want to talk to a human",
    "Can I speak to someone?",
    "Transfer me to an agent",
    "I need a real person",
    "Connect me to customer service",
    "I want to speak with a human agent",
    "Get me a manager",
    "This is not helpful, I want a person",
    "Can you transfer me?",
    "I need to talk to someone",
    "human please",
    "agent",
    "talk to human",
    "speak to human",
    # These should NOT trigger handoff
    "My house burned down",
    "I want to file a claim",
    "What is covered under my policy?",
]

print("=" * 60)
print("HUMAN HANDOFF INTENT DETECTION TEST")
print("=" * 60)

for phrase in test_phrases:
    intent, confidence = detect_intent_fast(phrase)
    response_key = get_quick_response_key(intent, "neutral", phrase)
    is_handoff = intent == "human_handoff"
    
    status = "✅ HANDOFF" if is_handoff else "❌ NOT HANDOFF"
    print(f"\n{status}")
    print(f"  Phrase: \"{phrase}\"")
    print(f"  Intent: {intent} (confidence: {confidence:.2f})")
    print(f"  Response Key: {response_key}")
    if is_handoff:
        print(f"  Response: {QUICK_RESPONSES.get(response_key, 'N/A')[:60]}...")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
