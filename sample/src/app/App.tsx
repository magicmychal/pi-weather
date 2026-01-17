import { RetroAnalogClock } from '@/app/components/RetroAnalogClock';
import { RetroWeatherPanel } from '@/app/components/RetroWeatherPanel';

export default function App() {
  return (
    <div className="size-full bg-gray-600 overflow-hidden" style={{
      background: 'linear-gradient(135deg, #4a5568 0%, #2d3748 100%)',
      position: 'relative'
    }}>
      {/* CRT Scanline Effect */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.15) 0px, rgba(0,0,0,0.15) 1px, transparent 1px, transparent 2px)',
        zIndex: 10
      }}></div>
      
      {/* Main Content */}
      <div className="h-full grid grid-cols-2 gap-0 relative z-0">
        {/* Left Side - Analog Clock */}
        <div className="border-r-4 border-gray-700">
          <RetroAnalogClock />
        </div>
        
        {/* Right Side - Weather Info */}
        <div>
          <RetroWeatherPanel />
        </div>
      </div>
      
      {/* Vignette Effect */}
      <div className="absolute inset-0 pointer-events-none" style={{
        background: 'radial-gradient(circle at center, transparent 50%, rgba(0,0,0,0.3) 100%)',
        zIndex: 5
      }}></div>
    </div>
  );
}