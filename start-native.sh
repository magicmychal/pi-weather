#!/bin/bash

# Pi Weather Display - Native Python/Tkinter Startup Script
# This script launches the weather display in fullscreen mode
# Also schedules a daily system restart at 3:00 AM

# Setup logging
LOG_FILE="/tmp/pi-weather.log"
exec 1>>"$LOG_FILE"
exec 2>>"$LOG_FILE"
echo "[$(date)] Starting weather display..." 

# Wait for network to be ready
sleep 10

# Set DISPLAY variable (critical for Tkinter on headless boot)
export DISPLAY=:0

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
	echo "[$(date)] Virtual environment activated" >&2
else
	echo "[$(date)] Warning: .venv not found at $PROJECT_DIR/.venv. Running with system python." >&2
fi

# Verify python3 is available
if ! command -v python3 &> /dev/null; then
	echo "[$(date)] ERROR: python3 not found!" >&2
	exit 1
fi

# Launch Python weather display
echo "[$(date)] Launching weather display..." >&2
python3 weather_display.py

# If app exits, log and optionally restart
echo "[$(date)] Weather display exited with code $?" >&2
