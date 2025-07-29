def restaurant_selector(option_number: int, previous_restaurant_results: dict):
    """
    A tool that handles restaurant selection from previously searched results.
    Stores the selected restaurant reservation in a structured format.
    """
    print(f"🍽️ RESTAURANT SELECTION: User selected option {option_number}")
    
    # Extract the selected restaurant from previous results
    if "restaurant_options" in previous_restaurant_results:
        restaurant_options = previous_restaurant_results["restaurant_options"]
        
        if 1 <= option_number <= len(restaurant_options):
            selected_restaurant = restaurant_options[option_number - 1]
            
            # Add location information
            selected_restaurant_copy = selected_restaurant.copy()
            location_info = "Selected Location"  # Default fallback
            if 'search_parameters' in previous_restaurant_results:
                location = previous_restaurant_results['search_parameters'].get('location', 'Location')
                location_info = f"{location.title()}"
            selected_restaurant_copy['location'] = location_info
            
            # Create structured itinerary update
            itinerary_update = {
                "restaurant_reservation": f"{selected_restaurant['name']} table reserved",
                "reservation_time": selected_restaurant['available_time'],
                "party_size": previous_restaurant_results['search_parameters']['party_size'],
                "booking_status": "pending_confirmation",
                "reservation_date": previous_restaurant_results['search_parameters']['date']
            }
            
            specialties_text = ", ".join(selected_restaurant['specialties'][:2])
            
            return {
                "status": "success",
                "selection_made": True,
                "selected_option": option_number,
                "option_number": option_number,
                "selected_restaurant": selected_restaurant_copy,
                "itinerary_update": itinerary_update,
                "confirmation_message": f"Perfect! You've reserved a table at {selected_restaurant['name']} for {selected_restaurant['available_time']}. This {selected_restaurant['rating']}-star {selected_restaurant['cuisine']} restaurant is known for {specialties_text}.",
                "next_steps": "Your dining reservation is set! Continue with your trip planning."
            }
        else:
            return {
                "status": "error",
                "message": f"Invalid option {option_number}. Please choose from options 1-{len(restaurant_options)}."
            }
    else:
        return {
            "status": "error", 
            "message": "No previous restaurant search results found. Please search for restaurants first."
        }
