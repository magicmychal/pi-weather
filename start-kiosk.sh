#!/bin/bash

# Pi Weather Kiosk Mode Startup Script
# This script launches the weather display in fullscreen Chromium

# Wait for the desktop environment to load
sleep 10

# Disable screen blanking and screensaver
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor after inactivity (optional)
unclutter -idle 0.1 &

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    . "$SCRIPT_DIR/.venv/bin/activate"
else
    echo "[start-kiosk] Warning: .venv not found at $SCRIPT_DIR/.venv. Running with system environment." >&2
fi

# Launch Chromium in kiosk mode with the index.html file
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --disable-restore-session-state \
    --no-first-run \
    --disable-notifications \
    --disable-pinch \
    --overscroll-history-navigation=0 \
    "file://${SCRIPT_DIR}/index.html" &

# Optional: Auto-reload the page every 24 hours to keep weather data fresh
# Uncomment the following lines if you want this feature
# while true; do
#     sleep 86400  # 24 hours
#     pkill chromium-browser
#     sleep 5
#     chromium-browser --kiosk --noerrdialogs --disable-infobars "file://${SCRIPT_DIR}/index.html" &
# done
