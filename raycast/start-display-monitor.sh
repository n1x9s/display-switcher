#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Start Display Monitor
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🟢
# @raycast.packageName Display Switcher

# Documentation:
# @raycast.description Start background monitoring to auto-switch primary display.

if launchctl list 2>/dev/null | grep -q "com.display-switcher"; then
    echo "Monitor is already running"
else
    launchctl load "$HOME/Library/LaunchAgents/com.display-switcher.plist" 2>/dev/null
    echo "Display monitor started"
fi
