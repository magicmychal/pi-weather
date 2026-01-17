# Airly API & Logging - Quick Reference

## What Was Changed

### 1. **Fixed Airly API Error Handling**
- Detects placeholder API keys and logs warnings
- Added HTTP status code checking
- Logs all API calls, responses, and errors to `pi-logs.log`
- Proper error context with detailed messages

### 2. **Implemented Logging System**
- All runtime errors and events logged to `pi-logs.log`
- Timestamp, log level, and message for each entry
- Persists across application restarts

### 3. **Key Log Messages**

| Event | Log Level | Example |
|-------|-----------|---------|
| App startup | INFO | "Application starting..." |
| Config loaded | INFO | "Configuration loaded - Latitude: 52.52, Longitude: 13.405" |
| Weather fetch | INFO | "Fetching weather data from: https://api..." |
| Weather success | INFO | "Weather fetched successfully - Temperature: 3.2°C, Code: 2" |
| Airly fetch | INFO | "Fetching Airly installations from URL: ..." |
| Airly success | INFO | "Found AIRLY_CAQI value: 45" |
| API failure | ERROR | "Failed to fetch Airly installations: connection refused" |
| Missing key | WARN | "AIRLY_API_KEY not found in environment" |
| Placeholder key | WARN | "AIRLY_API_KEY is set to placeholder value" |

## How to Use

### Check the logs:
```bash
tail -f pi-logs.log          # Real-time log monitoring
cat pi-logs.log              # View entire log
grep ERROR pi-logs.log       # Find all errors
grep "Failed to fetch" pi-logs.log  # Find specific failures
```

### Configure Airly API:
1. Get your API key from https://developer.airly.eu/
2. Update `.env`:
```env
AIRLY_API_KEY=your_actual_key_here
AIRLY_LATITUDE=52.52
AIRLY_LONGITUDE=13.405
```

### Troubleshooting Airly Issues:

**Issue**: "No AQI data" displayed
- **Check**: `grep "Airly" pi-logs.log` for API responses
- **Solution**: Verify coordinates have nearby monitoring stations (5km radius)

**Issue**: "AQI unavailable" displayed
- **Check**: `grep "AIRLY_CAQI" pi-logs.log`
- **Solution**: API might be returning different index names

**Issue**: Air quality never updates
- **Check**: `grep "AIRLY_API_KEY" pi-logs.log`
- **Solution**: Ensure key is not placeholder and valid

## Files Modified

- `Cargo.toml` - Added `log` and `fern` dependencies
- `src/main.rs` - Added logging, improved error handling
- `pi-logs.log` - Created automatically on first run

## Technical Details

- **Logger**: Initialized at startup in `setup_logger()`
- **Log File**: Appends to `pi-logs.log` in project root
- **Format**: `[LEVEL] YYYY-MM-DD HH:MM:SS - message`
- **Log Level**: INFO (warnings and errors always shown)
- **Async Safe**: Works with Slint timers and tokio runtime
