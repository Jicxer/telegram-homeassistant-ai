import requests
import os

def get_weather(location: str = None) -> str:
    """Fetch current weather for a location using wttr.in (no API key needed)."""
    location = location or os.getenv("WEATHER_LOCATION", "Portland,OR")
    location = location.replace(" ", "+")

    try:
        response = requests.get(
            f"https://wttr.in/{location}?format=3",
            timeout=5
        )
        response.raise_for_status()
        return response.text.strip()
    except requests.RequestException as e:
        return f"Could not fetch weather: {e}"
