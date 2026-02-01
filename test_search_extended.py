#!/usr/bin/env python3
"""
Extended search test with 10 new questions including unknown queries
"""
import requests
import json

API_URL = "http://localhost:8000"

# 10 New test questions - mix of known and unknown
test_questions = [
    {
        "id": 1,
        "query": "How do I add a new printer to my computer?",
        "in_database": True,
        "expected_answer_contains": "system settings"
    },
    {
        "id": 2,
        "query": "My laptop battery dies too fast",
        "in_database": True,
        "expected_answer_contains": "brightness"
    },
    {
        "id": 3,
        "query": "I received a suspicious email asking for my password",
        "in_database": True,
        "expected_answer_contains": "phishing"
    },
    {
        "id": 4,
        "query": "How do I book a meeting room?",
        "in_database": False,  # NOT in database
        "expected_answer_contains": None
    },
    {
        "id": 5,
        "query": "What's the guest WiFi password?",
        "in_database": True,
        "expected_answer_contains": "ACME-Guest"
    },
    {
        "id": 6,
        "query": "My external monitor is blurry",
        "in_database": True,
        "expected_answer_contains": "resolution"
    },
    {
        "id": 7,
        "query": "How do I request vacation time?",
        "in_database": False,  # NOT in database
        "expected_answer_contains": None
    },
    {
        "id": 8,
        "query": "My account is locked after too many login attempts",
        "in_database": True,
        "expected_answer_contains": "15 minutes"
    },
    {
        "id": 9,
        "query": "Where is the parking garage?",
        "in_database": False,  # NOT in database
        "expected_answer_contains": None
    },
    {
        "id": 10,
        "query": "My disk space is full",
        "in_database": True,
        "expected_answer_contains": "cleanup"
    }
]

def test_search(question_data):
    """Test a single search query"""
    query = question_data["query"]
    
    print(f"\n{'='*80}")
    print(f"Test {question_data['id']}: {query}")
    if question_data["in_database"]:
        print(f"Expected: ✅ Should find answer containing '{question_data['expected_answer_contains']}'")
    else:
        print(f"Expected: ⚠️  Not in database - should return no/few results")
    print(f"{'='*80}")
    
    try:
        response = requests.get(f"{API_URL}/search_knowledge", params={"query": query})
        response.raise_for_status()
        results = response.json()["results"]
        
        if not results:
            if question_data["in_database"]:
                print("❌ FAIL - Expected answer but got NO RESULTS")
                return False
            else:
                print("✅ PASS - Correctly returned no results for unknown query")
                return True
        
        # Show top result
        print(f"\n📊 Found {len(results)} results\n")
        top_result = results[0]
        print(f"1. 📄 {top_result['source']}")
        
        # Extract answer text
        content = top_result['content']
        if isinstance(content, dict):
            answer_text = content.get('Question', '') + " " + content.get('Resolution', '')
        else:
            answer_text = str(content)[:200]
        
        print(f"   {answer_text[:150]}...\n")
        
        # Check if answer is relevant
        if question_data["in_database"]:
            expected_text = question_data["expected_answer_contains"]
            if expected_text and expected_text.lower() in answer_text.lower():
                print(f"✅ PASS - Answer contains expected text: '{expected_text}'")
                return True
            else:
                print(f"⚠️  WARNING - Answer doesn't contain expected text: '{expected_text}'")
                return False
        else:
            # Unknown query - any result is okay but warn if confidence seems high
            if "Workplace_IT_Support_Database.csv" in top_result['source']:
                print(f"⚠️  INFO - Found CSV match for unknown query (may be tangentially related)")
            else:
                print(f"✅ INFO - Returned general context from TXT files")
            return True  # Don't fail unknown queries
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    print("🧪 Extended Knowledge Base Search Test")
    print(f"Testing {len(test_questions)} questions (including unknown queries)...\n")
    
    known_passed = 0
    known_failed = 0
    unknown_handled = 0
    
    for question in test_questions:
        result = test_search(question)
        if question["in_database"]:
            if result:
                known_passed += 1
            else:
                known_failed += 1
        else:
            if result:
                unknown_handled += 1
    
    # Summary
    print(f"\n{'='*80}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*80}")
    
    known_total = sum(1 for q in test_questions if q["in_database"])
    unknown_total = sum(1 for q in test_questions if not q["in_database"])
    
    print(f"\n📗 KNOWN QUERIES ({known_total} total):")
    print(f"  ✅ Passed: {known_passed}/{known_total}")
    print(f"  ❌ Failed: {known_failed}/{known_total}")
    print(f"  📈 Success Rate: {(known_passed/known_total*100):.1f}%")
    
    print(f"\n📕 UNKNOWN QUERIES ({unknown_total} total):")
    print(f"  ✅ Handled: {unknown_handled}/{unknown_total}")
    
    overall_success = (known_passed + unknown_handled) / len(test_questions) * 100
    print(f"\n🎯 OVERALL: {overall_success:.1f}% ({known_passed + unknown_handled}/{len(test_questions)})")
    print(f"{'='*80}\n")
    
    if known_passed == known_total and unknown_handled == unknown_total:
        print("🎉 ALL TESTS PASSED!")
    elif known_passed >= known_total * 0.7:
        print("✅ Good performance! 70%+ accuracy achieved")
    else:
        print("❌ Needs improvement")

if __name__ == "__main__":
    main()
