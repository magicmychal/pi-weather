slint::include_modules!();

use chrono::{Local, Timelike};
use serde::Deserialize;
use std::error::Error;
use std::rc::Rc;
use std::cell::RefCell;
use log::{info, error, warn};
use std::path::PathBuf;

// Weather API structures
#[derive(Debug, Deserialize)]
struct WeatherResponse {
    current: CurrentWeather,
}

#[derive(Debug, Deserialize)]
struct CurrentWeather {
    temperature_2m: f64,
    weather_code: i32,
}

// Air Quality structures
#[derive(Debug, Deserialize)]
struct AirlyInstallation {
    id: i32,
}

#[derive(Debug, Deserialize)]
struct AirlyMeasurement {
    current: AirlyCurrentData,
}

#[derive(Debug, Deserialize)]
struct AirlyCurrentData {
    indexes: Vec<AirlyIndex>,
}

#[derive(Debug, Deserialize)]
struct AirlyIndex {
    name: String,
    value: f64,
}

// Gradient computation
#[derive(Clone, Copy)]
struct GradientColors {
    start: (u8, u8, u8),
    end: (u8, u8, u8),
}

fn get_time_phase() -> &'static str {
    let hour = Local::now().hour();
    match hour {
        0..=4 | 21..=23 => "night",
        5..=7 => "sunrise",
        17..=20 => "sunset",
        _ => "day",
    }
}

fn compute_gradient(weather_code: i32) -> GradientColors {
    let phase = get_time_phase();
    
    let rain_codes = [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99];
    let snow_codes = [71, 73, 75, 77, 85, 86];
    let cloudy_codes = [2, 3, 45, 48];
    
    match phase {
        "night" => GradientColors {
            start: (11, 29, 58),
            end: (10, 25, 48),
        },
        "sunrise" => GradientColors {
            start: (255, 207, 113),
            end: (255, 140, 66),
        },
        "sunset" => GradientColors {
            start: (255, 159, 104),
            end: (46, 26, 71),
        },
        _ => {
            // Day - check weather
            if rain_codes.contains(&weather_code) {
                GradientColors {
                    start: (91, 75, 138),
                    end: (60, 47, 88),
                }
            } else if snow_codes.contains(&weather_code) {
                GradientColors {
                    start: (168, 192, 255),
                    end: (63, 43, 150),
                }
            } else if cloudy_codes.contains(&weather_code) {
                GradientColors {
                    start: (127, 141, 161),
                    end: (84, 99, 119),
                }
            } else {
                GradientColors {
                    start: (77, 163, 255),
                    end: (43, 111, 214),
                }
            }
        }
    }
}

fn caqi_to_status(caqi: f64) -> String {
    match caqi as i32 {
        0..=33 => "Can't get better".to_string(),
        34..=66 => "Take a breath in".to_string(),
        67..=99 => "It's ok...".to_string(),
        100..=150 => "Bad, but you won't die.".to_string(),
        _ => "Hazardous!".to_string(),
    }
}

fn weather_code_to_condition(code: i32) -> String {
    match code {
        0 => "Clear Sky".to_string(),
        1 | 2 => "Mostly Clear".to_string(),
        3 => "Overcast".to_string(),
        45 | 48 => "Foggy".to_string(),
        51 | 53 | 55 => "Light Rain".to_string(),
        61 | 63 => "Moderate Rain".to_string(),
        65 => "Heavy Rain".to_string(),
        71 | 73 => "Light Snow".to_string(),
        75 => "Heavy Snow".to_string(),
        77 => "Snow Grains".to_string(),
        80 | 81 => "Rain Showers".to_string(),
        82 => "Heavy Showers".to_string(),
        85 | 86 => "Snow Showers".to_string(),
        95 | 96 | 99 => "Thunderstorm".to_string(),
        _ => "Unknown".to_string(),
    }
}

fn weather_code_to_icon_path(code: i32) -> PathBuf {
    // Map WMO codes to available icons
    // Available icons: sun, moon, rain, snow, thunder
    let base = PathBuf::from("assets/icons");
    match code {
        0 | 1 | 2 | 3 | 45 | 48 => base.join("noun-sun-1367708.png"),
        51 | 53 | 55 | 61 | 63 | 65 | 80 | 81 | 82 => base.join("noun-rain-1367711.png"),
        71 | 73 | 75 | 77 | 85 | 86 => base.join("noun-snow-1367717.png"),
        95 | 96 | 99 => base.join("noun-thunder-1367716.png"),
        _ => base.join("noun-sun-1367708.png"),
    }
}

fn setup_logger() -> Result<(), fern::InitError> {
    fern::Dispatch::new()
        .format(|out, message, record| {
            out.finish(format_args!(
                "[{}] {} - {}",
                record.level(),
                chrono::Local::now().format("%Y-%m-%d %H:%M:%S"),
                message
            ))
        })
        .level(log::LevelFilter::Info)
        .level_for("slint", log::LevelFilter::Warn)
        .chain(
            std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open("pi-logs.log")
                .expect("Failed to open pi-logs.log"),
        )
        .apply()?;
    
    info!("Logger initialized successfully");
    Ok(())
}

async fn fetch_weather(lat: f64, lon: f64) -> Result<(f64, i32), Box<dyn Error>> {
    let url = format!(
        "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,weather_code&timezone=auto",
        lat, lon
    );
    
    info!("Fetching weather data from: {}", url);
    
    let response = reqwest::get(&url).await.map_err(|e| {
        let err_msg = format!("Failed to fetch weather data: {}", e);
        error!("{}", err_msg);
        Box::<dyn Error>::from(e)
    })?;
    
    if !response.status().is_success() {
        let status = response.status();
        let err_msg = format!("Weather API returned status: {}", status);
        error!("{}", err_msg);
        return Err(err_msg.into());
    }
    
    let data: WeatherResponse = response.json().await.map_err(|e| {
        let err_msg = format!("Failed to parse weather response: {}", e);
        error!("{}", err_msg);
        Box::<dyn Error>::from(e)
    })?;
    
    info!("Weather fetched successfully - Temperature: {}°C, Code: {}", 
        data.current.temperature_2m, data.current.weather_code);
    
    Ok((data.current.temperature_2m, data.current.weather_code))
}

// Removed legacy `fetch_air_quality()` (string-only) as it was superseded by
// `fetch_air_quality_with_value()` which also returns numeric AQI for UI bar.

async fn fetch_air_quality_with_value(api_key: &str, lat: f64, lon: f64) -> Result<(String, i32), Box<dyn Error>> {
    let client = reqwest::Client::new();
    
    // Get nearest installation
    let installations_url = format!(
        "https://airapi.airly.eu/v2/installations/nearest?lat={}&lng={}&maxDistanceKM=5&maxResults=1",
        lat, lon
    );
    
    info!("Fetching Airly installations from URL: {}", installations_url);
    
    let response = client
        .get(&installations_url)
        .header("apikey", api_key)
        .send()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to fetch Airly installations: {}", e);
            error!("{}", err_msg);
            Box::<dyn Error>::from(e)
        })?;
    
    if !response.status().is_success() {
        let status = response.status();
        let err_msg = format!("Airly installations API returned status: {}", status);
        error!("{}", err_msg);
        return Err(err_msg.into());
    }
    
    let installations: Vec<AirlyInstallation> = response
        .json()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to parse Airly installations response: {}", e);
            error!("{}", err_msg);
            Box::<dyn Error>::from(e)
        })?;
    
    if installations.is_empty() {
        warn!("No Airly installations found for coordinates: {}, {}", lat, lon);
        return Ok(("No AQI data".to_string(), 0));
    }
    
    let installation_id = installations[0].id;
    info!("Found Airly installation ID: {}", installation_id);
    
    // Get measurements
    let measurements_url = format!(
        "https://airapi.airly.eu/v2/measurements/installation?installationId={}",
        installation_id
    );
    
    info!("Fetching measurements from URL: {}", measurements_url);
    
    let response = client
        .get(&measurements_url)
        .header("apikey", api_key)
        .send()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to fetch Airly measurements: {}", e);
            error!("{}", err_msg);
            Box::<dyn Error>::from(e)
        })?;
    
    if !response.status().is_success() {
        let status = response.status();
        let err_msg = format!("Airly measurements API returned status: {}", status);
        error!("{}", err_msg);
        return Err(err_msg.into());
    }
    
    let measurement: AirlyMeasurement = response
        .json()
        .await
        .map_err(|e| {
            let err_msg = format!("Failed to parse Airly measurements response: {}", e);
            error!("{}", err_msg);
            Box::<dyn Error>::from(e)
        })?;
    
    // Find CAQI index
    for index in &measurement.current.indexes {
        if index.name == "AIRLY_CAQI" {
            let caqi_val = index.value as i32;
            info!("Found AIRLY_CAQI value: {}", index.value);
            return Ok((caqi_to_status(index.value), caqi_val));
        }
    }
    
    warn!("AIRLY_CAQI index not found in response");
    Ok(("AQI unavailable".to_string(), 0))
}

fn main() -> Result<(), Box<dyn Error>> {
    // Initialize logging first
    if let Err(e) = setup_logger() {
        eprintln!("Failed to initialize logger: {}", e);
    }
    
    info!("Application starting...");
    
    // Load environment variables
    dotenvy::dotenv().ok();
    
    let latitude: f64 = std::env::var("AIRLY_LATITUDE")
        .unwrap_or_else(|_| {
            warn!("AIRLY_LATITUDE not found in .env, using default 52.52");
            "52.52".to_string()
        })
        .parse()
        .unwrap_or_else(|e| {
            error!("Failed to parse AIRLY_LATITUDE: {}", e);
            52.52
        });
    
    let longitude: f64 = std::env::var("AIRLY_LONGITUDE")
        .unwrap_or_else(|_| {
            warn!("AIRLY_LONGITUDE not found in .env, using default 13.405");
            "13.405".to_string()
        })
        .parse()
        .unwrap_or_else(|e| {
            error!("Failed to parse AIRLY_LONGITUDE: {}", e);
            13.405
        });
    
    let airly_api_key = std::env::var("AIRLY_API_KEY").ok();
    
    if let Some(ref key) = airly_api_key {
        if key == "your_airly_api_key_here" {
            warn!("AIRLY_API_KEY is set to placeholder value - Air quality data will not be fetched");
        } else {
            info!("AIRLY_API_KEY loaded successfully from .env");
        }
    } else {
        warn!("AIRLY_API_KEY not found in environment - Air quality data will not be fetched");
    }
    
    info!("Configuration loaded - Latitude: {}, Longitude: {}", latitude, longitude);
    
    // Create UI
    let ui = WeatherDisplay::new().map_err(|e| {
        error!("Failed to create UI: {}", e);
        Box::<dyn Error>::from(e)
    })?;
    
    info!("UI created successfully");

    // Set font fallback based on OS
    #[cfg(target_os = "macos")]
    ui.set_font_family_name("Menlo".into());
    #[cfg(target_os = "linux")]
    ui.set_font_family_name("DejaVu Sans Mono".into());
    #[cfg(target_os = "windows")]
    ui.set_font_family_name("Courier New".into());
    
    // Update time every 60 seconds
    let ui_time = ui.as_weak();
    let timer = slint::Timer::default();
    timer.start(
        slint::TimerMode::Repeated,
        std::time::Duration::from_secs(60),
        move || {
            if let Some(ui) = ui_time.upgrade() {
                let now = Local::now();
                ui.set_time_text(now.format("%H:%M").to_string().into());
            }
        },
    );
    
    // Initial data fetch
    ui.set_time_text(Local::now().format("%H:%M").to_string().into());
    
    // Fetch weather data on UI start
    match blocking_fetch_weather(latitude, longitude) {
        Ok((temp, code)) => {
            info!("Initial weather fetch successful");
            ui.set_temperature_text(format!("{}°", temp.round() as i32).into());
            ui.set_condition_text(weather_code_to_condition(code).into());
            // Set condition icon
            let icon_path = weather_code_to_icon_path(code);
            match slint::Image::load_from_path(&icon_path) {
                Ok(img) => ui.set_condition_icon(img),
                Err(e) => warn!("Failed to load condition icon: {}", e),
            }
            let gradient = compute_gradient(code);
            ui.set_gradient_start(GradientColor {
                r: gradient.start.0 as i32,
                g: gradient.start.1 as i32,
                b: gradient.start.2 as i32,
            });
            ui.set_gradient_end(GradientColor {
                r: gradient.end.0 as i32,
                g: gradient.end.1 as i32,
                b: gradient.end.2 as i32,
            });
        }
        Err(e) => {
            error!("Failed to fetch initial weather data: {}", e);
        }
    }
    
    // Fetch air quality data on startup if API key is available
    if let Some(ref api_key) = airly_api_key {
        if api_key != "your_airly_api_key_here" {
            match blocking_fetch_air_quality_with_value(api_key, latitude, longitude) {
                Ok((status, aqi_val)) => {
                    info!("Initial air quality fetch successful: {} (AQI: {})", status, aqi_val);
                    ui.set_air_quality_text(status.into());
                    ui.set_aqi_value(aqi_val);
                }
                Err(e) => {
                    error!("Failed to fetch initial air quality data: {}", e);
                }
            }
        }
    }
    
    // Update weather every 60 minutes
    let ui_weather = ui.as_weak();
    let weather_timer = slint::Timer::default();
    weather_timer.start(
        slint::TimerMode::Repeated,
        std::time::Duration::from_secs(3600),
        move || {
            if let Some(ui) = ui_weather.upgrade() {
                match blocking_fetch_weather(latitude, longitude) {
                    Ok((temp, code)) => {
                        ui.set_temperature_text(format!("{}°", temp.round() as i32).into());
                        ui.set_condition_text(weather_code_to_condition(code).into());
                        // Update condition icon
                        let icon_path = weather_code_to_icon_path(code);
                        match slint::Image::load_from_path(&icon_path) {
                            Ok(img) => ui.set_condition_icon(img),
                            Err(e) => warn!("Failed to load condition icon: {}", e),
                        }
                        
                        let gradient = compute_gradient(code);
                        ui.set_gradient_start(GradientColor {
                            r: gradient.start.0 as i32,
                            g: gradient.start.1 as i32,
                            b: gradient.start.2 as i32,
                        });
                        ui.set_gradient_end(GradientColor {
                            r: gradient.end.0 as i32,
                            g: gradient.end.1 as i32,
                            b: gradient.end.2 as i32,
                        });
                    }
                    Err(e) => {
                        error!("Failed to fetch weather data: {}", e);
                    }
                }
            }
        },
    );
    
    // Update air quality at scheduled hours (6am, 3pm, 8pm)
    if let Some(api_key) = airly_api_key {
        if api_key != "your_airly_api_key_here" {
            info!("Setting up Airly air quality updates");
            let ui_aqi = ui.as_weak();
            let last_hour = Rc::new(RefCell::new(None::<u32>));
            let aqi_timer = slint::Timer::default();
            
            aqi_timer.start(
                slint::TimerMode::Repeated,
                std::time::Duration::from_secs(60),
                move || {
                    let current_hour = Local::now().hour();
                    
                    if [6, 15, 20].contains(&current_hour) {
                        let mut last = last_hour.borrow_mut();
                        if *last != Some(current_hour) {
                            *last = Some(current_hour);
                            drop(last);
                            
                            info!("Fetching air quality data at hour {}", current_hour);
                            if let Some(ui) = ui_aqi.upgrade() {
                                match blocking_fetch_air_quality_with_value(&api_key, latitude, longitude) {
                                    Ok((status, aqi_val)) => {
                                        info!("Air quality update successful: {} (AQI: {})", status, aqi_val);
                                        ui.set_air_quality_text(status.into());
                                        ui.set_aqi_value(aqi_val);
                                    }
                                    Err(e) => {
                                        error!("Failed to fetch air quality data: {}", e);
                                    }
                                }
                            }
                        }
                    }
                },
            );
            std::mem::forget(aqi_timer);
        } else {
            warn!("Airly API key is placeholder - skipping air quality updates");
        }
    } else {
        warn!("No Airly API key configured - air quality updates disabled");
    }
    
    std::mem::forget(timer);
    std::mem::forget(weather_timer);
    
    // Run UI
    info!("Starting UI...");
    ui.run().map_err(|e| {
        error!("UI runtime error: {}", e);
        Box::<dyn Error>::from(e)
    })?;
    
    info!("Application terminated gracefully");
    
    Ok(())
}

// Blocking wrapper for weather fetch (synchronous from Slint perspective)
fn blocking_fetch_weather(lat: f64, lon: f64) -> Result<(f64, i32), Box<dyn Error>> {
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()?;
    rt.block_on(fetch_weather(lat, lon))
}

// Removed legacy `blocking_fetch_air_quality()` wrapper; use
// `blocking_fetch_air_quality_with_value()` which also provides numeric AQI.

// Blocking wrapper for air quality fetch with numeric value
fn blocking_fetch_air_quality_with_value(api_key: &str, lat: f64, lon: f64) -> Result<(String, i32), Box<dyn Error>> {
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()?;
    let api_key = api_key.to_string();
    rt.block_on(fetch_air_quality_with_value(&api_key, lat, lon))
}
