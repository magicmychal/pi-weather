import { useEffect, useState } from 'react';

export function RetroAnalogClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const hours = time.getHours() % 12;
  const minutes = time.getMinutes();
  const seconds = time.getSeconds();

  const hourAngle = (hours * 30) + (minutes * 0.5);
  const minuteAngle = minutes * 6;
  const secondAngle = seconds * 6;

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 bg-gradient-to-br from-gray-300 to-gray-400">
      {/* Clock container with retro border */}
      <div className="relative" style={{
        width: '400px',
        height: '400px',
        background: 'linear-gradient(145deg, #e0e0e0, #f5f5f5)',
        borderRadius: '50%',
        boxShadow: 'inset 6px 6px 12px #bebebe, inset -6px -6px 12px #ffffff, 8px 8px 16px rgba(0,0,0,0.3)',
        border: '12px solid #c0c0c0',
      }}>
        {/* Clock face */}
        <div className="absolute inset-0 flex items-center justify-center">
          <svg width="100%" height="100%" viewBox="0 0 400 400">
            {/* Hour markers */}
            {[...Array(12)].map((_, i) => {
              const angle = (i * 30 - 90) * (Math.PI / 180);
              const x1 = 200 + Math.cos(angle) * 160;
              const y1 = 200 + Math.sin(angle) * 160;
              const x2 = 200 + Math.cos(angle) * 180;
              const y2 = 200 + Math.sin(angle) * 180;
              
              return (
                <g key={i}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="#333"
                    strokeWidth="8"
                    strokeLinecap="round"
                  />
                  <text
                    x={200 + Math.cos(angle) * 135}
                    y={200 + Math.sin(angle) * 135 + 8}
                    textAnchor="middle"
                    fontSize="32"
                    fontFamily="monospace"
                    fontWeight="bold"
                    fill="#000"
                  >
                    {i === 0 ? 12 : i}
                  </text>
                </g>
              );
            })}

            {/* Hour hand */}
            <line
              x1="200"
              y1="200"
              x2={200 + Math.cos((hourAngle - 90) * (Math.PI / 180)) * 90}
              y2={200 + Math.sin((hourAngle - 90) * (Math.PI / 180)) * 90}
              stroke="#222"
              strokeWidth="12"
              strokeLinecap="round"
              style={{
                filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.5))'
              }}
            />

            {/* Minute hand */}
            <line
              x1="200"
              y1="200"
              x2={200 + Math.cos((minuteAngle - 90) * (Math.PI / 180)) * 130}
              y2={200 + Math.sin((minuteAngle - 90) * (Math.PI / 180)) * 130}
              stroke="#333"
              strokeWidth="10"
              strokeLinecap="round"
              style={{
                filter: 'drop-shadow(2px 2px 4px rgba(0,0,0,0.5))'
              }}
            />

            {/* Second hand */}
            <line
              x1="200"
              y1="200"
              x2={200 + Math.cos((secondAngle - 90) * (Math.PI / 180)) * 140}
              y2={200 + Math.sin((secondAngle - 90) * (Math.PI / 180)) * 140}
              stroke="#c00000"
              strokeWidth="4"
              strokeLinecap="round"
            />

            {/* Center dot */}
            <circle cx="200" cy="200" r="12" fill="#222" />
            <circle cx="200" cy="200" r="8" fill="#c00000" />
          </svg>
        </div>
      </div>

      {/* Digital time display below clock */}
      <div className="mt-8 px-8 py-4 bg-black border-4 border-gray-500 rounded" style={{
        boxShadow: 'inset 2px 2px 4px rgba(0,0,0,0.5), 2px 2px 8px rgba(0,0,0,0.3)'
      }}>
        <div className="text-6xl font-mono text-green-400 tracking-wider" style={{
          textShadow: '0 0 10px rgba(0,255,0,0.8), 0 0 20px rgba(0,255,0,0.5)',
          fontFamily: 'Courier New, monospace'
        }}>
          {time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </div>
      </div>
    </div>
  );
}
