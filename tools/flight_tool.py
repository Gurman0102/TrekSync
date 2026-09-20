import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

def search_flights(query):
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": API_KEY,
        "limit": 5
    }

    try:
        # Added timeout=10 to prevent the agent from hanging indefinitely 
        response = requests.get(url, params=params, timeout=10)
        
        # This will trigger the RequestException block if Aviationstack returns a 401, 403, 500, etc.
        response.raise_for_status() 
        
        data = response.json()
        flights = []

        if "data" in data and data["data"]:  
            for flight in data["data"][:5]:
                airline = flight.get("airline", {}).get("name", "Unknown")
                departure = flight.get("departure", {}).get("airport", "Unknown")
                arrival = flight.get("arrival", {}).get("airport", "Unknown")
                status = flight.get("flight_status", "Unknown")

                flights.append(
                    f"Airline: {airline}\n"
                    f"Departure: {departure}\n"
                    f"Arrival: {arrival}\n"
                    f"Status: {status}\n"
                )
            return "\n".join(flights)
        else:
            return "No active flights found for this route."

    except requests.exceptions.ConnectionError:
        return "Error: Unable to connect to the flight database (DNS resolution failed). Please check network connectivity."
    except requests.exceptions.Timeout:
        return "Error: The flight search API took too long to respond."
    except requests.exceptions.RequestException as e:
        return f"Error: An unexpected API issue occurred: {e}"
    except ValueError:
        return "Error: Received an invalid JSON response from the flight API."