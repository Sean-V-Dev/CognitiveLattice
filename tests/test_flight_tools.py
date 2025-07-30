#!/usr/bin/env python3
"""
Test script for flight tool detection and execution
"""

from tool_manager import ToolManager

def test_flight_detection():
    print("🧪 Testing Flight Tool Detection and Execution")
    print("=" * 60)
    
    tm = ToolManager()
    print(f"Available tools: {list(tm.available_tools.keys())}")
    
    # Test flight search detection
    print("\n1. Testing Flight Search Detection:")
    search_tests = [
        "i want to fly from cincinnati to myrtle beach",
        "find flights from New York to Los Angeles", 
        "search for flights from Boston to Miami"
    ]
    
    for test in search_tests:
        print(f"\nTesting: '{test}'")
        tool_calls = tm.detect_tool_needs(test)
        if tool_calls:
            call = tool_calls[0]
            print(f"  ✅ Detected: {call['tool_name']}")
            print(f"     Origin: {call['parameters'].get('origin')}")
            print(f"     Destination: {call['parameters'].get('destination')}")
        else:
            print("  ❌ No tools detected")
    
    # Test flight selection detection
    print("\n2. Testing Flight Selection Detection:")
    selection_tests = [
        "i want option 1",
        "option 2",
        "choose option 1",
        "I'll take option 2 please",
        "1"
    ]
    
    # First simulate having flight results
    mock_flight_results = {
        "flight_options": [
            {"airline": "Spirit", "price": 450.78, "stops": 1},
            {"airline": "Delta", "price": 620.50, "stops": 0}
        ]
    }
    tm.recent_tool_results['flight_planner'] = mock_flight_results
    
    for test in selection_tests:
        print(f"\nTesting: '{test}'")
        tool_calls = tm.detect_tool_needs(test)
        if tool_calls:
            call = tool_calls[0]
            print(f"  ✅ Detected: {call['tool_name']}")
            print(f"     Option: {call['parameters'].get('option_number')}")
        else:
            print("  ❌ No tools detected")
    
    # Test full workflow
    print("\n3. Testing Full Workflow:")
    
    # Step 1: Search for flights
    search_query = "i want to fly from cincinnati to myrtle beach"
    print(f"\nStep 1 - Search: '{search_query}'")
    search_result = tm.enhance_llm_response(search_query)
    print(f"Tools used: {search_result['tools_used']}")
    if search_result['enhanced_response']:
        preview = search_result['enhanced_response'][:200].replace('\n', ' ')
        print(f"Response preview: {preview}...")
    
    # Step 2: Select a flight
    selection_query = "i want option 1"
    print(f"\nStep 2 - Selection: '{selection_query}'")
    selection_result = tm.enhance_llm_response(selection_query)
    print(f"Tools used: {selection_result['tools_used']}")
    if selection_result['enhanced_response']:
        preview = selection_result['enhanced_response'][:200].replace('\n', ' ')
        print(f"Response preview: {preview}...")
    
    print("\n" + "=" * 60)
    print("✅ Flight tool testing complete!")

if __name__ == "__main__":
    test_flight_detection()
