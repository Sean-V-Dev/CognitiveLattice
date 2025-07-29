def flight_selector(option_number: int, previous_flight_results: dict):
    """
    A tool that handles flight selection from previously searched results.
    Stores the selected flight information in a structured format.
    """
    print(f"✈️ FLIGHT SELECTION: User selected option {option_number}")
    
    # Extract the selected flight from previous results
    if "flight_options" in previous_flight_results:
        flight_options = previous_flight_results["flight_options"]
        
        if 1 <= option_number <= len(flight_options):
            selected_flight = flight_options[option_number - 1]
            
            # Create readable flight description
            stops_text = "direct" if selected_flight['stops'] == 0 else f"{selected_flight['stops']}-stop"
            
            # Add route information
            selected_flight_copy = selected_flight.copy()
            # Try to get route from search context if available
            route_info = "Selected Route"  # Default fallback
            if 'search_parameters' in previous_flight_results:
                origin = previous_flight_results['search_parameters'].get('origin', 'Origin')
                destination = previous_flight_results['search_parameters'].get('destination', 'Destination')
                route_info = f"{origin} → {destination}"
            selected_flight_copy['route'] = route_info
            
            # Create structured itinerary update
            itinerary_update = {
                "flight_confirmation": f"{selected_flight['airline']} flight selected",
                "total_cost": selected_flight['price'],
                "booking_status": "pending_confirmation",
                "travel_dates": {
                    "departure": "2025-07-29",
                    "return": "2025-08-01"
                }
            }
            
            return {
                "status": "success",
                "selection_made": True,
                "selected_option": option_number,
                "option_number": option_number,
                "selected_flight": selected_flight_copy,
                "itinerary_update": itinerary_update,
                "confirmation_message": f"Great choice! You've selected {selected_flight['airline']} for ${selected_flight['price']:.2f}. This {stops_text} flight departs at {selected_flight['departure_time']}.",
                "next_steps": "Now let's look for accommodation in Myrtle Beach!"
            }
        else:
            return {
                "status": "error",
                "message": f"Invalid option {option_number}. Please choose from options 1-{len(flight_options)}."
            }
    else:
            return {
                "status": "error", 
                "message": "No previous flight search results found. Please search for flights first."
            }