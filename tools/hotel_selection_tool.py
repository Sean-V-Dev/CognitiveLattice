def hotel_selector(option_number: int, previous_hotel_results: dict):
    """
    A tool that handles hotel selection from previously searched results.
    Stores the selected hotel information in a structured format.
    """
    print(f"🏨 HOTEL SELECTION: User selected option {option_number}")
    
    # Extract the selected hotel from previous results
    if "hotel_options" in previous_hotel_results:
        hotel_options = previous_hotel_results["hotel_options"]
        
        if 1 <= option_number <= len(hotel_options):
            selected_hotel = hotel_options[option_number - 1]
            
            # Add location information
            selected_hotel_copy = selected_hotel.copy()
            location_info = "Selected Location"  # Default fallback
            if 'search_parameters' in previous_hotel_results:
                location = previous_hotel_results['search_parameters'].get('location', 'Location')
                location_info = f"{location.title()}"
            selected_hotel_copy['location'] = location_info
            
            # Create structured itinerary update
            itinerary_update = {
                "hotel_confirmation": f"{selected_hotel['name']} booking confirmed",
                "nightly_rate": selected_hotel['price'],
                "total_accommodation_cost": selected_hotel['price'] * 3,  # 3 nights
                "booking_status": "pending_confirmation",
                "check_in": previous_hotel_results['search_parameters']['checkin_date'],
                "check_out": previous_hotel_results['search_parameters']['checkout_date']
            }
            
            amenities_text = ", ".join(selected_hotel['amenities'][:3])
            
            return {
                "status": "success",
                "selection_made": True,
                "selected_option": option_number,
                "option_number": option_number,
                "selected_hotel": selected_hotel_copy,
                "itinerary_update": itinerary_update,
                "confirmation_message": f"Excellent choice! You've booked {selected_hotel['name']} for ${selected_hotel['price']:.2f}/night. This {selected_hotel['rating']}-star hotel includes {amenities_text}.",
                "next_steps": "Now let's look for dining options in the area!"
            }
        else:
            return {
                "status": "error",
                "message": f"Invalid option {option_number}. Please choose from options 1-{len(hotel_options)}."
            }
    else:
        return {
            "status": "error", 
            "message": "No previous hotel search results found. Please search for hotels first."
        }
