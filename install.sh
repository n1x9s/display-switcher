#!/bin/bash
set -e

INSTALL_DIR="$HOME/.config/display-switcher"
PLIST_NAME="com.display-switcher.plist"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_NAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Display Switcher Installer ==="
echo ""

# 1. Check dependencies
echo "[1/5] Checking dependencies..."

if ! command -v displayplacer &>/dev/null; then
    echo "  Installing displayplacer..."
    brew install jakehilborn/jakehilborn/displayplacer
else
    echo "  displayplacer: OK"
fi

if ! command -v swiftc &>/dev/null; then
    echo "  ERROR: Xcode Command Line Tools required. Run: xcode-select --install"
    exit 1
fi
echo "  swiftc: OK"

# 2. Install files
echo "[2/5] Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/switch.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/lid-angle.swift" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/brightness-helper.swift" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/switch.py"

# 3. Compile Swift helpers
echo "[3/5] Compiling Swift helpers..."
swiftc "$INSTALL_DIR/lid-angle.swift" -o "$INSTALL_DIR/lid-angle" -framework IOKit
swiftc "$INSTALL_DIR/brightness-helper.swift" -o "$INSTALL_DIR/brightness-helper" -framework CoreGraphics
echo "  Compiled OK"

# 4. Test
echo "[4/5] Testing..."
ANGLE=$("$INSTALL_DIR/lid-angle" 2>/dev/null || echo "N/A")
BRIGHTNESS=$("$INSTALL_DIR/brightness-helper" 2>/dev/null || echo "N/A")
echo "  Lid angle: ${ANGLE}°"
echo "  Brightness: $BRIGHTNESS"

if [ "$ANGLE" = "-1" ] && [ "$BRIGHTNESS" = "-1" ]; then
    echo "  WARNING: Neither lid sensor nor brightness could be read."
    echo "  The tool may not work on this Mac model."
fi

# 5. Install LaunchAgent
echo "[5/5] Installing background service..."

# Stop existing service if running
launchctl unload "$PLIST_PATH" 2>/dev/null || true

cat > "$PLIST_PATH" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.display-switcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/switch.py</string>
        <string>--monitor</string>
        <string>--interval</string>
        <string>2</string>
    </array>
    <key>RunAtLoad</key>
    <false/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${INSTALL_DIR}/monitor.log</string>
    <key>StandardErrorPath</key>
    <string>${INSTALL_DIR}/monitor.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
PLIST

echo ""
echo "=== Installed! ==="
echo ""
echo "Usage:"
echo "  Start monitoring:  launchctl load $PLIST_PATH"
echo "  Stop monitoring:   launchctl unload $PLIST_PATH"
echo "  Run once:          python3 $INSTALL_DIR/switch.py"
echo "  Check lid angle:   $INSTALL_DIR/lid-angle"
echo "  Check brightness:  $INSTALL_DIR/brightness-helper"
echo ""
echo "Configuration:"
echo "  Edit $INSTALL_DIR/switch.py"
echo "  LID_ANGLE_THRESHOLD = 60  (degrees, below = external primary)"
echo ""
echo "Raycast scripts are in: $SCRIPT_DIR/raycast/"
echo "  Add that directory in Raycast → Settings → Extensions → Script Commands"
echo ""
echo "Start now? [y/N]"
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    launchctl load "$PLIST_PATH"
    echo "Monitor started!"
fi
