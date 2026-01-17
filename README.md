# Pi Weather Display

A fullscreen weather display application designed for Raspberry Pi, showing real-time weather information with a beautiful gradient background.

## Features

- Real-time weather data display
- Temperature and weather conditions
- Left-side large clock with a center divider; right-side condensed weather panel (temperature, condition, air quality)
- Air quality via Airly API with verbal status (e.g., "Open the windows, go out!") and scheduled updates at 06:00, 15:00, and 20:00
- Beautiful time/weather-aware gradient background
- Airly logo displayed at the bottom-right
- Gradient Demo button (debug-only)
- Fullscreen kiosk mode for Raspberry Pi
- Auto-start on boot

## Setup Instructions for Raspberry Pi

### Prerequisites

1. Raspberry Pi with Raspberry Pi OS (formerly Raspbian) installed
2. Internet connection
3. **Choose one:**
   - **Native Python version** (recommended for Pi Zero W): Python 3 + Tkinter (pre-installed)

### Installation Steps

## Option A: Native Python Version (Recommended for Pi Zero W)

The Python version is much lighter and faster on limited hardware like the Pi Zero W.

#### 1. Install Required Packages

Open a terminal on your Raspberry Pi and run:

```bash
sudo apt-get update
sudo apt-get install -y python3-tk python3-requests unclutter
```

- `python3-tk`: Tkinter GUI library (usually pre-installed)
- `python3-requests`: HTTP library for API calls
- `unclutter`: Hides the mouse cursor after inactivity

#### 2. Create a Python Virtual Environment (recommended)

From the project root, create and activate `.venv`, then install dependencies:

```bash
cd /home/pi/pi-weather
python3 -m venv .venv
source .venv/bin/activate
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

The startup scripts will automatically activate `.venv` if it exists.

#### 3. Clone or Copy the Project

Clone this repository or copy all project files to your Raspberry Pi:

```bash
cd ~
git clone <your-repository-url> pi-weather
cd pi-weather
```

Or if you're copying files manually, ensure all files are in a single directory (e.g., `/home/pi/pi-weather/`).

#### 4. Make the Startup Script Executable

```bash
chmod +x start-native.sh
```

#### 5. Configure Autostart

Create an autostart entry to launch the kiosk on boot:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/pi-weather.desktop
```

Paste the following content (adjust the path if your project is in a different location):

```ini
[Desktop Entry]
Type=Application
Name=Pi Weather Display
Exec=/home/pi/pi-weather/start-native.sh
X-GNOME-Autostart-enabled=true
```

Save and exit (Ctrl+X, then Y, then Enter).

#### 6. Disable Screen Blanking (Optional but Recommended)

Edit the lightdm configuration:

```bash
sudo nano /etc/lightdm/lightdm.conf
```

Find the `[Seat:*]` section and add or modify:

```ini
[Seat:*]
xserver-command=X -s 0 -dpms
```

Save and exit.

#### 7. Configure Your Location

Edit `weather_display.py` and change the location:

```python
LOCATION = {
    'city': 'Your City',
    'country': 'Your Country'
}
```

#### 8. Configure Environment Variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` and set:

```
AIRLY_API_KEY=your_airly_api_key
AIRLY_LATITUDE=52.52
AIRLY_LONGITUDE=13.405
AIRLY_MAX_DISTANCE_KM=5
DEBUG=false
```

- `DEBUG=true` shows the Gradient Demo button; `false` hides it.
- Latitude/longitude are used to locate the nearest Airly installation.

#### 9. Reboot

```bash
sudo reboot
```

After rebooting, the weather display should automatically launch in fullscreen mode!

## Manual Testing

To test without rebooting:

**Python version:**
```bash
cd /home/pi/pi-weather
source .venv/bin/activate  # if created
python3 weather_display.py
```
Press `Escape` to exit fullscreen, `F11` to re-enter fullscreen.

**Web version:**
```bash
cd /home/pi/pi-weather
source .venv/bin/activate  # if created
./start-kiosk.sh
```
Press `Alt+F4` or `Ctrl+W` to exit.

## Option B: Web Version (NetSurf or Chromium)

If you prefer the web version:

#### 1. Install Browser

**For NetSurf (lightweight):**
```bash
sudo apt-get install netsurf-gtk
```

**For Chromium:**
```bash
sudo apt-get install chromium-browser
```

#### 2. Use the Web Startup Script

```bash
chmod +x start-kiosk.sh
```

Edit `start-kiosk.sh` to use `netsurf-gtk` instead of `chromium-browser` if desired.

#### 3. Configure Location

Edit `scripts.js` and change the location in the LOCATION constant.

## Troubleshooting

### Display doesn't start automatically
- Check that the path in `pi-weather.desktop` matches your actual project location
- Verify the script has execute permissions: `ls -l start-native.sh`
- Check logs: `cat ~/.xsession-errors`

### Python version shows errors
- Ensure Python 3 is installed: `python3 --version`
- Install missing packages: `sudo apt-get install python3-tk python3-requests`
- Install Python dependencies: `pip3 install -r requirements.txt`
- Verify internet connection for API calls
- Check for errors: `python3 weather_display.py`

### Airly logo not visible
- Ensure internet access to the Airly CDN
- Confirm Pillow is installed: `pip3 install Pillow`
- The app falls back to a text placeholder if the image cannot be fetched

### Browser version shows error pages
- Ensure all files (index.html, scripts.js, styles.css) are in the same directory
- Check file permissions: `chmod 644 index.html scripts.js styles.css`
- Verify internet connection for external resources

### Mouse cursor is visible
- Ensure `unclutter` is installed: `sudo apt-get install unclutter`
- Check if unclutter is running: `ps aux | grep unclutter`

### Screen goes blank
- Verify screen blanking is disabled in lightdm.conf
- Add `xset s off` commands to the start script (already included)

## Stopping the Display

**Python version:**
- Press `Escape` to exit fullscreen (won't close the app)
- Or SSH into the Pi and run: `pkill -f weather_display.py`

**Browser version:**
- Press `Alt+F4` to close the browser
- Or SSH into the Pi and run: `pkill chromium-browser` or `pkill netsurf-gtk`

## Customization

### Change Refresh Interval
Edit `start-kiosk.sh` and uncomment the auto-reload section at the bottom to automatically refresh the page every 24 hours.

### Modify Startup Delay
If the display loads too quickly (before network is ready), increase the `sleep` value in `start-kiosk.sh`:

```bash
sleep 15  # Wait 15 seconds instead of 10
```

## File Structure

```
pi-weather/
├── weather_display.py  # Native Python application (recommended)
├── start-native.sh     # Startup script for Python version
├── index.html          # Web version HTML
├── scripts.js          # Web version JavaScript
├── styles.css          # Web version styling
├── start-kiosk.sh      # Web version startup script
├── requirements.txt    # Python dependencies (requests, python-dotenv, Pillow)
├── .env.example        # Environment variable template
└── README.md           # This file
```

## License

See LICENSE file for details.