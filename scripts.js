// Configuration
const REFRESH_INTERVAL = 600000; // Refresh every 10 minutes

// Set your location here (city name and country)
const LOCATION = {
    city: 'Berlin',
    country: 'Germany'
};

let latitude = null;
let longitude = null;
let locationName = '';

// Weather code to description and emoji mapping (Open-Meteo WMO Weather interpretation codes)
const weatherCodes = {
    0: { description: 'Clear sky', icon: '☀️' },
    1: { description: 'Mainly clear', icon: '🌤️' },
    2: { description: 'Partly cloudy', icon: '⛅' },
    3: { description: 'Overcast', icon: '☁️' },
    45: { description: 'Foggy', icon: '🌫️' },
    48: { description: 'Depositing rime fog', icon: '🌫️' },
    51: { description: 'Light drizzle', icon: '🌦️' },
    53: { description: 'Moderate drizzle', icon: '🌦️' },
    55: { description: 'Dense drizzle', icon: '🌧️' },
    61: { description: 'Slight rain', icon: '🌧️' },
    63: { description: 'Moderate rain', icon: '🌧️' },
    65: { description: 'Heavy rain', icon: '⛈️' },
    71: { description: 'Slight snow', icon: '🌨️' },
    73: { description: 'Moderate snow', icon: '❄️' },
    75: { description: 'Heavy snow', icon: '❄️' },
    77: { description: 'Snow grains', icon: '❄️' },
    80: { description: 'Slight rain showers', icon: '🌦️' },
    81: { description: 'Moderate rain showers', icon: '🌧️' },
    82: { description: 'Violent rain showers', icon: '⛈️' },
    85: { description: 'Slight snow showers', icon: '🌨️' },
    86: { description: 'Heavy snow showers', icon: '❄️' },
    95: { description: 'Thunderstorm', icon: '⛈️' },
    96: { description: 'Thunderstorm with slight hail', icon: '⛈️' },
    99: { description: 'Thunderstorm with heavy hail', icon: '⛈️' }
};

// Get coordinates from city name using geocoding
async function getCoordinatesFromCity() {
    try {
        const response = await fetch(
            `https://geocoding-api.open-meteo.com/v1/search?name=${LOCATION.city}&count=1&language=en&format=json`
        );
        const data = await response.json();
        
        if (data.results && data.results.length > 0) {
            const result = data.results[0];
            latitude = result.latitude;
            longitude = result.longitude;
            
            // Set location name from the configured city
            locationName = LOCATION.city;
            if (LOCATION.country) {
                locationName += `, ${LOCATION.country}`;
            }
        } else {
            throw new Error('Location not found');
        }
    } catch (error) {
        console.error('Error getting coordinates:', error);
        // Fallback to Berlin coordinates
        latitude = 52.52;
        longitude = 13.405;
        locationName = 'Berlin, Germany';
    }
    
    document.getElementById('location').textContent = locationName;
}

// Fetch weather data from Open-Meteo API
async function fetchWeather() {
    try {
        const url = `https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=auto&forecast_days=5`;
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error('Weather data fetch failed');
        }
        
        const data = await response.json();
        updateWeatherDisplay(data);
    } catch (error) {
        console.error('Error fetching weather:', error);
        document.getElementById('temperature').textContent = 'Error';
        document.getElementById('description').textContent = 'Unable to fetch weather data';
    }
}

// Update the weather display with fetched data
function updateWeatherDisplay(data) {
    const current = data.current;
    
    // Current temperature
    const temp = Math.round(current.temperature_2m);
    document.getElementById('temperature').textContent = `${temp}°`;
    
    // Weather description
    const weatherCode = current.weather_code;
    const weather = weatherCodes[weatherCode] || { description: 'Unknown', icon: '❓' };
    document.getElementById('description').textContent = weather.description;
}

// Update date and time display
function updateDateTime() {
    const now = new Date();
    const options = { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    document.getElementById('datetime').textContent = now.toLocaleDateString('en-US', options);
}

// Initialize the app
async function init() {
    try {
        await getCoordinatesFromCity();
        await fetchWeather();
        updateDateTime();
        
        // Update time every minute
        setInterval(updateDateTime, 60000);
        
        // Refresh weather data periodically
        setInterval(fetchWeather, REFRESH_INTERVAL);
    } catch (error) {
        console.error('Initialization error:', error);
        document.getElementById('location').textContent = 'Error loading weather';
    }
}

// Start the app when the page loads
window.addEventListener('load', init);
