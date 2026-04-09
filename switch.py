#!/usr/bin/env python3
"""
Switches primary display based on MacBook lid angle or brightness.
- Lid angle below threshold → built-in screen disabled entirely, external becomes primary
- Lid angle above threshold → built-in screen re-enabled and becomes primary
- Fallback: if lid sensor unavailable, uses brightness directly
"""

import subprocess
import re
import sys
import os
import json
import time

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(DIR, ".state.json")
BRIGHTNESS_HELPER = os.path.join(DIR, "brightness-helper")
LID_ANGLE_HELPER = os.path.join(DIR, "lid-angle")
BRIGHTNESS_THRESHOLD = 0.01
LID_ANGLE_THRESHOLD = 60  # degrees — below this, treat as "folded down"
COOLDOWN_SECONDS = 5


def get_brightness():
    try:
        result = subprocess.run(
            [BRIGHTNESS_HELPER], capture_output=True, text=True, timeout=5
        )
        return float(result.stdout.strip())
    except Exception:
        return -1


def get_lid_angle():
    try:
        result = subprocess.run(
            [LID_ANGLE_HELPER], capture_output=True, text=True, timeout=5
        )
        return int(result.stdout.strip())
    except Exception:
        return -1


def get_displays():
    result = subprocess.run(["displayplacer", "list"], capture_output=True, text=True)
    output = result.stdout

    displays = []
    current = {}

    for line in output.split("\n"):
        stripped = line.strip()

        m = re.match(r"Persistent screen id: (.+)", stripped)
        if m:
            if current and "persistent_id" in current:
                displays.append(current)
            current = {"persistent_id": m.group(1)}
            continue

        m = re.match(r"Type: (.+)", stripped)
        if m:
            current["type"] = m.group(1)
            current["is_builtin"] = "built in" in m.group(1).lower()
            continue

        m = re.match(r"Origin: \((-?\d+),(-?\d+)\)", stripped)
        if m:
            current["origin"] = (int(m.group(1)), int(m.group(2)))
            continue

        m = re.match(r"Enabled: (.+)", stripped)
        if m:
            current["enabled"] = m.group(1).strip().lower() == "true"
            continue

    if current and "persistent_id" in current:
        displays.append(current)

    return displays


def get_displayplacer_command():
    result = subprocess.run(["displayplacer", "list"], capture_output=True, text=True)
    for line in result.stdout.split("\n"):
        if line.startswith('displayplacer "'):
            return line.strip()
    return None


def switch_primary(cmd, target_id, displays):
    target = next((d for d in displays if d["persistent_id"] == target_id), None)
    if not target:
        return None

    ox, oy = target["origin"]
    if ox == 0 and oy == 0:
        return None  # Already primary

    def replace_origin(match):
        x, y = int(match.group(1)), int(match.group(2))
        return f"origin:({x - ox},{y - oy})"

    return re.sub(r"origin:\((-?\d+),(-?\d+)\)", replace_origin, cmd)


def disable_builtin(builtin_id):
    subprocess.run(
        ["displayplacer", f"id:{builtin_id} enabled:false"],
        capture_output=True
    )


def enable_builtin(builtin_id):
    subprocess.run(
        ["displayplacer", f"id:{builtin_id} enabled:true"],
        capture_output=True
    )
    time.sleep(1)


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def run_once(verbose=False, force=False):
    lid_angle = get_lid_angle()
    use_lid = lid_angle >= 0

    if use_lid:
        want_builtin = lid_angle >= LID_ANGLE_THRESHOLD
        trigger_info = f"lid={lid_angle}°"
    else:
        brightness = get_brightness()
        if brightness < 0:
            if verbose:
                print("No sensor available (lid closed?)")
            return
        want_builtin = brightness > BRIGHTNESS_THRESHOLD
        trigger_info = f"brightness={brightness:.4f}"

    state = load_state()
    current_mode = state.get("mode", "builtin")

    if want_builtin and current_mode == "builtin":
        if verbose:
            print(f"Already correct: MacBook is primary ({trigger_info})")
        return
    if not want_builtin and current_mode == "external":
        if verbose:
            print(f"Already correct: External is primary ({trigger_info})")
        return

    # Cooldown
    if not force:
        last_switch = state.get("last_switch_time", 0)
        if time.time() - last_switch < COOLDOWN_SECONDS:
            if verbose:
                print(f"Cooldown active, skipping ({trigger_info})")
            return

    displays = get_displays()
    builtin = next((d for d in displays if d.get("is_builtin")), None)
    externals = [d for d in displays if not d.get("is_builtin")]

    if not externals:
        if verbose:
            print("No external displays connected")
        return

    if want_builtin:
        # --- Switch to MacBook ---
        builtin_id = state.get("builtin_id")
        if not builtin_id:
            if builtin:
                builtin_id = builtin["persistent_id"]
            else:
                if verbose:
                    print("Cannot find built-in display ID")
                return

        # Re-enable built-in screen
        if not builtin or not builtin.get("enabled", True):
            enable_builtin(builtin_id)

        # Re-read displays after enabling
        displays = get_displays()
        builtin = next((d for d in displays if d.get("is_builtin")), None)
        externals = [d for d in displays if not d.get("is_builtin")]

        if not builtin:
            if verbose:
                print("Built-in display did not re-enable")
            return

        cmd = get_displayplacer_command()
        if cmd:
            new_cmd = switch_primary(cmd, builtin["persistent_id"], displays)
            if new_cmd:
                subprocess.run(new_cmd, shell=True, capture_output=True)

        subprocess.run(["killall", "Dock"], capture_output=True)
        state["mode"] = "builtin"
        state["last_switch_time"] = time.time()
        save_state(state)
        print(f"Switched → MacBook (enabled + primary) ({trigger_info})")

    else:
        # --- Switch to External ---
        if not builtin:
            if verbose:
                print("Built-in display already disabled")
            return

        # Remember builtin ID for re-enabling later
        state["builtin_id"] = builtin["persistent_id"]

        # Save which external should be main
        main_external = next(
            (d for d in externals if d.get("origin") == (0, 0)), None
        )
        if main_external:
            state["last_external_main"] = main_external["persistent_id"]
        else:
            state["last_external_main"] = externals[0]["persistent_id"]

        # Switch primary to external first
        cmd = get_displayplacer_command()
        if cmd:
            target_id = state["last_external_main"]
            new_cmd = switch_primary(cmd, target_id, displays)
            if new_cmd:
                subprocess.run(new_cmd, shell=True, capture_output=True)
                time.sleep(0.5)

        # Disable built-in screen entirely
        disable_builtin(builtin["persistent_id"])

        subprocess.run(["killall", "Dock"], capture_output=True)
        state["mode"] = "external"
        state["last_switch_time"] = time.time()
        save_state(state)
        print(f"Switched → External (builtin disabled) ({trigger_info})")


def monitor(interval=2):
    while True:
        try:
            run_once(verbose=False)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        time.sleep(interval)


if __name__ == "__main__":
    if "--monitor" in sys.argv:
        interval = 2
        for i, arg in enumerate(sys.argv):
            if arg == "--interval" and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])
        monitor(interval)
    else:
        run_once(verbose=True, force="--force" in sys.argv)
