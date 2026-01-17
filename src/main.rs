slint::include_modules!();

use chrono::{Local, Timelike};
use serde::Deserialize;
use std::error::Error;
use std::rc::Rc;
use std::cell::RefCell;

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
        0..=33 => "A-MAZE-BALLS".to_string(),
        34..=66 => "Open the windows, go out!".to_string(),
        67..=99 => "It's ok...".to_string(),
        100..=150 => "Bad, but will survive".to_string(),
        _ => "Hazardous, do not open the windows".to_string(),
    }
}

async fn fetch_weather(lat: f64, lon: f64) -> Result<(f64, i32), Box<dyn Error>> {
    let url = format!(
        "https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&current=temperature_2m,weather_code&timezone=auto",
        lat, lon
    );
    
    let response = reqwest::get(&url).await?;
    let data: WeatherResponse = response.json().await?;
    
    Ok((data.current.temperature_2m, data.current.weather_code))
}

async fn fetch_air_quality(api_key: &str, lat: f64, lon: f64) -> Result<String, Box<dyn Error>> {
    let client = reqwest::Client::new();
    
    // Get nearest installation
    let installations_url = format!(
        "https://airapi.airly.eu/v2/installations/nearest?lat={}&lng={}&maxDistanceKM=5&maxResults=1",
        lat, lon
    );
    
    let installations: Vec<AirlyInstallation> = client
        .get(&installations_url)
        .header("apikey", api_key)
        .send()
        .await?
        .json()
        .await?;
    
    if installations.is_empty() {
        return Ok("No AQI data".to_string());
    }
    
    let installation_id = installations[0].id;
    
    // Get measurements
    let measurements_url = format!(
        "https://airapi.airly.eu/v2/measurements/installation?installationId={}",
        installation_id
    );
    
    let measurement: AirlyMeasurement = client
        .get(&measurements_url)
        .header("apikey", api_key)
        .send()
        .await?
        .json()
        .await?;
    
    // Find CAQI index
    for index in &measurement.current.indexes {
        if index.name == "AIRLY_CAQI" {
            return Ok(caqi_to_status(index.value));
        }
    }
    
    Ok("AQI unavailable".to_string())
}

fn main() -> Result<(), Box<dyn Error>> {
    // Load environment variables
    dotenvy::dotenv().ok();
    
    let latitude: f64 = std::env::var("AIRLY_LATITUDE")
        .unwrap_or_else(|_| "52.52".to_string())
        .parse()
        .unwrap_or(52.52);
    
    let longitude: f64 = std::env::var("AIRLY_LONGITUDE")
        .unwrap_or_else(|_| "13.405".to_string())
        .parse()
        .unwrap_or(13.405);
    
    let airly_api_key = std::env::var("AIRLY_API_KEY").ok();
    
    // Create UI
    let ui = WeatherDisplay::new()?;
    
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
    if let Ok((temp, code)) = blocking_fetch_weather(latitude, longitude) {
        ui.set_temperature_text(format!("{}°", temp.round() as i32).into());
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
    
    // Update weather every 10 minutes
    let ui_weather = ui.as_weak();
    let weather_timer = slint::Timer::default();
    weather_timer.start(
        slint::TimerMode::Repeated,
        std::time::Duration::from_secs(600),
        move || {
            if let Some(ui) = ui_weather.upgrade() {
                if let Ok((temp, code)) = blocking_fetch_weather(latitude, longitude) {
                    ui.set_temperature_text(format!("{}°", temp.round() as i32).into());
                    
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
            }
        },
    );
    
    // Update air quality at scheduled hours (6am, 3pm, 8pm)
    if let Some(api_key) = airly_api_key {
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
                        
                        if let Some(ui) = ui_aqi.upgrade() {
                            if let Ok(status) = blocking_fetch_air_quality(&api_key, latitude, longitude) {
                                ui.set_air_quality_text(status.into());
                            }
                        }
                    }
                }
            },
        );
        std::mem::forget(aqi_timer);
    }
    
    std::mem::forget(timer);
    std::mem::forget(weather_timer);
    
    // Run UI
    ui.run()?;
    
    Ok(())
}

// Blocking wrapper for weather fetch (synchronous from Slint perspective)
fn blocking_fetch_weather(lat: f64, lon: f64) -> Result<(f64, i32), Box<dyn Error>> {
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()?;
    rt.block_on(fetch_weather(lat, lon))
}

// Blocking wrapper for air quality fetch
fn blocking_fetch_air_quality(api_key: &str, lat: f64, lon: f64) -> Result<String, Box<dyn Error>> {
    let rt = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()?;
    let api_key = api_key.to_string();
    rt.block_on(fetch_air_quality(&api_key, lat, lon))
}
