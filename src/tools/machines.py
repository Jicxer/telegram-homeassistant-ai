import os

def get_machine(name: str) -> dict | None:
    """Look up a machine's connection details from environment."""
    prefix = f"MACHINE_{name.upper()}"
    host = os.getenv(f"{prefix}_HOST")
    user = os.getenv(f"{prefix}_USER")
    if not host or not user:
        return None
    return {"host": host, "user": user}

def is_protected(name: str) -> bool:
    """Check if a machine is protected from destructive actions."""
    protected = os.getenv("PROTECTED_MACHINES", "").split(",")
    return name.lower().strip() in [p.lower().strip() for p in protected]

def list_machines() -> list[str]:
    """Return all configured machine names from environment."""
    machines = []
    for key in os.environ:
        if key.startswith("MACHINE_") and key.endswith("_HOST"):
            name = key[len("MACHINE_"):-len("_HOST")].lower()
            machines.append(name)
    return machines