import subprocess
import os

RPI_HOST = os.getenv("RPI_HOST")
RPI_USER = os.getenv("RPI_USER")

def wake_desktop() -> str:
    """Send WOL magic packet to desktop via RPI."""
    if not RPI_HOST or not RPI_USER:
        return "Error: RPI_HOST or RPI_USER not set in .env"
    try:
        result = subprocess.run(
            ["ssh", "-i", os.path.expanduser("~/.ssh/id_ed25519"),
             "-o", "StrictHostKeyChecking=no",
             "-o", "ConnectTimeout=5",
             f"{RPI_USER}@{RPI_HOST}",
             "sudo etherwake home-computer"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return "Wake signal sent to desktop. It should boot up shortly."
        else:
            return f"Error sending wake signal: {result.stderr}"
    except subprocess.TimeoutExpired:
        return "Error: SSH connection to RPI timed out."
    except Exception as e:
        return f"Error: {str(e)}"