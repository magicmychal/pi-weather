#!/usr/bin/env python3
"""
Pi Weather Display - Native Python/Tkinter Application
Lightweight weather display for Raspberry Pi
"""

import tkinter as tk
from tkinter import font
import requests
from datetime import datetime
import threading
import time

# Configuration
REFRESH_INTERVAL = 600  # Refresh weather every 10 minutes (in seconds)
TIME_UPDATE_INTERVAL = 60  # Update time every minute (in seconds)

# Set your location here
LOCATION = {
    'city': 'Berlin',
    'country': 'Germany'
}

# Weather code mapping (Open-Meteo WMO codes)
WEATHER_CODES = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Foggy',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail'
}


class WeatherDisplay:
    def __init__(self, root):
        self.root = root
        self.root.title("Weather Display")
        
        # Make fullscreen
        self.root.attributes('-fullscreen', True)
        self.root.configure(bg='#667eea')  # Base gradient color
        
        # Allow escape key to exit fullscreen (for testing)
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        self.root.bind('<F11>', lambda e: self.root.attributes('-fullscreen', True))
        
        # Create gradient background using Canvas
        self.canvas = tk.Canvas(root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Variables
        self.latitude = None
        self.longitude = None
        self.location_name = ''
        self.last_weather_code = 0
        self.gradient_start = (102, 126, 234)
        self.gradient_end = (118, 75, 162)
        self.phase_override = None
        self.animating = False
        
        # Create UI elements
        self.create_widgets()
        
        # Create gradient
        self.root.after(100, self.draw_gradient)
        
        # Start fetching data
        self.start_updates()
    
    def create_widgets(self):
        """Create all UI widgets as canvas text items (no background boxes)"""
        # Location text
        self.canvas.create_text(
            0, 0,
            text="Loading location...",
            font=('Segoe UI', 48, 'normal'),
            fill='white',
            anchor='n',
            tags=('location',)
        )

        # Temperature text
        self.canvas.create_text(
            0, 0,
            text="--°",
            font=('Segoe UI', 120),
            fill='white',
            anchor='e',
            tags=('temperature',)
        )

        # Weather description text
        self.canvas.create_text(
            0, 0,
            text="--",
            font=('Segoe UI', 36, 'normal'),
            fill='white',
            anchor='n',
            tags=('description',)
        )

        # Date/Time text (24h format, placed next to temperature)
        self.canvas.create_text(
            0, 0,
            text="--:--",
            font=('Segoe UI', 120),
            fill='white',
            anchor='w',
            tags=('datetime',)
        )

        # Vertical separator line between temperature and time
        self.canvas.create_line(
            0, 0, 0, 0,
            fill='white',
            width=2,
            capstyle=tk.ROUND,
            tags=('separator',)
        )

        # Gradient demo button (top-right corner)
        self.test_button = tk.Button(self.root, text="Gradient Demo", command=self.start_gradient_demo)
        self.canvas.create_window(
            0, 0,
            window=self.test_button,
            anchor='ne',
            tags=('test_button',)
        )

        # Bind resize event
        self.canvas.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event=None):
        """Handle window resize to reposition widgets"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Redraw gradient
        self.draw_gradient()
        
        # Position widgets
        self.canvas.coords('location', width // 2, height * 0.15)
        # Place temperature and time side by side at center
        center_x = width // 2
        middle_y = int(height * 0.45)
        # Place text with extra gap from separator
        self.canvas.coords('temperature', center_x - 40, middle_y)
        self.canvas.coords('datetime', center_x + 40, middle_y)

        # Position separator based on text bounding boxes
        bbox_temp = self.canvas.bbox('temperature')
        bbox_time = self.canvas.bbox('datetime')
        if bbox_temp and bbox_time:
            height_temp = bbox_temp[3] - bbox_temp[1]
            height_time = bbox_time[3] - bbox_time[1]
            sep_height = max(height_temp, height_time)
            y1 = middle_y - sep_height // 2
            y2 = middle_y + sep_height // 2
            self.canvas.coords('separator', center_x, y1, center_x, y2)
        else:
            # Fallback if bbox not ready
            self.canvas.coords('separator', center_x, middle_y - 60, center_x, middle_y + 60)
        self.canvas.coords('description', width // 2, height * 0.60)
        self.canvas.coords('test_button', width - 10, 10)
    
    def draw_gradient(self):
        """Draw gradient background"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 2 or height < 2:
            return
        
        # Delete old gradient
        self.canvas.delete('gradient')
        
        # Simplified gradient with rectangles
        steps = 100
        r1, g1, b1 = self.gradient_start
        r2, g2, b2 = self.gradient_end
        
        for i in range(steps):
            r = int(r1 + (r2 - r1) * i / steps)
            g = int(g1 + (g2 - g1) * i / steps)
            b = int(b1 + (b2 - b1) * i / steps)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            y1 = int(height * i / steps)
            y2 = int(height * (i + 1) / steps)
            
            self.canvas.create_rectangle(
                0, y1, width, y2,
                fill=color,
                outline=color,
                tags='gradient'
            )
        
        # Lower gradient to back
        self.canvas.tag_lower('gradient')

    def get_time_phase(self):
        if self.phase_override:
            return self.phase_override
        h = datetime.now().hour
        if h >= 21 or h < 5:
            return 'night'
        if 5 <= h < 8:
            return 'sunrise'
        if 17 <= h < 21:
            return 'sunset'
        return 'day'

    def compute_gradient(self, weather_code):
        phase = self.get_time_phase()

        def rgb(hex_str):
            return int(hex_str[1:3], 16), int(hex_str[3:5], 16), int(hex_str[5:7], 16)

        rain_codes = {51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99}
        snow_codes = {71, 73, 75, 77, 85, 86}
        cloudy_codes = {2, 3, 45, 48}

        if phase == 'night':
            return rgb('#0b1d3a'), rgb('#0a1930')
        if phase == 'sunrise':
            return rgb('#ffcf71'), rgb('#ff8c42')
        if phase == 'sunset':
            return rgb('#ff9f68'), rgb('#2e1a47')

        # day by weather
        if weather_code in rain_codes:
            return rgb('#5b4b8a'), rgb('#3c2f58')
        if weather_code in snow_codes:
            return rgb('#a8c0ff'), rgb('#3f2b96')
        if weather_code in cloudy_codes:
            return rgb('#7f8da1'), rgb('#546377')
        return rgb('#4da3ff'), rgb('#2b6fd6')

    def update_background(self):
        start, end = self.compute_gradient(self.last_weather_code)
        self.gradient_start = start
        self.gradient_end = end
        self.draw_gradient()

    def animate_gradient_to(self, target_start, target_end, duration_ms=6000, steps=60):
        start_start = self.gradient_start
        start_end = self.gradient_end

        def lerp(a, b, t):
            return int(a + (b - a) * t)

        def step(i):
            t = i / steps
            r1 = lerp(start_start[0], target_start[0], t)
            g1 = lerp(start_start[1], target_start[1], t)
            b1 = lerp(start_start[2], target_start[2], t)
            r2 = lerp(start_end[0], target_end[0], t)
            g2 = lerp(start_end[1], target_end[1], t)
            b2 = lerp(start_end[2], target_end[2], t)

            self.gradient_start = (r1, g1, b1)
            self.gradient_end = (r2, g2, b2)
            self.draw_gradient()

            if i < steps:
                delay = max(1, duration_ms // steps)
                self.root.after(delay, lambda: step(i + 1))
            else:
                self.gradient_start = target_start
                self.gradient_end = target_end

        step(0)

    def start_gradient_demo(self):
        if self.animating:
            return
        self.animating = True

        sequence = [
            ('night', 0),      # deep navy
            ('sunrise', 0),    # yellow/orange
            ('day', 0),        # clear blue
            ('day', 63),       # rainy purple
            ('sunset', 0),     # fade to dusk
            ('night', 0),      # back to navy
        ]

        step_duration = 5000  # 6 steps ~30s total (5s each)

        def run_stage(i):
            if i >= len(sequence):
                self.phase_override = None
                self.animating = False
                self.update_background()
                return

            phase, code = sequence[i]
            self.phase_override = phase
            self.last_weather_code = code
            target_start, target_end = self.compute_gradient(code)
            self.animate_gradient_to(target_start, target_end, duration_ms=step_duration)
            self.root.after(step_duration, lambda: run_stage(i + 1))

        run_stage(0)
    
    def get_coordinates_from_city(self):
        """Get coordinates from city name using geocoding"""
        try:
            url = f"https://geocoding-api.open-meteo.com/v1/search?name={LOCATION['city']}&count=1&language=en&format=json"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('results') and len(data['results']) > 0:
                result = data['results'][0]
                self.latitude = result['latitude']
                self.longitude = result['longitude']
                
                # Set location name
                self.location_name = LOCATION['city']
                if LOCATION.get('country'):
                    self.location_name += f", {LOCATION['country']}"
            else:
                raise Exception('Location not found')
        except Exception as e:
            print(f"Error getting coordinates: {e}")
            # Fallback to Berlin
            self.latitude = 52.52
            self.longitude = 13.405
            self.location_name = 'Berlin, Germany'
        
        self.canvas.itemconfig('location', text=self.location_name)
    
    def fetch_weather(self):
        """Fetch weather data from Open-Meteo API"""
        if self.latitude is None or self.longitude is None:
            return
        
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self.latitude}&longitude={self.longitude}"
                f"&current=temperature_2m,weather_code"
                f"&timezone=auto"
            )
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            self.update_weather_display(data)
        except Exception as e:
            print(f"Error fetching weather: {e}")
            self.canvas.itemconfig('temperature', text="Error")
            self.canvas.itemconfig('description', text="Unable to fetch weather")
    
    def update_weather_display(self, data):
        """Update UI with weather data"""
        try:
            current = data['current']
            
            # Temperature
            temp = round(current['temperature_2m'])
            self.canvas.itemconfig('temperature', text=f"{temp}°")

            # Weather description
            weather_code = current.get('weather_code', 0)
            description = WEATHER_CODES.get(weather_code, 'Unknown')
            self.canvas.itemconfig('description', text=description)
            self.last_weather_code = weather_code
            self.update_background()
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def update_datetime(self):
        """Update date and time display"""
        now = datetime.now()
        formatted = now.strftime("%H:%M")
        self.canvas.itemconfig('datetime', text=formatted)
        self.update_background()
    
    def update_loop(self):
        """Background thread for periodic updates"""
        while True:
            try:
                self.fetch_weather()
            except Exception as e:
                print(f"Error in weather update: {e}")
            time.sleep(REFRESH_INTERVAL)
    
    def time_update_loop(self):
        """Background thread for time updates"""
        while True:
            try:
                self.update_datetime()
            except Exception as e:
                print(f"Error in time update: {e}")
            time.sleep(TIME_UPDATE_INTERVAL)
    
    def start_updates(self):
        """Start all update threads"""
        # Initial data fetch
        self.get_coordinates_from_city()
        self.fetch_weather()
        self.update_datetime()
        
        # Start background threads
        weather_thread = threading.Thread(target=self.update_loop, daemon=True)
        weather_thread.start()
        
        time_thread = threading.Thread(target=self.time_update_loop, daemon=True)
        time_thread.start()


def main():
    root = tk.Tk()
    app = WeatherDisplay(root)
    root.mainloop()


if __name__ == '__main__':
    main()
