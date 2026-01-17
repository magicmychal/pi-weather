import { useEffect, useState } from 'react';

interface WeatherData {
  temperature: number;
  condition: string;
  airQuality: string;
  airQualityIndex: number;
}

export function RetroWeatherPanel() {
  const [weather, setWeather] = useState<WeatherData>({
    temperature: 72,
    condition: 'Partly Cloudy',
    airQuality: 'Good',
    airQualityIndex: 45
  });

  // Simulate weather updates
  useEffect(() => {
    const interval = setInterval(() => {
      const conditions = ['Sunny', 'Partly Cloudy', 'Cloudy', 'Clear'];
      const qualities = ['Good', 'Moderate', 'Fair'];
      
      setWeather({
        temperature: Math.floor(Math.random() * 20) + 65,
        condition: conditions[Math.floor(Math.random() * conditions.length)],
        airQuality: qualities[Math.floor(Math.random() * qualities.length)],
        airQualityIndex: Math.floor(Math.random() * 100) + 20
      });
    }, 30000); // Update every 30 seconds

    return () => clearInterval(interval);
  }, []);

  const getAQIColor = (aqi: number) => {
    if (aqi <= 50) return '#00ff00';
    if (aqi <= 100) return '#ffff00';
    if (aqi <= 150) return '#ff9900';
    return '#ff0000';
  };

  return (
    <div className="h-full p-8 bg-gradient-to-br from-gray-400 to-gray-500 flex flex-col justify-center gap-8">
      {/* Temperature Panel */}
      <div className="bg-gradient-to-br from-gray-300 to-gray-400 p-6 rounded-lg border-4 border-gray-600" style={{
        boxShadow: 'inset -2px -2px 4px rgba(255,255,255,0.5), inset 2px 2px 4px rgba(0,0,0,0.3), 4px 4px 12px rgba(0,0,0,0.4)'
      }}>
        <div className="bg-gray-800 border-4 border-gray-600 p-6 rounded" style={{
          boxShadow: 'inset 2px 2px 4px rgba(0,0,0,0.6)'
        }}>
          <div className="text-cyan-400 text-2xl font-mono mb-2 uppercase tracking-wider" style={{
            textShadow: '0 0 5px rgba(0,255,255,0.6)',
            fontFamily: 'Courier New, monospace'
          }}>
            ═══ TEMPERATURE ═══
          </div>
          <div className="flex items-baseline gap-2">
            <div className="text-9xl font-mono font-bold text-green-400" style={{
              textShadow: '0 0 15px rgba(0,255,0,0.8), 0 0 30px rgba(0,255,0,0.5)',
              fontFamily: 'Courier New, monospace',
              lineHeight: '1'
            }}>
              {weather.temperature}
            </div>
            <div className="text-6xl font-mono text-green-400 mb-4" style={{
              textShadow: '0 0 10px rgba(0,255,0,0.8)',
              fontFamily: 'Courier New, monospace'
            }}>
              °F
            </div>
          </div>
        </div>
      </div>

      {/* Condition Panel */}
      <div className="bg-gradient-to-br from-gray-300 to-gray-400 p-6 rounded-lg border-4 border-gray-600" style={{
        boxShadow: 'inset -2px -2px 4px rgba(255,255,255,0.5), inset 2px 2px 4px rgba(0,0,0,0.3), 4px 4px 12px rgba(0,0,0,0.4)'
      }}>
        <div className="bg-gray-800 border-4 border-gray-600 p-6 rounded" style={{
          boxShadow: 'inset 2px 2px 4px rgba(0,0,0,0.6)'
        }}>
          <div className="text-cyan-400 text-2xl font-mono mb-3 uppercase tracking-wider" style={{
            textShadow: '0 0 5px rgba(0,255,255,0.6)',
            fontFamily: 'Courier New, monospace'
          }}>
            ═══ CONDITION ═══
          </div>
          <div className="text-5xl font-mono font-bold text-amber-400 uppercase" style={{
            textShadow: '0 0 10px rgba(255,191,0,0.8), 0 0 20px rgba(255,191,0,0.5)',
            fontFamily: 'Courier New, monospace'
          }}>
            {weather.condition}
          </div>
        </div>
      </div>

      {/* Air Quality Panel */}
      <div className="bg-gradient-to-br from-gray-300 to-gray-400 p-6 rounded-lg border-4 border-gray-600" style={{
        boxShadow: 'inset -2px -2px 4px rgba(255,255,255,0.5), inset 2px 2px 4px rgba(0,0,0,0.3), 4px 4px 12px rgba(0,0,0,0.4)'
      }}>
        <div className="bg-gray-800 border-4 border-gray-600 p-6 rounded" style={{
          boxShadow: 'inset 2px 2px 4px rgba(0,0,0,0.6)'
        }}>
          <div className="text-cyan-400 text-2xl font-mono mb-3 uppercase tracking-wider" style={{
            textShadow: '0 0 5px rgba(0,255,255,0.6)',
            fontFamily: 'Courier New, monospace'
          }}>
            ═══ AIR QUALITY ═══
          </div>
          <div className="flex items-center justify-between mb-4">
            <div className="text-5xl font-mono font-bold uppercase" style={{
              color: getAQIColor(weather.airQualityIndex),
              textShadow: `0 0 10px ${getAQIColor(weather.airQualityIndex)}80, 0 0 20px ${getAQIColor(weather.airQualityIndex)}40`,
              fontFamily: 'Courier New, monospace'
            }}>
              {weather.airQuality}
            </div>
          </div>
          
          {/* AQI Bar Graph */}
          <div className="space-y-2">
            <div className="text-xl font-mono text-cyan-400" style={{
              fontFamily: 'Courier New, monospace'
            }}>
              AQI: {weather.airQualityIndex}
            </div>
            <div className="w-full bg-gray-900 h-8 border-2 border-gray-600 rounded overflow-hidden" style={{
              boxShadow: 'inset 2px 2px 4px rgba(0,0,0,0.8)'
            }}>
              <div 
                className="h-full transition-all duration-1000"
                style={{
                  width: `${Math.min(weather.airQualityIndex, 200) / 2}%`,
                  backgroundColor: getAQIColor(weather.airQualityIndex),
                  boxShadow: `0 0 10px ${getAQIColor(weather.airQualityIndex)}`
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* System Status Bar */}
      <div className="bg-black border-2 border-gray-600 px-4 py-2 rounded flex items-center justify-between" style={{
        boxShadow: 'inset 1px 1px 2px rgba(0,0,0,0.5)'
      }}>
        <div className="text-green-400 font-mono text-sm" style={{
          fontFamily: 'Courier New, monospace',
          textShadow: '0 0 5px rgba(0,255,0,0.5)'
        }}>
          SYSTEM READY
        </div>
        <div className="flex gap-2">
          <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" style={{
            boxShadow: '0 0 8px rgba(0,255,0,0.8)'
          }}></div>
          <div className="text-green-400 font-mono text-sm" style={{
            fontFamily: 'Courier New, monospace'
          }}>
            {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
          </div>
        </div>
      </div>
    </div>
  );
}
