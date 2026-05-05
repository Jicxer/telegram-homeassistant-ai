import subprocess

def get_cpu_temp() -> str:
    """Read CPU temperature using lm-sensors."""
    try:
        result = subprocess.run(
            ["sensors"],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.splitlines()
        temps = [l for l in lines if "Tdie" in l or "Tccd" in l or "Core" in l]
        if temps:
            return "\n".join(temps)
        return "Could not read CPU temperature."
    except Exception as e:
        return f"Error reading sensors: {e}"

def get_gpu_temp() -> str:
    """Read GPU temperature using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5
        )
        temp = result.stdout.strip()
        return f"GPU temperature: {temp}°C"
    except Exception as e:
        return f"Error reading GPU temp: {e}"
