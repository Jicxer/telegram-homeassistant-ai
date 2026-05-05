import requests
import os
from datetime import datetime

def get_weather(location: str = None) -> str:
    """Fetch current weather for a location using wttr.in."""
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

def get_forecast(location: str = None, days: int = 3) -> str:
    """Fetch multi-day forecast using wttr.in JSON API."""
    location = location or os.getenv("WEATHER_LOCATION", "Portland,OR")
    days = max(1, min(days, 3))  # clamp between 1 and 3
    location_query = location.replace(" ", "+")
    try:
        response = requests.get(
            f"https://wttr.in/{location_query}?format=j1",
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
        lines = [f"<b>Forecast for {location}</b>"]
        for day in data["weather"][:days]:
            date = datetime.strptime(day["date"], "%Y-%m-%d").strftime("%a %b %d")
            high = day["maxtempF"]
            low = day["mintempF"]
            desc = day["hourly"][4]["weatherDesc"][0]["value"]
            humidity = day["hourly"][4]["humidity"]
            wind = day["hourly"][4]["windspeedMiles"]
            wind_dir = day["hourly"][4]["winddir16Point"]
            precip = day["hourly"][4]["chanceofrain"]
            snow = day["hourly"][4]["chanceofsnow"]

            lines.append(
                f"\n<b>{date}</b>"
                f"\n{desc}"
                f"\nHigh {high}F  |  Low {low}F"
                f"\nHumidity: {humidity}%  |  Wind: {wind}mph {wind_dir}"
                f"\nRain: {precip}%  |  Snow: {snow}%"
            )
        return "\n".join(lines)
    except requests.RequestException as e:
        return f"Could not fetch forecast: {e}"
    except (KeyError, ValueError) as e:
        return f"Could not parse forecast data: {e}"