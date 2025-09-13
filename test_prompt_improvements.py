#!/usr/bin/env python3
"""
Test the enhanced prompt builder and DOM processor fixes.
This tests both the line formatting and group/catering filtering.
"""

from tools.web_automation.prompt_builder import SYSTEM_INSTRUCTIONS

def test_prompt_formatting():
    """Test that system instructions are properly formatted with newlines."""
    print("🧪 Testing prompt formatting...")
    
    # Check that instructions have proper line breaks
    line_count = SYSTEM_INSTRUCTIONS.count('\n')
    print(f"📏 System instructions contain {line_count} line breaks")
    
    # Check for key sections
    sections = ["CONTEXTUAL AWARENESS:", "SELECTION POLICY", "DISQUALIFIERS", "PREFERENCES"]
    for section in sections:
        if section in SYSTEM_INSTRUCTIONS:
            print(f"✅ Found section: {section}")
        else:
            print(f"❌ Missing section: {section}")
    
    # Check for group/catering disqualifiers
    if "group order" in SYSTEM_INSTRUCTIONS and "catering" in SYSTEM_INSTRUCTIONS:
        print("✅ Group/catering disqualifiers present")
    else:
        print("❌ Group/catering disqualifiers missing")
        
    # Check for serving size disqualifiers
    if "serves X" in SYSTEM_INSTRUCTIONS or "serves 4-6" in SYSTEM_INSTRUCTIONS:
        print("✅ Serving size disqualifiers present")
    else:
        print("❌ Serving size disqualifiers missing")
        
    print("\n� System Instructions Preview:")
    print("=" * 60)
    print(SYSTEM_INSTRUCTIONS[:500] + "..." if len(SYSTEM_INSTRUCTIONS) > 500 else SYSTEM_INSTRUCTIONS)
    print("=" * 60)

if __name__ == "__main__":
    test_prompt_formatting()
    print("\n✅ Testing completed!")
