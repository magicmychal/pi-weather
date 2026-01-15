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
        
        # Create UI elements
        self.create_widgets()
        
        # Create gradient
        self.root.after(100, self.draw_gradient)
        
        # Start fetching data
        self.start_updates()
    
    def create_widgets(self):
        """Create all UI widgets"""
        # Location label
        self.location_label = tk.Label(
            self.canvas,
            text="Loading location...",
            font=('Segoe UI', 48, 'normal'),
            fg='white',
            bg='#667eea'
        )
        self.canvas.create_window(
            0, 0,
            window=self.location_label,
            anchor='n',
            tags='location'
        )
        
        # Temperature label
        self.temp_label = tk.Label(
            self.canvas,
            text="--°",
            font=('Segoe UI', 120, 'ultralight'),
            fg='white',
            bg='#667eea'
        )
        self.canvas.create_window(
            0, 0,
            window=self.temp_label,
            anchor='center',
            tags='temperature'
        )
        
        # Weather description label
        self.desc_label = tk.Label(
            self.canvas,
            text="--",
            font=('Segoe UI', 36, 'normal'),
            fg='white',
            bg='#667eea'
        )
        self.canvas.create_window(
            0, 0,
            window=self.desc_label,
            anchor='n',
            tags='description'
        )
        
        # Date/Time label
        self.datetime_label = tk.Label(
            self.canvas,
            text="--",
            font=('Segoe UI', 28, 'normal'),
            fg='white',
            bg='#764ba2'
        )
        self.canvas.create_window(
            0, 0,
            window=self.datetime_label,
            anchor='s',
            tags='datetime'
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
        self.canvas.coords('temperature', width // 2, height * 0.45)
        self.canvas.coords('description', width // 2, height * 0.60)
        self.canvas.coords('datetime', width // 2, height * 0.90)
    
    def draw_gradient(self):
        """Draw gradient background"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 2 or height < 2:
            return
        
        # Delete old gradient
        self.canvas.delete('gradient')
        
        # Create gradient from purple (#667eea) to darker purple (#764ba2)
        # Simplified gradient with rectangles
        steps = 100
        r1, g1, b1 = 102, 126, 234  # #667eea
        r2, g2, b2 = 118, 75, 162   # #764ba2
        
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
        
        self.location_label.config(text=self.location_name)
    
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
            self.temp_label.config(text="Error")
            self.desc_label.config(text="Unable to fetch weather")
    
    def update_weather_display(self, data):
        """Update UI with weather data"""
        try:
            current = data['current']
            
            # Temperature
            temp = round(current['temperature_2m'])
            self.temp_label.config(text=f"{temp}°")
            
            # Weather description
            weather_code = current.get('weather_code', 0)
            description = WEATHER_CODES.get(weather_code, 'Unknown')
            self.desc_label.config(text=description)
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def update_datetime(self):
        """Update date and time display"""
        now = datetime.now()
        formatted = now.strftime("%b %d, %I:%M %p")
        self.datetime_label.config(text=formatted)
    
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
