def restaurant_planner(location: str, date: str = "2025-07-29", party_size: int = 2):
    """
    A mock restaurant search tool that returns sample dining options.
    In a real implementation, this would call restaurant reservation APIs.
    """
    print(f"🍽️ SEARCHING RESTAURANTS: {location} for {party_size} people on {date}")
    
    # Mock restaurant search results
    restaurant_options = [
        {
            "name": "The Oceanfront Grill",
            "cuisine": "Seafood",
            "price_range": "$$$",
            "rating": 4.7,
            "available_time": "7:30 PM",
            "specialties": ["Fresh Lobster", "Grilled Mahi-Mahi", "Ocean View Dining"]
        },
        {
            "name": "Mario's Italian Bistro",
            "cuisine": "Italian", 
            "price_range": "$$",
            "rating": 4.4,
            "available_time": "6:00 PM",
            "specialties": ["Homemade Pasta", "Wood-Fired Pizza", "Wine Selection"]
        }
    ]
    
    return {
        "status": "success",
        "search_parameters": {
            "location": location.lower(),
            "date": date,
            "party_size": party_size
        },
        "restaurant_options": restaurant_options
    }
