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
import os
from dotenv import load_dotenv
from PIL import Image, ImageTk
from io import BytesIO
from urllib.request import urlopen

# Configuration
REFRESH_INTERVAL = 600  # Refresh weather every 10 minutes (in seconds)
TIME_UPDATE_INTERVAL = 60  # Update time every minute (in seconds)

# Load environment variables
load_dotenv()
AIRLY_API_KEY = os.getenv('AIRLY_API_KEY')
AIRLY_LATITUDE = os.getenv('AIRLY_LATITUDE')
AIRLY_LONGITUDE = os.getenv('AIRLY_LONGITUDE')
AIRLY_MAX_DISTANCE_KM = os.getenv('AIRLY_MAX_DISTANCE_KM', '5')
DEBUG_ENV = os.getenv('DEBUG', 'false')

def parse_bool(value):
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

DEBUG = parse_bool(DEBUG_ENV)

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
        self.air_quality = None
        self.airly_logo = None
        self.airly_logo_photo = None
        self.last_aqi_fetch_hour = None
        self.debug_enabled = DEBUG
        
        # Create UI elements
        self.create_widgets()
        
        # Create gradient
        self.root.after(100, self.draw_gradient)
        
        # Start fetching data
        self.start_updates()
    
    def create_widgets(self):
        """Create all UI widgets as canvas text items (no background boxes)"""

        # Temperature text
        self.canvas.create_text(
            0, 0,
            text="--°",
            font=('Segoe UI', 78),
            fill='white',
            anchor='w',
            tags=('temperature',)
        )

        # Date/Time text (24h format, right-aligned toward divider)
        self.canvas.create_text(
            0, 0,
            text="--:--",
            font=('Segoe UI', 78),
            fill='white',
            anchor='e',
            tags=('datetime',)
        )

        # Vertical separator line between clock and weather
        self.canvas.create_line(
            0, 0, 0, 0,
            fill='white',
            width=2,
            capstyle=tk.ROUND,
            tags=('divider',)
        )

        # Air quality text (same size as temperature, with auto-fit)
        self.canvas.create_text(
            0, 0,
            text="--",
            font=('Segoe UI', 78),
            fill='white',
            anchor='w',
            tags=('air_quality',)
        )

        # Airly logo (bottom right corner)
        self.airly_logo = self.canvas.create_image(
            0, 0,
            anchor='se',
            tags=('airly_logo',)
        )

        # Gradient demo button (top-right corner, only in debug mode)
        if self.debug_enabled:
            self.test_button = tk.Button(self.root, text="Gradient Demo", command=self.start_gradient_demo)
            self.canvas.create_window(
                0, 0,
                window=self.test_button,
                anchor='ne',
                tags=('test_button',)
            )
        else:
            self.test_button = None

        # Bind resize event
        self.canvas.bind('<Configure>', self.on_resize)
    
    def on_resize(self, event=None):
        """Handle window resize to reposition widgets"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Redraw gradient
        self.draw_gradient()
        
        # Divider line in the middle
        divider_x = width // 2
        gap = int(width * 0.02)  # small gap between content and divider

        # Left panel: Clock (time), right-aligned toward divider
        clock_x = divider_x - gap
        clock_y = height * 0.45
        self.canvas.coords('datetime', clock_x, clock_y)
        
        # Divider line
        self.canvas.coords('divider', divider_x, height * 0.20, divider_x, height * 0.80)
        
        # Right panel: Temperature and air quality (left-aligned away from divider)
        right_x = divider_x + gap
        right_max_width = width - right_x - 20  # available width for right panel
        temp_y = height * 0.35
        air_quality_y = height * 0.55
        
        self.canvas.coords('temperature', right_x, temp_y)
        self.canvas.coords('air_quality', right_x, air_quality_y)
        
        # Auto-fit air quality text if too wide
        self.auto_fit_text('air_quality', right_max_width)
        
        # Position logo and button
        self.canvas.coords('airly_logo', width - 20, height - 20)
        if self.debug_enabled:
            self.canvas.coords('test_button', width - 10, 10)
    
    def auto_fit_text(self, tag, max_width):
        """Shrink font size until text fits within max_width"""
        item = self.canvas.find_withtag(tag)
        if not item:
            return
        
        # Get current text and font
        text = self.canvas.itemcget(tag, 'text')
        if not text:
            return
        
        # Start with the base font size and reduce until it fits
        base_size = 78
        min_size = 24
        font_family = 'Helvetica'
        
        for size in range(base_size, min_size - 1, -2):
            f = font.Font(family=font_family, size=size, weight='bold')
            text_width = f.measure(text)
            if text_width <= max_width:
                self.canvas.itemconfig(tag, font=(font_family, size, 'bold'))
                return
        
        # If still too wide, use minimum size
        self.canvas.itemconfig(tag, font=(font_family, min_size, 'bold'))
    
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
        
        # Raise all UI elements above gradient
        self.canvas.tag_raise('airly_logo')
        self.canvas.tag_raise('air_quality')
        self.canvas.tag_raise('divider')
        self.canvas.tag_raise('temperature')
        self.canvas.tag_raise('datetime')
        if self.debug_enabled:
            self.canvas.tag_raise('test_button')

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
    
    def fetch_air_quality(self):
        """Fetch air quality data from Airly API"""
        print(f"[AQI] Fetching air quality data from Airly...")
        print(f"[AQI] AIRLY_API_KEY: {'***' if AIRLY_API_KEY else 'NOT SET'}")
        print(f"[AQI] Location: {AIRLY_LATITUDE}, {AIRLY_LONGITUDE}")
        
        if not AIRLY_API_KEY or not AIRLY_LATITUDE or not AIRLY_LONGITUDE:
            print("[AQI] Warning: AIRLY_API_KEY, AIRLY_LATITUDE, or AIRLY_LONGITUDE not configured in .env")
            return

        try:
            # Step 1: Get nearest installations
            url_installations = f"https://airapi.airly.eu/v2/installations/nearest?lat={AIRLY_LATITUDE}&lng={AIRLY_LONGITUDE}&maxDistanceKM={AIRLY_MAX_DISTANCE_KM}&maxResults=3"
            headers = {"apikey": AIRLY_API_KEY}
            print(f"[AQI] Step 1: Fetching nearest installations...")
            print(f"[AQI] URL: {url_installations}")
            
            response = requests.get(url_installations, headers=headers, timeout=10)
            print(f"[AQI] Response status: {response.status_code}")
            
            installations = response.json()
            print(f"[AQI] Found {len(installations)} installations")
            
            if not installations or len(installations) == 0:
                raise Exception('No installations found')
            
            # Get the closest installation
            closest_installation = installations[0]
            installation_id = closest_installation.get('id')
            print(f"[AQI] Using installation ID: {installation_id}")
            print(f"[AQI] Address: {closest_installation.get('address', {}).get('displayAddress1', 'Unknown')}")
            
            # Step 2: Get measurements for the closest installation
            url_measurements = f"https://airapi.airly.eu/v2/measurements/installation?installationId={installation_id}&includeWildcards=true"
            print(f"[AQI] Step 2: Fetching measurements for installation {installation_id}...")
            
            response = requests.get(url_measurements, headers=headers, timeout=10)
            print(f"[AQI] Response status: {response.status_code}")
            
            data = response.json()
            print(f"[AQI] Response data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")

            if data.get('current'):
                current = data['current']
                indexes = current.get('indexes', [])
                values = current.get('values', [])
                
                print(f"[AQI] Indexes found: {len(indexes)}")
                print(f"[AQI] Values found: {len(values)}")
                
                # Extract AIRLY_CAQI or PM2.5
                air_quality_text = "--"
                for index in indexes:
                    if index.get('name') == 'AIRLY_CAQI':
                        caqi_value = round(index.get('value', 0))
                        status = self.caqi_to_status(caqi_value)
                        air_quality_text = status
                        print(f"[AQI] Found CAQI index: {caqi_value} -> {status}")
                        break
                
                # Fallback to PM2.5 if CAQI not found
                if air_quality_text == "--":
                    for value in values:
                        if value.get('name') == 'PM25':
                            pm25_value = round(value.get('value', 0), 1)
                            # Rough PM2.5 to CAQI conversion (PM2.5: 0-12 good, 12-35 moderate, etc.)
                            if pm25_value <= 12:
                                status = "Take a deep breath!"
                            elif pm25_value <= 35:
                                status = "Air is getting better."
                            elif pm25_value <= 55:
                                status = "It's ok... don't "
                            elif pm25_value <= 150:
                                status = "Try to limit outdoor activities"
                            else:
                                status = "Hazardous, do not go out!"
                            air_quality_text = status
                            print(f"[AQI] Found PM2.5: {pm25_value} -> {status}")
                            break
                
                print(f"[AQI] Setting air quality text: {air_quality_text}")
                self.air_quality = air_quality_text
                self.canvas.itemconfig('air_quality', text=air_quality_text)
                print(f"[AQI] Air quality updated successfully")
                
                # Load Airly logo
                self.load_airly_logo()
            else:
                raise Exception('Air quality data not found in response')
        except Exception as e:
            print(f"[AQI] Error fetching air quality: {e}")
            import traceback
            traceback.print_exc()
            self.canvas.itemconfig('air_quality', text="AQI: Error")
    
    def caqi_to_status(self, caqi_value):
        """Convert CAQI value to verbal air quality status"""
        caqi = float(caqi_value)
        if caqi <= 33:
            return "A-MAZE-BALLS"
        elif caqi <= 66:
            return "Open the windows, go out!"
        elif caqi <= 99:
            return "It's ok..."
        elif caqi <= 150:
            return "Bad, but will survive"
        else:
            return "Hazardous, do not open the windows"
    
    def load_airly_logo(self):
        """Load and display Airly logo from CDN"""
        try:
            print("[Logo] Loading Airly logo...")
            # Direct PNG URL provided by user
            png_url = "https://cdn.airly.org/assets/brand/logo/primary/airly-1024.png"

            resp = requests.get(png_url, timeout=8)
            if resp.status_code == 200 and resp.headers.get('Content-Type', '').lower().startswith('image/'):
                img = Image.open(BytesIO(resp.content))
                # Limit width to 160px, keep aspect ratio
                max_w = 160
                if img.width > max_w:
                    new_h = int(img.height * (max_w / img.width))
                    img = img.resize((max_w, new_h), Image.LANCZOS)

                self.airly_logo_photo = ImageTk.PhotoImage(img)
                # Assign to canvas image item
                self.canvas.itemconfig('airly_logo', image=self.airly_logo_photo)
                # Ensure on top and position at bottom-right
                w = self.canvas.winfo_width()
                h = self.canvas.winfo_height()
                self.canvas.coords('airly_logo', w - 20, h - 20)
                self.canvas.tag_raise('airly_logo')
                print("[Logo] Airly logo set successfully")
            else:
                raise Exception(f"PNG not available (status {resp.status_code}, content-type {resp.headers.get('Content-Type')})")
        except Exception as e:
            print(f"[Logo] Error loading Airly logo: {e}")
            # Fallback to text logo placeholder
            if not self.canvas.find_withtag('airly_logo_text'):
                self.canvas.create_text(
                    0, 0,
                    text="Airly",
                        font=('Segoe UI', 16, 'bold'),
                    fill='white',
                    anchor='se',
                    tags=('airly_logo_text',)
                )
            # Position placeholder at bottom-right
            w = self.canvas.winfo_width()
            h = self.canvas.winfo_height()
            self.canvas.coords('airly_logo_text', w - 20, h - 20)
            self.canvas.tag_raise('airly_logo_text')
    
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
    
    def air_quality_loop(self):
        """Background thread for air quality updates - only at 6am, 3pm, and 8pm"""
        scheduled_hours = [6, 15, 20]
        
        while True:
            now = datetime.now()
            current_hour = now.hour
            
            # Check if we're at a scheduled hour and haven't fetched yet this hour
            if current_hour in scheduled_hours and self.last_aqi_fetch_hour != current_hour:
                try:
                    print(f"[AQI] Scheduled fetch at {now.strftime('%H:%M')}")
                    self.fetch_air_quality()
                    self.last_aqi_fetch_hour = current_hour
                except Exception as e:
                    print(f"Error in air quality update: {e}")
            
            # Sleep for 1 minute before checking again
            time.sleep(60)
    
    def start_updates(self):
        """Start all update threads"""
        # Initial data fetch
        self.get_coordinates_from_city()
        self.fetch_weather()
        self.fetch_air_quality()
        self.update_datetime()
        
        # Start background threads
        weather_thread = threading.Thread(target=self.update_loop, daemon=True)
        weather_thread.start()
        
        air_quality_thread = threading.Thread(target=self.air_quality_loop, daemon=True)
        air_quality_thread.start()
        
        time_thread = threading.Thread(target=self.time_update_loop, daemon=True)
        time_thread.start()


def main():
    root = tk.Tk()
    app = WeatherDisplay(root)
    root.mainloop()


if __name__ == '__main__':
    main()
