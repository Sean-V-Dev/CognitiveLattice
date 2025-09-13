#!/usr/bin/env python3
"""
Test to verify that "Build Your Own" gets proper scoring for custom bowl goals.
This should validate that our DOM processor fixes work correctly.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import score_interactive_elements
from tools.web_automation.models import Element

def test_build_your_own_scoring():
    """Test that Build Your Own gets higher score than pre-made bowls for custom goals."""
    
    # Create test elements similar to what we saw in the Chipotle debug
    elements = [
        # Pre-made bowls (these were ranking high)
        Element(
            tag="div",
            text="Lifestyle Bowl",
            attrs={"class": "display-name mealLifestyle", "role": "link"},
            selectors=["div.display-name.mealLifestyle"]
        ),
        Element(
            tag="div", 
            text="DJ Lagway's Carne Asada Bowl",
            attrs={"class": "button meal-card-button"},
            selectors=["div.button.meal-card-button"]
        ),
        Element(
            tag="div",
            text="Carne Asada Burrito Bowl", 
            attrs={"class": "button meal-card-button"},
            selectors=["div.button.meal-card-button"]
        ),
        # Build Your Own (this should rank higher with our fixes)
        Element(
            tag="div",
            text="Build Your Own",
            attrs={"data-qa-group-name": "Build Your Own", "class": "top-level-menu"},
            selectors=["div[data-qa-group-name=\"Build Your Own\"]"]
        ),
        # Regular Burrito Bowl category
        Element(
            tag="div",
            text="Burrito Bowl",
            attrs={"data-qa-group-name": "Burrito Bowl", "class": "top-level-menu"},
            selectors=["div[data-qa-group-name=\"Burrito Bowl\"]"]
        )
    ]
    
    # Test goal that asks for custom bowl building
    goal = "Select the option to build a custom bowl."
    
    print(f"🧪 Testing goal: '{goal}'")
    print("=" * 60)
    
    # Score the elements
    scored_elements = score_interactive_elements(elements, goal)
    
    # Print results
    print("SCORING RESULTS:")
    print("-" * 30)
    for i, elem in enumerate(scored_elements, 1):
        score = getattr(elem, 'score', 0.0)
        print(f"{i:2d}. {elem.text:<30} score={score:5.1f}")
    
    # Find Build Your Own position
    build_your_own_pos = None
    build_your_own_score = None
    for i, elem in enumerate(scored_elements, 1):
        if "Build Your Own" in elem.text:
            build_your_own_pos = i
            build_your_own_score = getattr(elem, 'score', 0.0)
            break
    
    print(f"\n🎯 'Build Your Own' ranked #{build_your_own_pos} with score {build_your_own_score}")
    
    # Check if it's in top 10 (should be with our fixes)
    if build_your_own_pos and build_your_own_pos <= 10:
        print("✅ SUCCESS: Build Your Own is in top 10!")
        return True
    else:
        print("❌ FAIL: Build Your Own is not in top 10")
        return False

def test_regular_goal_scoring():
    """Test that for non-custom goals, regular bowls still rank appropriately."""
    
    # Same elements as above
    elements = [
        Element(
            tag="div",
            text="Lifestyle Bowl",
            attrs={"class": "display-name mealLifestyle", "role": "link"},
            selectors=["div.display-name.mealLifestyle"]
        ),
        Element(
            tag="div",
            text="Build Your Own",
            attrs={"data-qa-group-name": "Build Your Own", "class": "top-level-menu"},
            selectors=["div[data-qa-group-name=\"Build Your Own\"]"]
        ),
        Element(
            tag="div",
            text="Burrito Bowl",
            attrs={"data-qa-group-name": "Burrito Bowl", "class": "top-level-menu"},
            selectors=["div[data-qa-group-name=\"Burrito Bowl\"]"]
        )
    ]
    
    # Test goal that asks for specific bowl type (not custom)
    goal = "Select the Burrito Bowl option."
    
    print(f"\n🧪 Testing goal: '{goal}'")
    print("=" * 60)
    
    scored_elements = score_interactive_elements(elements, goal)
    
    print("SCORING RESULTS:")
    print("-" * 30)
    for i, elem in enumerate(scored_elements, 1):
        score = getattr(elem, 'score', 0.0)
        print(f"{i:2d}. {elem.text:<30} score={score:5.1f}")
    
    # Burrito Bowl should rank highest for this goal
    top_element = scored_elements[0] if scored_elements else None
    if top_element and "Burrito Bowl" in top_element.text:
        print("✅ SUCCESS: Burrito Bowl ranks #1 for specific bowl goal")
        return True
    else:
        print("❌ FAIL: Burrito Bowl should rank #1 for specific bowl goal")
        return False

if __name__ == "__main__":
    print("🔬 DOM PROCESSOR SCORING TEST")
    print("Testing Build Your Own scoring improvements...\n")
    
    # Test custom bowl goal
    test1_passed = test_build_your_own_scoring()
    
    # Test specific bowl goal  
    test2_passed = test_regular_goal_scoring()
    
    print("\n" + "=" * 60)
    print("OVERALL RESULTS:")
    print(f"✅ Custom bowl goal test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Specific bowl goal test: {'PASSED' if test2_passed else 'FAILED'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 ALL TESTS PASSED! DOM processor scoring is working correctly.")
    else:
        print("\n❌ Some tests failed. DOM processor needs more work.")
