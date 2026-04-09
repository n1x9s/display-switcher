#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Stop Display Monitor
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🔴
# @raycast.packageName Display Switcher

# Documentation:
# @raycast.description Stop background display monitoring.

if launchctl list 2>/dev/null | grep -q "com.display-switcher"; then
    launchctl unload "$HOME/Library/LaunchAgents/com.display-switcher.plist" 2>/dev/null
    echo "Display monitor stopped"
else
    echo "Monitor is not running"
fi
