'use client';

import { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { 
  Car, 
  Route,
  Layers,
  ZoomIn,
  ZoomOut,
  Navigation,
  Settings
} from 'lucide-react';

declare global {
  interface Window {
    kakao: any;
  }
}

interface KakaoMapPlaceholderProps {
  className?: string;
  showControls?: boolean;
  vehicles?: Array<{id: string; name: string; color: string}>;
}

export default function KakaoMapPlaceholder({ 
  className = "h-[500px]",
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
    traffic: false, // 기본값을 false로 변경
    satellite: false,
    terrain: false
  });

  const mapContainer = useRef<HTMLDivElement>(null);
  const [map, setMap] = useState<any>(null);
  const KAKAO_APP_KEY = "4e34ef0e449c2ec445ee2ed78657054e";

  // 카카오맵 초기화
  useEffect(() => {
    if (!mapContainer.current) return;

    const script = document.createElement('script');
    script.src = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_APP_KEY}&autoload=false`;
    script.async = true;
    
    script.onload = () => {
      window.kakao.maps.load(() => {
        const mapOption = {
          center: new window.kakao.maps.LatLng(37.5665, 126.9780),
          level: 10
        };
        
        const newMap = new window.kakao.maps.Map(mapContainer.current, mapOption);
        setMap(newMap);
      });
    };

    document.head.appendChild(script);

    return () => {
      if (script.parentNode) {
        script.parentNode.removeChild(script);
      }
    };
  }, []);

  // 레이어 설정 변경 시 지도 업데이트 - 안전하게 처리
  useEffect(() => {
    if (map && window.kakao && window.kakao.maps) {
      try {
        // 교통정보 표시 (메서드가 존재하는지 확인)
        if (typeof map.setTraffic === 'function') {
          map.setTraffic(mapLayers.traffic);
        }
        
        // 위성지도 표시
        if (typeof map.setMapTypeId === 'function') {
          map.setMapTypeId(
            mapLayers.satellite 
              ? window.kakao.maps.MapTypeId.HYBRID 
              : window.kakao.maps.MapTypeId.ROADMAP
          );
        }
      } catch (error) {
        console.error('지도 레이어 설정 중 오류:', error);
      }
    }
  }, [map, mapLayers]);

  const toggleVehicle = (vehicleId: string) => {
    setActiveVehicles(prev => 
      prev.includes(vehicleId) 
        ? prev.filter(id => id !== vehicleId)
        : [...prev, vehicleId]
    );
  };

  // 줌 인/아웃 함수
  const zoomIn = () => {
    if (map && typeof map.setLevel === 'function') {
      map.setLevel(map.getLevel() - 1);
    }
  };

  const zoomOut = () => {
    if (map && typeof map.setLevel === 'function') {
      map.setLevel(map.getLevel() + 1);
    }
  };

  // 현재 위치로 이동
  const moveToCurrentLocation = () => {
    if (navigator.geolocation && map && window.kakao && window.kakao.maps) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const newPosition = new window.kakao.maps.LatLng(lat, lng);
          map.setCenter(newPosition);
          map.setLevel(6);
        },
        (error) => {
          console.error('현재 위치를 가져오는데 실패했습니다:', error);
        }
      );
    }
  };

  return (
    <div className={`relative rounded-lg border overflow-hidden ${className}`}>
      {/* 실제 지도 컨테이너 - 전체 영역을 차지하도록 */}
      <div 
        ref={mapContainer}
        className="w-full h-full absolute inset-0"
      />
      
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
                    onClick={() => {
                      // 교통정보는 기본적으로 꺼져있도록 설정
                      setMapLayers(prev => ({ 
                        ...prev, 
                        [layer]: !prev[layer as keyof typeof prev] 
                      }))
                    }}
                  >
                    {layer === 'traffic' ? '교통' : layer === 'satellite' ? '위성' : '지형'}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {/* Zoom Controls */}
          <div className="absolute bottom-4 right-4 flex flex-col gap-1 z-10">
            <Button 
              variant="secondary" 
              size="sm" 
              className="bg-white/90 backdrop-blur"
              onClick={zoomIn}
            >
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button 
              variant="secondary" 
              size="sm" 
              className="bg-white/90 backdrop-blur"
              onClick={zoomOut}
            >
              <ZoomOut className="w-4 h-4" />
            </Button>
            <Button 
              variant="secondary" 
              size="sm" 
              className="bg-white/90 backdrop-blur"
              onClick={moveToCurrentLocation}
            >
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