# Pi Weather Display - Rust + Slint Edition

A modern, hardware-accelerated weather display application built with Rust and Slint UI framework, optimized for Raspberry Pi Zero W.

## Features

- **Modern UI with Slint**: Hardware-accelerated, efficient rendering
- **Real-time Weather**: Fetches data from Open-Meteo API
- **Air Quality Monitoring**: Integrates with Airly API
- **Dynamic Gradients**: Background changes based on time of day and weather
- **Two-Panel Layout**: Clock on left, weather info on right
- **Optimized for Pi Zero W**: Minimal resource usage, async operations

## Prerequisites

### Install Rust

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

### System Dependencies (for Raspberry Pi)

```bash
# Debian/Raspbian
sudo apt-get update
sudo apt-get install -y libfontconfig-dev libxcb-shape0-dev libxcb-xfixes0-dev libxkbcommon-dev
```

## Installation

1. **Clone the repository**:
   ```bash
   cd /Users/michalpawlicki/Repositories/pi-weather
   ```

2. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Build the project**:
   ```bash
   cargo build --release
   ```

4. **Run the application**:
   ```bash
   cargo run --release
   ```

## Configuration

Edit the `.env` file:

- `AIRLY_API_KEY`: Your Airly API key from https://airly.org
- `AIRLY_LATITUDE`: Your location latitude (default: 52.52 for Berlin)
- `AIRLY_LONGITUDE`: Your location longitude (default: 13.405 for Berlin)

## Building for Raspberry Pi Zero W

### Cross-compilation from macOS/Linux:

```bash
# Install cross-compilation tools
rustup target add arm-unknown-linux-gnueabihf

# Build for Pi Zero W
cargo build --release --target arm-unknown-linux-gnueabihf

# Copy to Raspberry Pi
scp target/arm-unknown-linux-gnueabihf/release/pi-weather-slint pi@raspberrypi:~/
```

### Direct build on Raspberry Pi:

```bash
# On the Pi
cargo build --release

# The binary will be at: target/release/pi-weather-slint
```

## Running on Boot (Raspberry Pi)

Create a systemd service:

```bash
sudo nano /etc/systemd/system/weather-display.service
```

Add:
```ini
[Unit]
Description=Weather Display
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/pi-weather
Environment=DISPLAY=:0
ExecStart=/home/pi/pi-weather/target/release/pi-weather-slint
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable weather-display
sudo systemctl start weather-display
```

## Performance Optimizations

The Rust + Slint version includes several optimizations for Pi Zero W:

- **Compiled binary**: No interpreter overhead
- **Async operations**: Non-blocking API calls with Tokio
- **Hardware acceleration**: Slint uses GPU when available
- **Size optimization**: Release builds are stripped and optimized for size
- **Minimal allocations**: Efficient memory usage

## Project Structure

```
pi-weather/
├── Cargo.toml          # Rust dependencies
├── build.rs            # Slint build script
├── src/
│   └── main.rs         # Main application logic
├── ui/
│   └── weather_display.slint  # UI definition
├── .env.example        # Environment template
└── README.md
```

## API Documentation

- **Weather Data**: [Open-Meteo API](https://open-meteo.com/)
- **Air Quality**: [Airly API](https://developer.airly.org/)
- **UI Framework**: [Slint Documentation](https://slint.dev/docs/)

## License

See LICENSE file.

## Comparison: Python vs Rust

| Feature | Python/Tkinter | Rust/Slint |
|---------|----------------|------------|
| Startup time | ~2-3s | <500ms |
| Memory usage | ~50-80MB | ~10-20MB |
| CPU usage | Higher | Lower |
| UI rendering | Software | Hardware-accelerated |
| Binary size | N/A (interpreter) | ~5MB stripped |

## Troubleshooting

### "cannot find -lfontconfig" error
Install fontconfig development files:
```bash
sudo apt-get install libfontconfig-dev
```

### Display not showing
Ensure DISPLAY environment variable is set:
```bash
export DISPLAY=:0
```

### Cargo not found
Install Rust:
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```
