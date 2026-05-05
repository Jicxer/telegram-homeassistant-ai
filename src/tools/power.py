import subprocess
import os
from tools.machines import get_machine, is_protected

SSH_KEY = os.path.expanduser("~/.ssh/id_ed25519")

def _ssh(host: str, user: str, command: str) -> tuple[bool, str]:
    """Run a command on a remote machine via SSH."""
    try:
        result = subprocess.run(
            [
                "ssh",
                "-i", SSH_KEY,
                "-o", "StrictHostKeyChecking=yes",
                "-o", "ConnectTimeout=5",
                f"{user}@{host}",
                command
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "SSH connection timed out."
    except Exception as e:
        return False, str(e)

def _parse_time(when: str) -> tuple[str, str] | None:
    """
    Parse time argument into (shutdown_arg, human_readable).
    Accepts: 'now', '+N' (minutes), 'HH:MM' (absolute)
    Returns None if invalid.
    """
    when = when.strip().lower()
    if when == "now":
        return "now", "now"
    if when.startswith("+"):
        try:
            minutes = int(when[1:])
            return f"+{minutes}", f"in {minutes} minute{'s' if minutes != 1 else ''}"
        except ValueError:
            return None
    if ":" in when:
        parts = when.split(":")
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                return f"{h:02d}:{m:02d}", f"at {h:02d}:{m:02d}"
    return None

def shutdown(machine_name: str, when: str = "now") -> str:
    """Shutdown a target machine."""
    if is_protected(machine_name):
        return f" {machine_name} is protected and cannot be shut down remotely."
    machine = get_machine(machine_name)
    if not machine:
        return f" Unknown machine: '{machine_name}'. Check configuration."
    parsed = _parse_time(when)
    if not parsed:
        return " Invalid time format. Use: now, +10 (minutes), or 23:00 (absolute)."
    shutdown_arg, human = parsed
    success, err = _ssh(machine["host"], machine["user"], f"sudo shutdown {shutdown_arg}")
    if success:
        return f" {machine_name.capitalize()} shutting down {human}."
    return f" Failed to shutdown {machine_name}: {err}"

def reboot(machine_name: str) -> str:
    """Reboot a target machine."""
    if is_protected(machine_name):
        return f" {machine_name} is protected and cannot be rebooted remotely."
    machine = get_machine(machine_name)
    if not machine:
        return f" Unknown machine: '{machine_name}'. Check configuration."
    success, err = _ssh(machine["host"], machine["user"], "sudo reboot")
    if success:
        return f" {machine_name.capitalize()} is rebooting."
    return f" Failed to reboot {machine_name}: {err}"