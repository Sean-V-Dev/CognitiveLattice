# Test the enhanced goal-aware scoring for menu selection
goal = "Select 'Bowl' as the type of order you want to build."
goal_lower = goal.lower()

print(f'Goal: {goal}')
print(f'Goal lower: {goal_lower}')

# Check if this is a menu selection goal
is_menu_goal = (any(keyword in goal_lower for keyword in ['select', 'choose', 'pick']) and 
               any(food_type in goal_lower for food_type in ['bowl', 'burrito', 'taco', 'salad', 'quesadilla']))

print(f'Is menu selection goal: {is_menu_goal}')

if is_menu_goal:
    # Extract food items from goal
    goal_food_items = []
    for food_type in ['bowl', 'burrito', 'taco', 'salad', 'quesadilla', 'chips', 'drink', 'kids meal']:
        if food_type in goal_lower:
            goal_food_items.append(food_type)
    
    print(f'Goal food items: {goal_food_items}')
    
    # Test Burrito Bowl element
    text = 'Burrito Bowl'
    text_lower = text.lower()
    
    base_score = 1.5  # From current scoring
    menu_boost = 0
    
    # Check for exact menu item matches
    for food_item in goal_food_items:
        if food_item in text_lower:
            menu_boost += 6.0
            print(f'MENU BOOST: "{text}" gets +6.0 for "{food_item}" match')
    
    final_score = base_score + menu_boost
    print(f'\nBurrito Bowl scoring:')
    print(f'  Base score: {base_score}')
    print(f'  Menu boost: +{menu_boost}')
    print(f'  Final score: {final_score}')
    print(f'\nThis should now rank much higher in the candidates list!')
else:
    print('Not detected as menu goal - check goal detection logic')
