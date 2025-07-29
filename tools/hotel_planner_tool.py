def hotel_planner(location: str, checkin_date: str = "2025-07-29", checkout_date: str = "2025-08-01"):
    """
    A mock hotel search tool that returns sample accommodation options.
    In a real implementation, this would call hotel booking APIs.
    """
    print(f"🏨 SEARCHING HOTELS: {location} from {checkin_date} to {checkout_date}")
    
    # Mock hotel search results
    hotel_options = [
        {
            "name": "Ocean View Resort",
            "price": 189.99,
            "rating": 4.5,
            "amenities": ["Pool", "Beach Access", "Free WiFi"],
            "room_type": "Ocean View Suite"
        },
        {
            "name": "Downtown Comfort Inn", 
            "price": 129.99,
            "rating": 4.2,
            "amenities": ["Free Breakfast", "Fitness Center", "Business Center"],
            "room_type": "Standard King Room"
        }
    ]
    
    return {
        "status": "success",
        "search_parameters": {
            "location": location.lower(),
            "checkin_date": checkin_date,
            "checkout_date": checkout_date
        },
        "hotel_options": hotel_options
    }
