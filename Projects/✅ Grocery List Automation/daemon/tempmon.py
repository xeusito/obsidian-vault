"""One-shot Pi temperature reporter.

Reads the CPU temperature from /sys/class/thermal/thermal_zone0/temp,
pushes it to a Home Assistant input_number helper, and shuts the Pi
down if the temperature has reached the critical threshold.

Designed to be run by a systemd timer every 30 s (no long-running
process to manage). All config is read from /home/pi/grocery-scanner/.env.
"""

import os
import sys
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

HA_URL        = os.getenv("HA_URL")
HA_TOKEN      = os.getenv("HA_TOKEN")
TEMP_ENTITY   = "input_number.grocery_scanner_pi"
THERMAL_FILE  = "/sys/class/thermal/thermal_zone0/temp"
CRITICAL_TEMP = 80.0  # °C — Pi auto-shuts down at or above this

def read_temp() -> float:
    with open(THERMAL_FILE) as f:
        return round(int(f.read().strip()) / 1000.0, 1)

def push_to_ha(temp: float) -> None:
    requests.post(
        f"{HA_URL}/api/services/input_number/set_value",
        headers={"Authorization": f"Bearer {HA_TOKEN}",
                 "Content-Type": "application/json"},
        json={"entity_id": TEMP_ENTITY, "value": temp},
        timeout=5,
    )

def shutdown() -> None:
    subprocess.run(["sudo", "/sbin/shutdown", "-h", "now"], check=False)

def main() -> int:
    try:
        temp = read_temp()
    except Exception as e:
        print(f"tempmon: failed to read temp: {e}", file=sys.stderr)
        return 1

    try:
        push_to_ha(temp)
    except Exception as e:
        # Don't fail hard — HA might be momentarily unreachable.
        # The critical-shutdown path below still runs.
        print(f"tempmon: failed to push to HA: {e}", file=sys.stderr)

    if temp >= CRITICAL_TEMP:
        print(f"tempmon: critical temp {temp} °C — shutting down", file=sys.stderr)
        shutdown()

    return 0

if __name__ == "__main__":
    sys.exit(main())
