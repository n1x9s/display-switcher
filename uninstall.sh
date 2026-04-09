#!/bin/bash
set -e

INSTALL_DIR="$HOME/.config/display-switcher"
PLIST_PATH="$HOME/Library/LaunchAgents/com.display-switcher.plist"

echo "=== Display Switcher Uninstaller ==="

launchctl unload "$PLIST_PATH" 2>/dev/null && echo "Stopped background service" || true
rm -f "$PLIST_PATH" && echo "Removed LaunchAgent"
rm -rf "$INSTALL_DIR" && echo "Removed $INSTALL_DIR"

echo "Done. displayplacer is still installed (brew uninstall displayplacer to remove)."
