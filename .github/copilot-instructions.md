# Pi Weather Display - Rust + Slint Project

## Project Overview
Converting Python Tkinter weather display to Rust with Slint UI framework for better performance on Raspberry Pi Zero W.

## Progress Checklist

- [x] Verify copilot-instructions.md file created
- [x] Clarify Project Requirements - Rust + Slint weather display
- [ ] Scaffold the Rust Project with Cargo
- [ ] Customize with weather APIs and Slint UI
- [ ] Install Required Extensions (rust-analyzer, Slint extension)
- [ ] Compile the Project with cargo build
- [ ] Create and Run Task for cargo run
- [ ] Launch the Project
- [ ] Ensure Documentation is Complete

## Project Structure
```
pi-weather/
├── Cargo.toml
├── src/
│   └── main.rs
├── ui/
│   └── weather_display.slint
├── .env
└── README.md
```

## Key Requirements
- Slint UI framework for modern, hardware-accelerated UI
- Async Rust with tokio runtime
- Open-Meteo API for weather data
- Airly API for air quality data
- Optimized for Raspberry Pi Zero W
- Full-screen two-panel layout with gradient background
