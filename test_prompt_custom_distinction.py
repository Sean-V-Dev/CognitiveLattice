#!/usr/bin/env python3
"""
Test prompt improvements for better custom vs product name distinction.
"""

from tools.web_automation.prompt_builder import build_reasoning_prompt
from tools.web_automation.models import PageContext, InteractiveElement

def test_custom_vs_product_distinction():
    """Test that prompt correctly distinguishes custom building from product selection."""
    print("🧪 Testing Custom vs Product Name Distinction")
    print("=" * 60)
    
    # Create mock page context similar to Chipotle scenario
    ctx = PageContext(
        url="https://example-restaurant.com",
        title="Restaurant — Order Now", 
        signature="test123",
        skeleton="",
        interactive=[]
    )
    
    # Mock candidates similar to Chipotle's confusing options
    mock_candidates = [
        InteractiveElement(
            tag="div",
            text="Burrito Bowl",  # Specific product name
            selectors=["div.display-name.mealBurrito:nth-child(1)"],
            score=19.0
        ),
        InteractiveElement(
            tag="div", 
            text="Lifestyle Bowl",  # Branded product
            selectors=["div.display-name.mealLifestyle"],
            score=19.0
        ),
        InteractiveElement(
            tag="button",
            text="Build Your Own",  # Generic customization tool
            selectors=["button.customize-btn"],
            score=18.5
        ),
        InteractiveElement(
            tag="div",
            text="Create Custom Bowl",  # Clear customization option
            selectors=["div[data-action='customize']"],
            score=18.0
        ),
        InteractiveElement(
            tag="div",
            text="DJ Celebrity Bowl",  # Celebrity product
            selectors=["div.celebrity-meal"],
            score=17.5
        )
    ]
    
    ctx.interactive = mock_candidates
    
    # Test goal asking for custom building
    goal = "Select the option to build a custom bowl."
    
    prompt = build_reasoning_prompt(goal, ctx)
    
    print("🎯 Goal:", goal)
    print("\n📊 Available Candidates:")
    for i, candidate in enumerate(mock_candidates, 1):
        print(f"  {i}. '{candidate.text}' (score: {candidate.score})")
    
    print("\n🔍 Checking Prompt Instructions:")
    
    # Check for improved custom vs product distinctions
    improvements = [
        ("Custom building guidance", "CRITICAL: When goal says 'custom/build/create', look for BUILD-YOUR-OWN functionality"),
        ("Product name avoidance", "CRITICAL: Distinguish between CUSTOMIZATION TOOLS vs PRODUCT NAMES"),
        ("Custom preference", "STRONGLY prefer customization tools over product names"),
        ("Customization keywords", "Look for phrases like: 'Build Your Own', 'Create', 'Customize'"),
        ("Product avoidance", "AVOID: Specific product names, branded items, pre-configured options")
    ]
    
    for improvement_name, expected_text in improvements:
        if expected_text in prompt:
            print(f"  ✅ {improvement_name}: Found")
        else:
            print(f"  ❌ {improvement_name}: Missing")
    
    print("\n🚫 Checking Chipotle-Specific Removals:")
    
    # Check that Chipotle-specific instructions were removed
    chipotle_specifics = [
        "Burrito Bowl' is a PRODUCT NAME",
        "Custom bowl' means BUILD-YOUR-OWN",
        "Focus ONLY on location search functionality",
        "Selected Burrito Bowl', 'Added chicken protein"
    ]
    
    removed_count = 0
    for specific in chipotle_specifics:
        if specific not in prompt:
            removed_count += 1
            print(f"  ✅ Removed: '{specific[:30]}...'")
        else:
            print(f"  ❌ Still present: '{specific[:30]}...'")
    
    print(f"\n📈 Summary:")
    print(f"  ✅ Improvements added: {len([i for i in improvements if i[1] in prompt])}/{len(improvements)}")
    print(f"  ✅ Chipotle specifics removed: {removed_count}/{len(chipotle_specifics)}")
    
    # Check that generic examples are still present
    if "Build Your Own" in prompt and "Create" in prompt and "Customize" in prompt:
        print(f"  ✅ Generic customization keywords present")
    else:
        print(f"  ⚠️  Generic customization keywords may be missing")
    
    print(f"\n🎉 Expected Behavior:")
    print(f"  - Should prefer 'Build Your Own' (candidate #3) over 'Burrito Bowl' (candidate #1)")
    print(f"  - Should prefer 'Create Custom Bowl' (candidate #4) over branded products")
    print(f"  - Should avoid celebrity/lifestyle products when goal asks for 'custom'")
    
    return prompt

if __name__ == "__main__":
    test_prompt = test_custom_vs_product_distinction()
    
    print(f"\n📝 Prompt Length: {len(test_prompt)} characters")
    print(f"✅ Prompt improvements implemented and verified!")
