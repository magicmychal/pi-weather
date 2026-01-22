#!/usr/bin/env python3
"""
Pi Weather Display - Native Python/Tkinter Application
Lightweight weather display for Raspberry Pi
"""

import tkinter as tk
from tkinter import font
import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from PIL import Image, ImageTk
from io import BytesIO
from urllib.request import urlopen

# Load environment variables FIRST (before using os.getenv)
load_dotenv()

# Configuration
REFRESH_INTERVAL = 1800  # Refresh weather every 30 minutes (in seconds)
TIME_UPDATE_INTERVAL = 59  # Update time every minute (in seconds)
TRANSPORT_REFRESH_INTERVAL = 300  # Refresh transport every 5 minutes (in seconds)

# Transport API configuration (VBB)
TRANSPORT_API_BASE = "https://v6.vbb.transport.rest/stops"
TRANSPORT_STATION_ID = os.getenv('TRANSPORT_STATION_ID', '900003201')  # Default: Berlin Hbf
TRANSPORT_DURATION = 25  # Look ahead duration in minutes
TRANSPORT_RESULTS = 6  # Number of departures to fetch (enough for ~3 per direction)

def build_transport_url():
    """Build VBB transport API URL for S-Bahn departures only"""
    return (
        f"{TRANSPORT_API_BASE}/{TRANSPORT_STATION_ID}/departures"
        f"?duration={TRANSPORT_DURATION}"
        f"&results={TRANSPORT_RESULTS}"
        f"&suburban=true"
        f"&subway=false"
        f"&tram=false"
        f"&bus=false"
        f"&ferry=false"
        f"&express=false"
        f"&regional=false"
    )
AIRLY_API_KEY = os.getenv('AIRLY_API_KEY')
AIRLY_LATITUDE = os.getenv('AIRLY_LATITUDE')
AIRLY_LONGITUDE = os.getenv('AIRLY_LONGITUDE')
AIRLY_MAX_DISTANCE_KM = os.getenv('AIRLY_MAX_DISTANCE_KM', '5')
DEBUG_ENV = os.getenv('DEBUG', 'false')

def parse_bool(value):
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

DEBUG = parse_bool(DEBUG_ENV)

# Location configuration (from .env)
LOCATION = {
    'city': os.getenv('LOCATION_CITY', 'Berlin'),
    'country': os.getenv('LOCATION_COUNTRY', 'Germany')
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
        self.last_aqi_fetch_hour = None
        self.debug_enabled = DEBUG
        self.aqi_canvas = None
        self.current_caqi_value = 50  # Store current CAQI for re-applying after resize
        
        # Performance optimizations for Pi Zero
        self._font_cache = {}  # Cache Font objects to avoid repeated creation
        self._resize_after_id = None  # Debounce resize events
        self._weather_after_id = None  # Scheduled weather update
        self._time_after_id = None  # Scheduled time update
        self._aqi_after_id = None  # Scheduled AQI update
        self._transport_after_id = None  # Scheduled transport update
        
        # Create UI elements
        self.create_widgets()
        
        # Create gradient
        self.root.after(100, self.draw_gradient)
        
        # Start fetching data
        self.start_updates()
    
    def create_widgets(self):
        """Create all UI widgets for new 3-section layout"""

        # === SECTION 1: HEADER ===
        # Time (left-aligned, large)
        self.canvas.create_text(
            0, 0,
            text="--:--",
            font=('IBM Plex Mono', 90, 'bold italic'),
            fill='#FFFFFF',
            anchor='w',
            tags=('datetime',)
        )

        # Temperature (right-aligned, large)
        self.canvas.create_text(
            0, 0,
            text="--°",
            font=('IBM Plex Mono', 90, 'bold italic'),
            fill='#FFFFFF',
            anchor='e',
            tags=('temperature',)
        )

        # === SECTION 2: AIR QUALITY SLIDER ===
        # Canvas for AQI slider (will be positioned in resize)
        self.aqi_canvas = tk.Canvas(self.root, highlightthickness=0, bg='#667eea')
        self.canvas.create_window(
            0, 0,
            window=self.aqi_canvas,
            anchor='center',
            tags=('aqi_slider',)
        )
        
        # Store image references
        self.aqi_bar_images = {}
        self.aqi_indicator_image = None
        
        # === SECTION 3: TRANSPORT SCHEDULE ===
        # Headers
        self.canvas.create_text(
            0, 0,
            text="Linie",
            font=('IBM Plex Mono', 24, 'bold italic'),
            fill='#FFFFFF',
            anchor='w',
            tags=('transport_header_linie',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="wann (min)",
            font=('IBM Plex Mono', 24, 'bold italic'),
            fill='#FFFFFF',
            anchor='center',
            tags=('transport_header_wann',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="nach",
            font=('IBM Plex Mono', 24, 'bold italic'),
            fill='#FFFFFF',
            anchor='e',
            tags=('transport_header_nach',)
        )
        
        # Row 1: S42
        self.canvas.create_text(
            0, 0,
            text="S42",
            font=('IBM Plex Mono', 40, 'bold italic'),
            fill='#FFFFFF',
            anchor='w',
            tags=('transport_row1_linie',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="2 10 23",
            font=('IBM Plex Mono', 40, 'bold italic'),
            fill='#FFFFFF',
            anchor='center',
            tags=('transport_row1_wann',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="Ostkreuz",
            font=('IBM Plex Mono', 20, 'bold italic'),
            fill='#FFFFFF',
            anchor='e',
            tags=('transport_row1_nach',)
        )
        
        # Row 2: S41
        self.canvas.create_text(
            0, 0,
            text="S41",
            font=('IBM Plex Mono', 40, 'bold italic'),
            fill='#FFFFFF',
            anchor='w',
            tags=('transport_row2_linie',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="2 10 23",
            font=('IBM Plex Mono', 40, 'bold italic'),
            fill='#FFFFFF',
            anchor='center',
            tags=('transport_row2_wann',)
        )
        
        self.canvas.create_text(
            0, 0,
            text="Sudkreuz",
            font=('IBM Plex Mono', 20, 'bold italic'),
            fill='#FFFFFF',
            anchor='e',
            tags=('transport_row2_nach',)
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
        
        # Load AQI slider assets
        self.load_aqi_assets()
    
    def on_resize(self, event=None):
        """Handle window resize to reposition widgets (debounced for performance)"""
        # Cancel any pending resize callback
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        # Debounce: wait 150ms after last resize event before redrawing
        self._resize_after_id = self.root.after(150, self._do_resize)
    
    def _do_resize(self):
        """Actually perform the resize operations"""
        self._resize_after_id = None
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        # Redraw gradient
        self.draw_gradient()
        
        margin = int(width * 0.05)  # 5% margin from screen edges
        
        # === SECTION 1: HEADER (Top) ===
        header_y = height * 0.12
        
        # Time (left-aligned)
        self.canvas.coords('datetime', margin, header_y)
        
        # Temperature (right-aligned)
        self.canvas.coords('temperature', width - margin, header_y)
        
        # === SECTION 2: AQI SLIDER (Middle) ===
        aqi_y = height * 0.40
        aqi_slider_width = int(width * 0.7)  # 70% of screen width
        aqi_slider_height = 60
        
        # Position the AQI canvas
        self.canvas.coords('aqi_slider', width // 2, aqi_y)
        
        # Resize AQI canvas
        if self.aqi_canvas:
            self.aqi_canvas.config(width=aqi_slider_width, height=aqi_slider_height)
            self.setup_aqi_slider()
        
        # === SECTION 3: TRANSPORT SCHEDULE (Bottom) ===
        transport_start_y = height * 0.60
        row_spacing = height * 0.10
        
        # Calculate column positions
        col1_x = margin  # Left column (Linie)
        col2_x = width // 2  # Center column (wann)
        col3_x = width - margin  # Right column (nach)
        
        # Headers
        self.canvas.coords('transport_header_linie', col1_x, transport_start_y)
        self.canvas.coords('transport_header_wann', col2_x, transport_start_y)
        self.canvas.coords('transport_header_nach', col3_x, transport_start_y)
        
        # Row 1
        row1_y = transport_start_y + row_spacing
        self.canvas.coords('transport_row1_linie', col1_x, row1_y)
        self.canvas.coords('transport_row1_wann', col2_x, row1_y)
        self.canvas.coords('transport_row1_nach', col3_x, row1_y)
        
        # Row 2
        row2_y = transport_start_y + row_spacing * 2
        self.canvas.coords('transport_row2_linie', col1_x, row2_y)
        self.canvas.coords('transport_row2_wann', col2_x, row2_y)
        self.canvas.coords('transport_row2_nach', col3_x, row2_y)
        
        # Position button
        if self.debug_enabled:
            self.canvas.coords('test_button', width - 10, 10)
    
    def _get_cached_font(self, family, size, weight='normal'):
        """Get a cached Font object to avoid repeated creation (expensive on Pi Zero)"""
        key = (family, size, weight)
        if key not in self._font_cache:
            self._font_cache[key] = font.Font(family=family, size=size, weight=weight)
        return self._font_cache[key]
    
    def auto_fit_text(self, tag, max_width, fill_space=False):
        """Adjust font size to fit within max_width (optimized with font cache)
        
        Args:
            tag: Canvas text item tag
            max_width: Maximum width available
            fill_space: If True, scale UP to fill space; if False, only shrink if needed
        """
        item = self.canvas.find_withtag(tag)
        if not item:
            return
        
        # Get current text and font
        text = self.canvas.itemcget(tag, 'text')
        if not text:
            return
        
        # Font size range - allow larger sizes when filling space
        max_size = 200 if fill_space else 78
        min_size = 24
        font_family = 'Helvetica'
        
        # Find the largest font size that fits
        best_size = min_size
        for size in range(max_size, min_size - 1, -4):
            f = self._get_cached_font(font_family, size, 'bold')
            text_width = f.measure(text)
            if text_width <= max_width:
                best_size = size
                break
        
        self.canvas.itemconfig(tag, font=(font_family, best_size, 'bold'))
    
    def draw_gradient(self):
        """Draw gradient background"""
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width < 2 or height < 2:
            return
        
        # Delete old gradient
        self.canvas.delete('gradient')
        
        # Simplified gradient with rectangles (reduced steps for Pi Zero performance)
        steps = 20
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
        self.canvas.tag_raise('temperature')
        self.canvas.tag_raise('datetime')
        self.canvas.tag_raise('aqi_slider')
        self.canvas.tag_raise('transport_header_linie')
        self.canvas.tag_raise('transport_header_wann')
        self.canvas.tag_raise('transport_header_nach')
        self.canvas.tag_raise('transport_row1_linie')
        self.canvas.tag_raise('transport_row1_wann')
        self.canvas.tag_raise('transport_row1_nach')
        self.canvas.tag_raise('transport_row2_linie')
        self.canvas.tag_raise('transport_row2_wann')
        self.canvas.tag_raise('transport_row2_nach')
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
    
    def load_aqi_assets(self):
        """Load AQI slider images from assets folder"""
        try:
            from PIL import Image, ImageTk
            
            # Load full bar image
            self.aqi_bar_images['full'] = ImageTk.PhotoImage(Image.open('assets/bar_full.png'))
            self.aqi_indicator_image = ImageTk.PhotoImage(Image.open('assets/bar_indicator.png'))
            
            print("[AQI] Assets loaded successfully")
        except Exception as e:
            print(f"[AQI] Error loading assets: {e}")
            # Create placeholder rectangles if images not found
            self.aqi_bar_images = None
    
    def setup_aqi_slider(self):
        """Setup the AQI slider visualization on the canvas"""
        if not self.aqi_canvas:
            return
        
        # Clear canvas
        self.aqi_canvas.delete('all')
        
        # Update canvas background to match gradient
        # Use the middle gradient color for better blending
        r = (self.gradient_start[0] + self.gradient_end[0]) // 2
        g = (self.gradient_start[1] + self.gradient_end[1]) // 2
        b = (self.gradient_start[2] + self.gradient_end[2]) // 2
        self.aqi_canvas.config(bg=f'#{r:02x}{g:02x}{b:02x}')
        
        canvas_width = self.aqi_canvas.winfo_width()
        canvas_height = self.aqi_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        if self.aqi_bar_images:
            try:
                from PIL import Image, ImageTk
                
                # Load and resize bar_full.png to fill entire canvas width
                full_img = Image.open('assets/bar_full.png')
                full_resized = full_img.resize((canvas_width, canvas_height), Image.BILINEAR)
                self.aqi_bar_images['full_resized'] = ImageTk.PhotoImage(full_resized)
                
                # Place full bar spanning the entire canvas (left edge = 0, right edge = 100)
                self.aqi_canvas.create_image(
                    canvas_width // 2, canvas_height // 2,
                    image=self.aqi_bar_images['full_resized'],
                    tags=('bar_full',)
                )
                
                # Create indicator (initially at position 0)
                self.aqi_canvas.create_image(
                    0, canvas_height // 2,
                    image=self.aqi_indicator_image,
                    anchor='center',
                    tags=('indicator',)
                )
                
                print(f"[AQI] Slider setup complete - canvas: {canvas_width}x{canvas_height}")
                
                # Re-apply the current CAQI value to position the indicator
                self.root.after(100, lambda: self.update_aqi(self.current_caqi_value))
            except Exception as e:
                print(f"[AQI] Error resizing images: {e}")
                import traceback
                traceback.print_exc()
                # Fall back to rectangles
                self.aqi_bar_images = None
        
        if not self.aqi_bar_images:
            # Fallback: draw gradient rectangle (0-100)
            self.aqi_canvas.create_rectangle(
                0, 0, canvas_width, canvas_height,
                fill='#4CAF50', outline='',
                tags=('bar_full',)
            )
            
            # White indicator line
            self.aqi_canvas.create_line(
                0, 0, 0, canvas_height,
                fill='white', width=4,
                tags=('indicator',)
            )
    
    def update_aqi(self, caqi_value):
        """Update AQI indicator position based on CAQI value
        
        CAQI is inverted:
        - CAQI 100+ = bad air = indicator at LEFT (0%)
        - CAQI ~50-75 = medium = indicator in MIDDLE
        - CAQI 0-25 = good air = indicator at RIGHT (100%)
        
        Args:
            caqi_value: Raw CAQI value (0 to 100+)
        """
        # Store the value for re-applying after resize
        self.current_caqi_value = caqi_value
        
        if not self.aqi_canvas:
            print("[AQI] No aqi_canvas available")
            return
        
        canvas_width = self.aqi_canvas.winfo_width()
        canvas_height = self.aqi_canvas.winfo_height()
        
        if canvas_width <= 1:
            print(f"[AQI] Canvas too small: {canvas_width}x{canvas_height}, will retry later")
            # Schedule a retry after canvas is ready
            self.root.after(500, lambda: self.update_aqi(caqi_value))
            return
        
        # Clamp CAQI to 0-100 range, then invert
        # CAQI 0 -> position 100% (right), CAQI 100+ -> position 0% (left)
        clamped_caqi = max(0, min(100, caqi_value))
        position_percent = 100 - clamped_caqi
        
        # Calculate X position - position_percent maps to canvas width
        # 0% = left edge, 100% = right edge
        x_pos = int((position_percent / 100) * canvas_width)
        
        print(f"[AQI] CAQI: {caqi_value} -> clamped: {clamped_caqi} -> position: {position_percent}% -> x_pos: {x_pos} (canvas_width: {canvas_width})")
        
        # Move indicator
        indicator = self.aqi_canvas.find_withtag('indicator')
        if indicator:
            if self.aqi_indicator_image:
                # Image-based indicator
                self.aqi_canvas.coords('indicator', x_pos, canvas_height // 2)
            else:
                # Line-based indicator
                self.aqi_canvas.coords('indicator', x_pos, 0, x_pos, canvas_height)
            print(f"[AQI] Indicator moved to {x_pos}")
        else:
            print("[AQI] No indicator found on canvas")
    
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
                aqi_score = 0
                for index in indexes:
                    if index.get('name') == 'AIRLY_CAQI':
                        caqi_value = round(index.get('value', 0))
                        aqi_score = caqi_value
                        print(f"[AQI] Found CAQI index: {caqi_value}")
                        break
                
                # Fallback to PM2.5 if CAQI not found
                if aqi_score == 0:
                    for value in values:
                        if value.get('name') == 'PM25':
                            pm25_value = round(value.get('value', 0), 1)
                            # Convert PM2.5 to 0-100 scale (rough approximation)
                            aqi_score = min(100, int(pm25_value * 0.5))
                            print(f"[AQI] Found PM2.5: {pm25_value} -> score {aqi_score}")
                            break
                
                # Update the slider
                print(f"[AQI] Updating slider with score: {aqi_score}")
                self.update_aqi(aqi_score)
                print(f"[AQI] Air quality updated successfully")
            else:
                raise Exception('Air quality data not found in response')
        except Exception as e:
            print(f"[AQI] Error fetching air quality: {e}")
            import traceback
            traceback.print_exc()
    
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
    
    def schedule_weather_update(self):
        """Schedule weather updates using Tkinter's after() (more efficient than threads)"""
        try:
            self.fetch_weather()
        except Exception as e:
            print(f"Error in weather update: {e}")
        # Schedule next update
        self._weather_after_id = self.root.after(REFRESH_INTERVAL * 1000, self.schedule_weather_update)
    
    def schedule_time_update(self):
        """Schedule time updates using Tkinter's after() (more efficient than threads)"""
        try:
            self.update_datetime()
        except Exception as e:
            print(f"Error in time update: {e}")
        # Schedule next update
        self._time_after_id = self.root.after(TIME_UPDATE_INTERVAL * 1000, self.schedule_time_update)
    
    def schedule_aqi_update(self):
        """Schedule air quality updates using Tkinter's after() - only at 6am, 3pm, and 8pm"""
        scheduled_hours = [6, 15, 20]
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
        
        # Check again in 1 minute
        self._aqi_after_id = self.root.after(60 * 1000, self.schedule_aqi_update)
    
    def fetch_transport(self):
        """Fetch transport departure data from VBB API
        
        Makes a single API call for S-Bahn departures, then groups by line name
        to display up to 2 different lines in separate rows.
        """
        if self.debug_enabled:
            print("[Transport] Fetching transport data...")
        
        try:
            # Single API call for all S-Bahn departures
            response = requests.get(build_transport_url(), timeout=15)
            data = response.json()
            departures = data.get('departures', [])
            
            if self.debug_enabled:
                print(f"[Transport] Received {len(departures)} departures")
            
            # Group departures by line name (preserves insertion order)
            lines = {}
            for dep in departures:
                line_name = dep.get('line', {}).get('name', 'Unknown')
                if line_name not in lines:
                    lines[line_name] = []
                lines[line_name].append(dep)
            
            # Get first two distinct line groups
            line_groups = list(lines.values())[:2]
            
            # Update rows with available line groups
            if len(line_groups) >= 1:
                self.update_transport_row(1, line_groups[0])
            else:
                self.update_transport_row(1, [])
            
            if len(line_groups) >= 2:
                self.update_transport_row(2, line_groups[1])
            else:
                self.update_transport_row(2, [])
            
            if self.debug_enabled:
                print(f"[Transport] Found {len(lines)} distinct lines: {list(lines.keys())}")
        except requests.exceptions.Timeout:
            print("[Transport] Request timed out, keeping old data")
        except requests.exceptions.ConnectionError:
            print("[Transport] No connection, will retry later")
        except Exception as e:
            print(f"[Transport] Error fetching transport data: {e}")
    
    def update_transport_row(self, row_num, departures):
        """Update a transport row with departure data
        
        Args:
            row_num: 1 or 2 (which row to update)
            departures: List of departure objects from VBB API
        """
        if not departures:
            self.canvas.itemconfig(f'transport_row{row_num}_linie', text="--")
            self.canvas.itemconfig(f'transport_row{row_num}_wann', text="--")
            self.canvas.itemconfig(f'transport_row{row_num}_nach', text="--")
            return
        
        # Get line name from first departure
        first_departure = departures[0]
        line_name = first_departure.get('line', {}).get('name', '--')
        
        # Get destination - use direction field and clean it up
        direction = first_departure.get('direction', '')
        # The direction is like "Ringbahn S42 ⟲" - extract meaningful destination
        dest_stop = first_departure.get('destination', {})
        if dest_stop:
            nach = dest_stop.get('name', '--')
            # Clean up station name
            nach = nach.replace(' (Berlin)', '').replace('S ', '').replace('Bhf', '').replace('S+U ', '').strip()
        else:
            nach = direction.split()[-1] if direction else '--'
        
        # Calculate minutes for up to 3 departures
        minutes_list = []
        now = datetime.now()
        
        for dep in departures[:3]:  # Get up to 3 departures
            when_str = dep.get('when')
            delay = dep.get('delay', 0) or 0
            
            if when_str:
                try:
                    # Parse ISO format datetime
                    when_dt = datetime.fromisoformat(when_str.replace('Z', '+00:00'))
                    # Remove timezone for comparison with local time
                    when_local = when_dt.replace(tzinfo=None)
                    
                    # Calculate minutes until departure
                    delta = when_local - now
                    minutes = int(delta.total_seconds() / 60)
                    
                    if minutes < 0:
                        minutes = 0
                    
                    # Format with delay if present (delay is in seconds)
                    if delay > 0:
                        delay_min = delay // 60
                        minutes_list.append(f"{minutes}+{delay_min}")
                    else:
                        minutes_list.append(str(minutes))
                except Exception as e:
                    if self.debug_enabled:
                        print(f"[Transport] Error parsing time: {e}")
                    minutes_list.append("--")
        
        # Pad to 3 items with "?" for missing departures
        while len(minutes_list) < 3:
            minutes_list.append("?")
        
        # Join minutes with spaces
        wann_text = " ".join(minutes_list[:3])
        
        # Update UI
        self.canvas.itemconfig(f'transport_row{row_num}_linie', text=line_name)
        self.canvas.itemconfig(f'transport_row{row_num}_wann', text=wann_text)
        self.canvas.itemconfig(f'transport_row{row_num}_nach', text=nach)
        
        if self.debug_enabled:
            print(f"[Transport] Row {row_num}: {line_name} | {wann_text} | {nach}")
    
    def schedule_transport_update(self):
        """Schedule transport updates using Tkinter's after()"""
        try:
            self.fetch_transport()
        except Exception as e:
            print(f"Error in transport update: {e}")
        # Schedule next update
        self._transport_after_id = self.root.after(TRANSPORT_REFRESH_INTERVAL * 1000, self.schedule_transport_update)
    
    def start_updates(self):
        """Start all update schedules using Tkinter's after() (more efficient than threads on Pi Zero)"""
        # Initial data fetch
        self.get_coordinates_from_city()
        self.fetch_weather()
        self.fetch_air_quality()
        self.fetch_transport()
        self.update_datetime()
        
        # Schedule periodic updates using after() instead of threads
        # This is more efficient on weak hardware as it avoids thread overhead
        # and doesn't require thread-safe UI updates
        self._weather_after_id = self.root.after(REFRESH_INTERVAL * 1000, self.schedule_weather_update)
        self._aqi_after_id = self.root.after(60 * 1000, self.schedule_aqi_update)
        self._time_after_id = self.root.after(TIME_UPDATE_INTERVAL * 1000, self.schedule_time_update)
        self._transport_after_id = self.root.after(TRANSPORT_REFRESH_INTERVAL * 1000, self.schedule_transport_update)


def main():
    root = tk.Tk()
    app = WeatherDisplay(root)
    root.mainloop()


if __name__ == '__main__':
    main()
