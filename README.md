# Display Switcher

Automatically switches the primary display on macOS when you tilt your MacBook lid down.

**Lid below threshold** → external monitor becomes primary, built-in brightness set to 0, Dock moves.
**Lid above threshold** → MacBook becomes primary, brightness restored, Dock moves back.

Falls back to brightness-based detection on Macs without a lid angle sensor.

## Compatibility

**Lid angle sensor** works on:
- MacBook Pro 14"/16" (2021–2024, M1 Pro/Max through M4 Max)
- MacBook Air M2 (2022), M4 (2025)
- MacBook Pro 16" (2019, Intel)

**Brightness fallback** works on any MacBook with an external display.

Requires macOS 14+ and an external monitor connected.

## Install

```bash
git clone https://github.com/n1x9s/display-switcher.git
cd display-switcher
chmod +x install.sh
./install.sh
```

The installer will:
1. Install `displayplacer` via Homebrew (if missing)
2. Compile Swift helpers (lid angle sensor + brightness reader)
3. Test that sensors work on your Mac
4. Set up a background service (LaunchAgent)

## Configuration

Edit `~/.config/display-switcher/switch.py`:

```python
LID_ANGLE_THRESHOLD = 60  # degrees — below this, switch to external
```

After editing, restart the service:
```bash
launchctl unload ~/Library/LaunchAgents/com.display-switcher.plist
launchctl load ~/Library/LaunchAgents/com.display-switcher.plist
```

## Raycast

Script commands are in the `raycast/` folder:
- **Switch Display by Lid/Brightness** — manual one-shot switch
- **Start Display Monitor** — start background service
- **Stop Display Monitor** — stop background service

Add `raycast/` directory in **Raycast → Settings → Extensions → Script Commands → Add Directory**.

## Manual usage

```bash
# Check lid angle
~/.config/display-switcher/lid-angle

# Check brightness
~/.config/display-switcher/brightness-helper

# Run once (check & switch if needed)
python3 ~/.config/display-switcher/switch.py

# Start/stop background monitor
launchctl load ~/Library/LaunchAgents/com.display-switcher.plist
launchctl unload ~/Library/LaunchAgents/com.display-switcher.plist
```

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## How it works

1. **lid-angle** — Swift CLI that reads the HID lid angle sensor (Apple VendorID 0x05AC, ProductID 0x8104) via IOKit
2. **brightness-helper** — Swift CLI that reads built-in display brightness via DisplayServices private framework
3. **switch.py** — Python script that polls every 2 seconds, compares lid angle (or brightness) against threshold, and calls `displayplacer` to reconfigure which display is primary
4. The Dock is restarted (`killall Dock`) after each switch so it moves to the new primary display immediately

## Credits

Lid angle sensor reading based on [LidAngleSensor](https://github.com/samhenrigold/LidAngleSensor) by Sam Henri Gold.
