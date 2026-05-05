import requests
import os

SHELLY_IP = os.getenv("SHELLY_DEVICE_IP")

def _request(action: str) -> dict:
    """Send a command to the Shelly plug."""
    if not SHELLY_IP:
        return {"error": "SHELLY_DEVICE_IP not set in .env"}
    try:
        response = requests.get(
            f"http://{SHELLY_IP}/relay/0",
            params={"turn": action},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def turn_on() -> str:
    result = _request("on")
    return "Plug turned on." if "error" not in result else f"Error: {result['error']}"

def turn_off() -> str:
    result = _request("off")
    return "Plug turned off." if "error" not in result else f"Error: {result['error']}"

def get_status() -> str:
    try:
        response = requests.get(f"http://{SHELLY_IP}/relay/0", timeout=5)
        data = response.json()
        state = "on" if data.get("ison") else "off"
        return f"Plug is currently {state}."
    except requests.RequestException as e:
        return f"Could not get plug status: {e}"
