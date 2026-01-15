#!/bin/bash

# Pi Weather Display - Native Python/Tkinter Startup Script
# This script launches the weather display in fullscreen mode

# Wait for network to be ready
sleep 10

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor (install unclutter if not available)
unclutter -idle 0.1 &

# Change to script directory
cd "$(dirname "$0")"

# Launch Python weather display
python3 weather_display.py

# If the app exits, wait and restart (optional)
# Uncomment below to auto-restart on crash
# while true; do
#     python3 weather_display.py
#     sleep 5
# done
