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

# Entity IDs containing any of these substrings are hidden from output.
# They're config/diagnostic entities, not things you'd toggle day-to-day.
HIDDEN_KEYWORDS = [
    "child_lock",
    "random_on_off",
    "charge_energy",
    "energy_total",
    "firmware",
    "restart",
    "rssi",
    "uptime",
    "update.",
]


def _is_hidden(entity_id: str) -> bool:
    """Return True if the entity should be hidden from user-facing output."""
    eid_lower = entity_id.lower()
    return any(kw in eid_lower for kw in HIDDEN_KEYWORDS)


def _friendly(entity: dict) -> str:
    """Get the friendly name, falling back to a cleaned entity_id."""
    name = entity.get("attributes", {}).get("friendly_name", "")
    if not name or name == entity["entity_id"]:
        # Clean up raw entity_id: switch.bedroom_lamp_socket_1 -> Bedroom Lamp Socket 1
        raw = entity["entity_id"].split(".", 1)[-1]
        name = raw.replace("_", " ").title()
    return name


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
        return r.json() if r.text else {"status": "ok"}
    except requests.RequestException as e:
        logger.error(f"HA API POST error: {e}")
        return None


# ---------------------------------------------------------------------------
# Device discovery
# ---------------------------------------------------------------------------

def list_devices() -> str:
    """List all HA entities grouped by domain, with entity_id for commands."""
    states = _api_get("states")
    if not states:
        return "Failed to connect to Home Assistant."

    relevant = ["switch", "light", "cover", "fan", "climate", "media_player", "lock"]
    grouped: dict[str, list[str]] = {}

    for entity in states:
        entity_id = entity["entity_id"]
        domain = entity_id.split(".")[0]
        if domain not in relevant or _is_hidden(entity_id):
            continue
        name = _friendly(entity)
        state = entity["state"]
        icon = "on" if state == "on" else "off"
        grouped.setdefault(domain, []).append(
            f"  [{icon}] {name}\n       /ha toggle {entity_id}"
        )

    lines = []
    for domain in relevant:
        if domain in grouped:
            lines.append(f"\n{domain.upper()}:")
            lines.extend(grouped[domain])

    return "\n".join(lines) if lines else "No controllable devices found."


# ---------------------------------------------------------------------------
# Turn on / off / toggle
# ---------------------------------------------------------------------------
def _resolve_entity(name_or_id: str) -> str | None:
    """Resolve a friendly name or partial match to an entity_id."""
    if "." in name_or_id:
        return name_or_id

    states = _api_get("states")
    if not states:
        return None

    name_lower = name_or_id.lower()

    # First pass: exact match
    for entity in states:
        if _is_hidden(entity["entity_id"]):
            continue
        friendly = _friendly(entity).lower()
        if name_lower == friendly:
            return entity["entity_id"]

    # Second pass: partial match
    for entity in states:
        if _is_hidden(entity["entity_id"]):
            continue
        friendly = _friendly(entity).lower()
        if name_lower in friendly:
            return entity["entity_id"]

    return None


def turn_on(entity_id: str) -> str:
    """Turn on any HA entity (switch, light, etc.)."""
    resolved = _resolve_entity(entity_id)
    if not resolved:
        return f"Could not find device matching '{entity_id}'"
    domain = resolved.split(".")[0]
    result = _api_post(f"services/{domain}/turn_on", {"entity_id": resolved})
    if result is None:
        return f"Failed to turn on {resolved}"
    state = _api_get(f"states/{resolved}")
    name = _friendly(state) if state else resolved
    return f"Turned on {name}"


def turn_off(entity_id: str) -> str:
    """Turn off any HA entity."""
    resolved = _resolve_entity(entity_id)
    if not resolved:
        return f"Could not find device matching '{entity_id}'"
    domain = resolved.split(".")[0]
    result = _api_post(f"services/{domain}/turn_off", {"entity_id": entity_id})
    if result is None:
        return f"Failed to turn off {entity_id}"
    state = _api_get(f"states/{entity_id}")
    name = _friendly(state) if state else entity_id
    return f"Turned off {name}"


def toggle(entity_id: str) -> str:
    """Toggle any HA entity."""
    domain = entity_id.split(".")[0]
    result = _api_post(f"services/{domain}/toggle", {"entity_id": entity_id})
    if result is None:
        return f"Failed to toggle {entity_id}"
    state = _api_get(f"states/{entity_id}")
    if state:
        name = _friendly(state)
        new_state = state["state"]
        return f"{name} is now {new_state}"
    return f"Toggled {entity_id}"


# ---------------------------------------------------------------------------
# State queries
# ---------------------------------------------------------------------------

def get_state(entity_id: str) -> str:
    """Get current state of a specific entity."""
    state = _api_get(f"states/{entity_id}")
    if not state:
        return f"Could not get state for {entity_id}"

    name = _friendly(state)
    current = state["state"]

    attrs = state.get("attributes", {})
    extras = []
    if "current_power_w" in attrs:
        extras.append(f"Power: {attrs['current_power_w']}W")
    if "current" in attrs:
        extras.append(f"Current: {attrs['current']}A")
    if "voltage" in attrs:
        extras.append(f"Voltage: {attrs['voltage']}V")
    if "temperature" in attrs:
        extras.append(f"Temp: {attrs['temperature']}deg")
    if "brightness" in attrs:
        extras.append(f"Brightness: {round(attrs['brightness'] / 255 * 100)}%")

    extra_str = f" ({', '.join(extras)})" if extras else ""
    return f"{name}: {current}{extra_str}"


def get_all_states() -> str:
    """Get states of all controllable entities, cleanly formatted."""
    states = _api_get("states")
    if not states:
        return "Failed to connect to Home Assistant."

    relevant = ["switch", "light", "cover", "fan", "climate", "media_player", "lock"]
    on_devices = []
    off_devices = []

    for entity in states:
        eid = entity["entity_id"]
        domain = eid.split(".")[0]
        if domain not in relevant or _is_hidden(eid):
            continue
        name = _friendly(entity)
        if entity["state"] == "on":
            on_devices.append(f"  [on]  {name}")
        else:
            off_devices.append(f"  [off] {name}")

    lines = []
    if on_devices:
        lines.append("ON:")
        lines.extend(on_devices)
    if off_devices:
        if on_devices:
            lines.append("")
        lines.append("OFF:")
        lines.extend(off_devices)

    return "\n".join(lines) if lines else "No controllable devices found."


# ---------------------------------------------------------------------------
# Convenience wrappers
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
        if domain in ["switch", "light"] and entity["state"] == "on" and not _is_hidden(eid):
            turn_off(eid)
            turned_off.append(_friendly(entity))

    if turned_off:
        return "Turned off:\n" + "\n".join(f"  - {name}" for name in turned_off)
    return "Everything is already off."


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    HA_TOKEN = os.getenv("HA_TOKEN", "")
    HEADERS["Authorization"] = f"Bearer {HA_TOKEN}"

    print("=== HA Devices ===")
    print(list_devices())
    print("\n=== All States ===")
    print(get_all_states())