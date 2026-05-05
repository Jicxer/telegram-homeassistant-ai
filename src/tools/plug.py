import requests
import os

SHELLY_IP = os.getenv("SHELLY_DEVICE_IP")

def _rpc(method: str, params: dict = {}) -> dict:
    """Send a Gen2 RPC command to the Shelly device."""
    if not SHELLY_IP:
        return {"error": "SHELLY_DEVICE_IP not set in .env"}
    try:
        response = requests.get(
            f"http://{SHELLY_IP}/rpc/{method}",
            params=params,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": str(e)}

def turn_on() -> str:
    result = _rpc("Switch.Set", {"id": 0, "on": "true"})
    return "Plug turned on." if "error" not in result else f"Error: {result['error']}"

def turn_off() -> str:
    result = _rpc("Switch.Set", {"id": 0, "on": "false"})
    return "Plug turned off." if "error" not in result else f"Error: {result['error']}"

def get_status() -> str:
    result = _rpc("Switch.GetStatus", {"id": 0})
    if "error" in result:
        return f"Error: {result['error']}"
    state = "on" if result.get("output") else "off"
    return f"Plug is currently {state}."

def get_power() -> str:
    result = _rpc("Switch.GetStatus", {"id": 0})
    if "error" in result:
        return f"Error: {result['error']}"
    power   = result.get("apower", "N/A")
    voltage = result.get("voltage", "N/A")
    current = result.get("current", "N/A")
    temp    = result.get("temperature", {}).get("tC", "N/A")
    energy  = result.get("aenergy", {}).get("total", "N/A")
    return (
        f"⚡ Power: {power}W\n"
        f"🔌 Voltage: {voltage}V\n"
        f"💡 Current: {current}A\n"
        f"🌡️ Device temp: {temp}°C\n"
        f"📊 Total energy: {energy}Wh"
    )