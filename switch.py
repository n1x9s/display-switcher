#!/usr/bin/env python3
"""
Switches primary display based on MacBook lid angle or brightness.
- Lid angle below threshold → brightness to 0, external becomes primary
- Lid angle above threshold → brightness restored, MacBook becomes primary
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


def set_brightness(value):
    """Set built-in display brightness (0.0 to 1.0)."""
    try:
        swift_code = f"""
import Foundation
import CoreGraphics
let h = dlopen("/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices", RTLD_NOW)
typealias SB = @convention(c) (CGDirectDisplayID, Float) -> Int32
let setBrightness = unsafeBitCast(dlsym(h!, "DisplayServicesSetBrightness"), to: SB.self)
var ds = [CGDirectDisplayID](repeating: 0, count: 8)
var dc: UInt32 = 0
CGGetActiveDisplayList(8, &ds, &dc)
for i in 0..<Int(dc) {{ if CGDisplayIsBuiltin(ds[i]) != 0 {{ setBrightness(ds[i], {value}) }} }}
if h != nil {{ dlclose(h) }}
"""
        subprocess.run(
            ["swift", "-e", swift_code],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        pass


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
        want_builtin_main = lid_angle >= LID_ANGLE_THRESHOLD
        trigger_info = f"lid={lid_angle}°"
    else:
        brightness = get_brightness()
        if brightness < 0:
            if verbose:
                print("No sensor available (lid closed?)")
            return
        want_builtin_main = brightness > BRIGHTNESS_THRESHOLD
        trigger_info = f"brightness={brightness:.4f}"

    displays = get_displays()
    if len(displays) < 2:
        if verbose:
            print("Only one display connected — nothing to switch")
        return

    builtin = next((d for d in displays if d.get("is_builtin")), None)
    externals = [d for d in displays if not d.get("is_builtin")]

    if not builtin or not externals:
        if verbose:
            print("Could not identify builtin/external displays")
        return

    builtin_is_main = builtin.get("origin") == (0, 0)

    if want_builtin_main == builtin_is_main:
        if verbose:
            current = "MacBook" if builtin_is_main else "External"
            print(f"Already correct: {current} is primary ({trigger_info})")
        return

    # Cooldown
    state = load_state()
    if not force:
        last_switch = state.get("last_switch_time", 0)
        if time.time() - last_switch < COOLDOWN_SECONDS:
            if verbose:
                print(f"Cooldown active, skipping ({trigger_info})")
            return

    cmd = get_displayplacer_command()
    if not cmd:
        if verbose:
            print("Could not get displayplacer command")
        return

    if want_builtin_main:
        # Switching to MacBook as main
        main_external = next(
            (d for d in externals if d.get("origin") == (0, 0)), None
        )
        if main_external:
            state["last_external_main"] = main_external["persistent_id"]

        new_cmd = switch_primary(cmd, builtin["persistent_id"], displays)
        target_name = "MacBook"

        # Restore brightness if lid triggered
        if use_lid:
            saved = state.get("saved_brightness", 0.5)
            set_brightness(saved)
    else:
        # Switching to external as main
        target_id = state.get("last_external_main", externals[0]["persistent_id"])
        if not any(d["persistent_id"] == target_id for d in externals):
            target_id = externals[0]["persistent_id"]

        new_cmd = switch_primary(cmd, target_id, displays)
        target_name = "External"

        # Save and zero brightness if lid triggered
        if use_lid:
            current_brightness = get_brightness()
            if current_brightness > BRIGHTNESS_THRESHOLD:
                state["saved_brightness"] = current_brightness
            set_brightness(0.0)

    if new_cmd:
        subprocess.run(new_cmd, shell=True, capture_output=True)
        subprocess.run(["killall", "Dock"], capture_output=True)
        state["last_switch_time"] = time.time()
        save_state(state)
        print(f"Switched primary → {target_name} ({trigger_info})")
    elif verbose:
        print("No switch needed")


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
