def flight_planner(origin: str, destination: str, departure_date: str, return_date: str):
    """
    A mock tool that simulates finding flights.
    """
    print(f"✈️ MOCK TOOL: Searching for flights from {origin} to {destination}...")
    
    # Return a fake, but realistically structured, piece of data
    return {
        "status": "success",
        "search_parameters": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date
        },
        "flight_options": [
            {
                "airline": "Spirit",
                "price": 450.78,
                "stops": 1,
                "departure_time": "08:30 AM"
            },
            {
                "airline": "Delta",
                "price": 620.50,
                "stops": 0,
                "departure_time": "10:15 AM"
            }
        ]
    }