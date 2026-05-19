"""
Home Assistant tool — control HA devices via REST API.

Requires in .env:
    HA_URL=http://localhost:8123
    HA_TOKEN=<long-lived access token>
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

HA_URL = os.getenv("HA_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}


def _api_get(endpoint: str) -> dict | list | None:
    """GET request to HA API."""
    try:
        r = requests.get(f"{HA_URL}/api/{endpoint}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.error(f"HA API GET error: {e}")
        return None


def _api_post(endpoint: str, payload: dict = None) -> dict | list | None:
    """POST request to HA API."""
    try:
        r = requests.post(
            f"{HA_URL}/api/{endpoint}",
            headers=HEADERS,
            json=payload or {},
            timeout=10,
        )
        r.raise_for_status()
        # Some HA endpoints return empty 200
        return r.json() if r.text else {"status": "ok"}
    except requests.RequestException as e:
        logger.error(f"HA API POST error: {e}")
        return None


# ---------------------------------------------------------------------------
# Device discovery
# ---------------------------------------------------------------------------

def list_devices() -> str:
    """List all HA entities grouped by domain (switch, light, etc.)."""
    states = _api_get("states")
    if not states:
        return "Failed to connect to Home Assistant."

    # Group by domain
    grouped: dict[str, list[str]] = {}
    for entity in states:
        entity_id = entity["entity_id"]
        domain = entity_id.split(".")[0]
        friendly = entity["attributes"].get("friendly_name", entity_id)
        state = entity["state"]
        grouped.setdefault(domain, []).append(f"  {friendly} ({entity_id}) — {state}")

    # Only show actionable domains
    relevant = ["switch", "light", "cover", "fan", "climate", "media_player", "lock"]
    lines = []
    for domain in relevant:
        if domain in grouped:
            lines.append(f"\n{domain.upper()}:")
            lines.extend(grouped[domain])

    return "\n".join(lines) if lines else "No controllable devices found."


# ---------------------------------------------------------------------------
# Turn on / off / toggle
# ---------------------------------------------------------------------------

def turn_on(entity_id: str) -> str:
    """Turn on any HA entity (switch, light, etc.)."""
    domain = entity_id.split(".")[0]
    result = _api_post(f"services/{domain}/turn_on", {"entity_id": entity_id})
    if result is not None:
        return f"Turned on {entity_id}"
    return f"Failed to turn on {entity_id}"


def turn_off(entity_id: str) -> str:
    """Turn off any HA entity."""
    domain = entity_id.split(".")[0]
    result = _api_post(f"services/{domain}/turn_off", {"entity_id": entity_id})
    if result is not None:
        return f"Turned off {entity_id}"
    return f"Failed to turn off {entity_id}"


def toggle(entity_id: str) -> str:
    """Toggle any HA entity."""
    domain = entity_id.split(".")[0]
    result = _api_post(f"services/{domain}/toggle", {"entity_id": entity_id})
    if result is not None:
        return f"Toggled {entity_id}"
    return f"Failed to toggle {entity_id}"


# ---------------------------------------------------------------------------
# State queries
# ---------------------------------------------------------------------------

def get_state(entity_id: str) -> str:
    """Get current state of a specific entity."""
    state = _api_get(f"states/{entity_id}")
    if not state:
        return f"Could not get state for {entity_id}"

    friendly = state["attributes"].get("friendly_name", entity_id)
    current = state["state"]

    # Include useful attributes
    attrs = state.get("attributes", {})
    extras = []
    if "current_power_w" in attrs:
        extras.append(f"Power: {attrs['current_power_w']}W")
    if "current" in attrs:
        extras.append(f"Current: {attrs['current']}A")
    if "voltage" in attrs:
        extras.append(f"Voltage: {attrs['voltage']}V")
    if "temperature" in attrs:
        extras.append(f"Temp: {attrs['temperature']}°")
    if "brightness" in attrs:
        extras.append(f"Brightness: {round(attrs['brightness'] / 255 * 100)}%")

    extra_str = f" ({', '.join(extras)})" if extras else ""
    return f"{friendly}: {current}{extra_str}"


def get_all_states() -> str:
    """Get states of all controllable entities."""
    states = _api_get("states")
    if not states:
        return "Failed to connect to Home Assistant."

    relevant = ["switch", "light", "cover", "fan", "climate", "media_player", "lock"]
    lines = []
    for entity in states:
        domain = entity["entity_id"].split(".")[0]
        if domain in relevant:
            friendly = entity["attributes"].get("friendly_name", entity["entity_id"])
            lines.append(f"{friendly}: {entity['state']}")

    return "\n".join(lines) if lines else "No controllable devices found."


# ---------------------------------------------------------------------------
# Convenience wrappers for common commands
# ---------------------------------------------------------------------------

def all_off() -> str:
    """Turn off all switches and lights."""
    states = _api_get("states")
    if not states:
        return "Failed to connect to Home Assistant."

    turned_off = []
    for entity in states:
        eid = entity["entity_id"]
        domain = eid.split(".")[0]
        if domain in ["switch", "light"] and entity["state"] == "on":
            turn_off(eid)
            friendly = entity["attributes"].get("friendly_name", eid)
            turned_off.append(friendly)

    if turned_off:
        return f"Turned off: {', '.join(turned_off)}"
    return "Everything is already off."


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    # Reinitialize after loading env
    HA_TOKEN = os.getenv("HA_TOKEN", "")
    HEADERS["Authorization"] = f"Bearer {HA_TOKEN}"

    print("=== HA Devices ===")
    print(list_devices())
    print("\n=== All States ===")
    print(get_all_states())