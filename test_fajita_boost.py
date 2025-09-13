#!/usr/bin/env python3
"""
Test the keyword boosting fix for Fajita Veggies case.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import score_interactive_elements
from tools.web_automation.models import Element

def test_fajita_veggies_scoring():
    """Test that Fajita Veggies gets proper keyword boost for the goal 'Add Fajita Veggies as a topping'."""
    print("🌶️ Testing Fajita Veggies Keyword Boosting")
    print("=" * 55)
    
    # Create mock elements similar to the Chipotle debug output
    elements = [
        # Top scoring element that shouldn't match the goal
        Element(
            tag="a",
            text="START A GROUP ORDER",
            attrs={"class": "aem-card__button cmp-button", "href": "/order/group/create"},
            selectors=["a.aem-card__button.cmp-button"],
            score=4.6
        ),
        # The Fajita Veggies element that should get massive boost
        Element(
            tag="div",
            text="Fajita Veggies", 
            attrs={
                "class": "meal-builder-item-selector-card-container",
                "data-qa-item-name": "Fajita Veggies",
                "data-qa-title": "Fajita Veggies",
                "data-qa-item-id": "CMG-5101"
            },
            selectors=["div[data-qa-item-name='Fajita Veggies']"],
            score=2.0  # Low initial score
        ),
        # Other food items for comparison
        Element(
            tag="div",
            text="Cheese",
            attrs={
                "class": "meal-builder-item-selector-card-container", 
                "data-qa-item-name": "Cheese",
                "data-qa-title": "Cheese"
            },
            selectors=["div[data-qa-item-name='Cheese']"],
            score=2.0
        ),
        Element(
            tag="div",
            text="Romaine Lettuce",
            attrs={
                "class": "meal-builder-item-selector-card-container",
                "data-qa-item-name": "Romaine Lettuce", 
                "data-qa-title": "Romaine Lettuce"
            },
            selectors=["div[data-qa-item-name='Romaine Lettuce']"],
            score=2.0
        ),
        # Generic high-scoring element
        Element(
            tag="a",
            text="ORDER NOW",
            attrs={"class": "aem-hero__button cmp-button", "href": "#menu"},
            selectors=["a.aem-hero__button.cmp-button"],
            score=3.8
        )
    ]
    
    # Test goal that should boost Fajita Veggies
    goal = "Add 'Fajita Veggies' as a topping."
    
    print(f"🎯 Goal: '{goal}'")
    print(f"📊 Initial scores:")
    for i, elem in enumerate(elements, 1):
        print(f"  {i}. '{elem.text}' - Score: {elem.score}")
    
    # Apply scoring 
    scored_elements = score_interactive_elements(elements, goal)
    
    print(f"\n📈 After keyword boosting:")
    for i, elem in enumerate(scored_elements, 1):
        print(f"  {i}. '{elem.text}' - Score: {elem.score:.1f}")
    
    # Check if Fajita Veggies is now at the top
    fajita_veggies = next((e for e in scored_elements if "Fajita Veggies" in e.text), None)
    
    if fajita_veggies:
        fajita_position = scored_elements.index(fajita_veggies) + 1
        print(f"\n🌶️ Fajita Veggies Analysis:")
        print(f"  Position: #{fajita_position}")
        print(f"  Final Score: {fajita_veggies.score:.1f}")
        print(f"  Has data-qa-item-name: {'data-qa-item-name' in fajita_veggies.attrs}")
        
        if fajita_position == 1:
            print(f"  ✅ SUCCESS: Fajita Veggies is now top candidate!")
        elif fajita_position <= 3:
            print(f"  ⚠️  PARTIAL: Fajita Veggies in top 3 but not #1")
        else:
            print(f"  ❌ FAILED: Fajita Veggies not in top candidates")
    else:
        print(f"  ❌ ERROR: Fajita Veggies element not found")
    
    # Test specific keyword matches
    print(f"\n🔍 Keyword Analysis:")
    goal_words = goal.lower().split()
    target_keywords = []
    skip_words = {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'as', 'add'}
    action_words = {'select', 'choose', 'pick', 'click', 'build', 'your', 'own', 'option', 'as', 'type', 'order', 'get', 'go', 'find', 'then', 'me', 'add'}
    
    for word in goal_words:
        clean_word = word.strip('.,!?;:"()[]{}').lower()
        if len(clean_word) >= 2 and clean_word not in skip_words and clean_word not in action_words:
            target_keywords.append(clean_word)
    
    print(f"  Target keywords extracted: {target_keywords}")
    
    if fajita_veggies:
        text_lower = fajita_veggies.text.lower()
        matches = [kw for kw in target_keywords if kw in text_lower]
        print(f"  Keywords found in 'Fajita Veggies': {matches}")
        print(f"  Expected boost: {len(matches) * 3.0} base + {len(matches) * 3.0 * 3.0} compound = {len(matches) * 12.0}")
    
    # Check for phrase match
    goal_phrase = goal.lower().replace("add", "").replace("'", "").replace('"', "").replace("as a topping", "").replace("as", "").strip()
    print(f"  Goal phrase for exact match: '{goal_phrase}'")
    if fajita_veggies and goal_phrase in fajita_veggies.text.lower():
        print(f"  ✅ Phrase match found - should get +5.0 boost")
    
    return scored_elements

if __name__ == "__main__":
    test_fajita_veggies_scoring()
    print(f"\n🌶️ Fajita Veggies keyword boosting test complete!")
