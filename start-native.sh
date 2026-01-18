#!/bin/bash

# Pi Weather Display - Native Python/Tkinter Startup Script
# This script launches the weather display in fullscreen mode
# Also schedules a daily system restart at 3:00 AM

# Wait for network to be ready
sleep 10

# Disable screen blanking
xset s off
xset -dpms
xset s noblank

# Hide mouse cursor (install unclutter if not available)
unclutter -idle 0.1 &

# Change to project directory
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# Schedule daily system restart at 3:00 AM
schedule_daily_restart() {
	while true; do
		current_time=$(date +%s)
		# Calculate next 3:00 AM
		current_hour=$(date +%H)
		if [ "$current_hour" -ge 03 ]; then
			# 3 AM has passed today, schedule for tomorrow
			next_restart=$(date -d "tomorrow 03:00:00" +%s)
		else
			# 3 AM hasn't happened yet today
			next_restart=$(date -d "today 03:00:00" +%s)
		fi
		
		sleep_duration=$((next_restart - current_time))
		if [ $sleep_duration -gt 0 ]; then
			echo "[start-native] Next system restart scheduled for 3:00 AM (in $((sleep_duration / 3600))h $((sleep_duration % 3600 / 60))m)" >&2
			sleep "$sleep_duration"
			echo "[start-native] Triggering system restart at 3:00 AM" >&2
			sudo shutdown -r now
		fi
	done
}

# Start restart scheduler in background
schedule_daily_restart &

# Activate virtual environment if present
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
	. "$PROJECT_DIR/.venv/bin/activate"
else
	echo "[start-native] Warning: .venv not found at $PROJECT_DIR/.venv. Running with system python." >&2
fi

# Launch Python weather display
python3 weather_display.py

# If the app exits, wait and restart (optional)
# Uncomment below to auto-restart on crash
# while true; do
#     python3 weather_display.py
#     sleep 5
# done
