# Pi Weather Display

A fullscreen weather display application designed for Raspberry Pi, showing real-time weather information with a beautiful map background.

## Features

- Real-time weather data display
- Temperature and weather conditions
- Interactive map background
- Fullscreen kiosk mode for Raspberry Pi
- Auto-start on boot

## Setup Instructions for Raspberry Pi

### Prerequisites

1. Raspberry Pi with Raspberry Pi OS (formerly Raspbian) installed
2. Internet connection
3. Chromium browser (usually pre-installed)

### Installation Steps

#### 1. Install Required Packages

Open a terminal on your Raspberry Pi and run:

```bash
sudo apt-get update
sudo apt-get install -y chromium-browser unclutter xdotool
```

- `chromium-browser`: Web browser for displaying the app
- `unclutter`: Hides the mouse cursor after inactivity
- `xdotool`: Utility for window management (optional but recommended)

#### 2. Clone or Copy the Project

Clone this repository or copy all project files to your Raspberry Pi:

```bash
cd ~
git clone <your-repository-url> pi-weather
cd pi-weather
```

Or if you're copying files manually, ensure all files are in a single directory (e.g., `/home/pi/pi-weather/`).

#### 3. Make the Startup Script Executable

```bash
chmod +x start-kiosk.sh
```

#### 4. Configure Autostart

Create an autostart entry to launch the kiosk on boot:

```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/pi-weather.desktop
```

Paste the following content (adjust the path if your project is in a different location):

```ini
[Desktop Entry]
Type=Application
Name=Pi Weather Kiosk
Exec=/home/pi/pi-weather/start-kiosk.sh
X-GNOME-Autostart-enabled=true
```

Save and exit (Ctrl+X, then Y, then Enter).

#### 5. Disable Screen Blanking (Optional but Recommended)

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

#### 6. Configure Weather API (if needed)

If your weather application requires an API key, edit `scripts.js` and add your API credentials.

#### 7. Reboot

```bash
sudo reboot
```

After rebooting, the weather display should automatically launch in fullscreen mode!

## Manual Testing

To test the kiosk mode without rebooting:

```bash
cd /home/pi/pi-weather
./start-kiosk.sh
```

Press `Alt+F4` or `Ctrl+W` to exit fullscreen mode for testing.

## Troubleshooting

### Display doesn't start automatically
- Check that the path in `pi-weather.desktop` matches your actual project location
- Verify the script has execute permissions: `ls -l start-kiosk.sh`
- Check logs: `cat ~/.xsession-errors`

### Chromium shows error pages
- Ensure all files (index.html, scripts.js, styles.css) are in the same directory
- Check file permissions: `chmod 644 index.html scripts.js styles.css`
- Verify internet connection for external resources

### Mouse cursor is visible
- Ensure `unclutter` is installed: `sudo apt-get install unclutter`
- Check if unclutter is running: `ps aux | grep unclutter`

### Screen goes blank
- Verify screen blanking is disabled in lightdm.conf
- Add `xset s off` commands to the start script (already included)

## Stopping the Kiosk

To exit kiosk mode:
- Press `Alt+F4` to close Chromium
- Or SSH into the Pi and run: `pkill chromium-browser`

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
├── index.html          # Main HTML file
├── scripts.js          # JavaScript for weather functionality
├── styles.css          # Styling
├── start-kiosk.sh      # Kiosk mode startup script
└── README.md           # This file
```

## License

See LICENSE file for details.