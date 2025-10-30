'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { 
  MapPin, 
  Car, 
  Route,
  Layers,
  ZoomIn,
  ZoomOut,
  Navigation,
  Settings
} from 'lucide-react';

interface KakaoMapPlaceholderProps {
  className?: string;
  showControls?: boolean;
  vehicles?: Array<{id: string; name: string; color: string}>;
}

export default function KakaoMapPlaceholder({ 
  className = "h-[420px]", 
  showControls = true,
  vehicles = [
    {id: "TRK01", name: "전기차 1톤", color: "bg-green-500"},
    {id: "TRK02", name: "하이브리드 1.5톤", color: "bg-blue-500"}, 
    {id: "TRK03", name: "디젤 2톤", color: "bg-red-500"}
  ]
}: KakaoMapPlaceholderProps) {
  const [activeVehicles, setActiveVehicles] = useState<string[]>(["TRK01", "TRK02"]);
  const [showRouteComparison, setShowRouteComparison] = useState(false);
  const [mapLayers, setMapLayers] = useState({
    traffic: true,
    satellite: false,
    terrain: false
  });

  const toggleVehicle = (vehicleId: string) => {
    setActiveVehicles(prev => 
      prev.includes(vehicleId) 
        ? prev.filter(id => id !== vehicleId)
        : [...prev, vehicleId]
    );
  };

  return (
    <div className={`relative bg-slate-100 rounded-lg border overflow-hidden ${className}`}>
      {/* Map Content Area */}
      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-200">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 mx-auto bg-slate-300 rounded-full flex items-center justify-center">
            <MapPin className="w-8 h-8 text-slate-500" />
          </div>
          <div className="space-y-2">
            <p className="text-slate-600 font-medium">카카오맵 영역</p>
            <p className="text-sm text-slate-500">실제 지도와 경로가 표시됩니다</p>
          </div>
          
          {/* Mock Route Lines */}
          <div className="absolute top-20 left-20 w-32 h-24">
            <svg className="w-full h-full" viewBox="0 0 128 96">
              <path 
                d="M 10 80 Q 40 20 80 40 T 118 10" 
                stroke="#22c55e" 
                strokeWidth="3" 
                fill="none"
                strokeDasharray="5,5"
                className="animate-pulse"
              />
              <path 
                d="M 10 80 Q 60 60 90 20 T 118 30" 
                stroke="#3b82f6" 
                strokeWidth="3" 
                fill="none"
                strokeDasharray="5,5"
                className="animate-pulse delay-300"
              />
            </svg>
          </div>
          
          {/* Mock Vehicle Icons */}
          <div className="absolute top-16 right-24">
            <Car className="w-6 h-6 text-green-600" />
          </div>
          <div className="absolute bottom-20 left-32">
            <Car className="w-6 h-6 text-blue-600" />
          </div>
        </div>
      </div>

      {showControls && (
        <>
          {/* Top Controls */}
          <div className="absolute top-4 left-4 right-4 flex flex-wrap gap-2 z-10">
            {/* Vehicle Toggles */}
            <div className="flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <Car className="w-4 h-4 text-slate-600" />
              {vehicles.map((vehicle) => (
                <Badge
                  key={vehicle.id}
                  variant={activeVehicles.includes(vehicle.id) ? "default" : "secondary"}
                  className={`cursor-pointer transition-all hover:scale-105 ${
                    activeVehicles.includes(vehicle.id) 
                      ? `${vehicle.color} text-white` 
                      : 'bg-slate-200'
                  }`}
                  onClick={() => toggleVehicle(vehicle.id)}
                >
                  {vehicle.name}
                </Badge>
              ))}
            </div>

            {/* Route Comparison */}
            <div className="flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <Route className="w-4 h-4 text-slate-600" />
              <Label htmlFor="route-comparison" className="text-sm">A/B 경로 비교</Label>
              <Switch 
                id="route-comparison"
                checked={showRouteComparison}
                onCheckedChange={setShowRouteComparison}
                size="sm"
              />
            </div>

            {/* Layer Controls */}
            <div className="flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <Layers className="w-4 h-4 text-slate-600" />
              <div className="flex gap-1">
                {Object.entries(mapLayers).map(([layer, active]) => (
                  <Badge
                    key={layer}
                    variant={active ? "default" : "secondary"}
                    className="cursor-pointer text-xs"
                    onClick={() => setMapLayers(prev => ({ ...prev, [layer]: !prev[layer as keyof typeof prev] }))}
                  >
                    {layer === 'traffic' ? '교통' : layer === 'satellite' ? '위성' : '지형'}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {/* Zoom Controls */}
          <div className="absolute bottom-4 right-4 flex flex-col gap-1 z-10">
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur">
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur">
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur">
              <Navigation className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur">
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </>
      )}
    </div>
  );
}