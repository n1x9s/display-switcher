#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Switch Display by Lid/Brightness
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🖥
# @raycast.packageName Display Switcher

# Documentation:
# @raycast.description Check MacBook lid angle (or brightness) and switch primary display accordingly.

/usr/bin/python3 "$HOME/.config/display-switcher/switch.py" --force
