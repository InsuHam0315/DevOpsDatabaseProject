'use client';

import { useEffect, useRef, useState } from 'react';
import Script from 'next/script';

import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Car, Route as RouteIcon, Layers, ZoomIn, ZoomOut, Navigation, Settings } from 'lucide-react';

import type { VehicleRoute, PolylinePoint } from '@/lib/types';

declare global {
  interface Window {
    kakao: any;
  }
}

interface KakaoMapPlaceholderProps {
  className?: string;
  showControls?: boolean;
  routes?: VehicleRoute[];
}

type MapLayersState = {
  traffic: boolean;
  satellite: boolean;
  terrain: boolean;
};

const FALLBACK_BADGE_COLORS = ['bg-blue-500', 'bg-emerald-500', 'bg-orange-500', 'bg-rose-500', 'bg-slate-500'];
const ROUTE_STROKE_COLORS = ['#2563eb', '#059669', '#f97316', '#dc2626', '#7c3aed'];
const DEFAULT_CENTER = { lat: 37.5665, lng: 126.978 };
const START_MARKER_IMAGE_SRC = 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/marker_red.png';
const END_MARKER_IMAGE_SRC = 'https://t1.daumcdn.net/localimg/localimages/07/mapapidoc/markerStar.png';

const normalizePolyline = (polyline?: PolylinePoint[] | Array<[number, number]> | null): PolylinePoint[] => {
  if (!polyline) return [];
  return polyline
    .map((point: any) => {
      if (Array.isArray(point) && point.length >= 2) {
        const [lng, lat] = point;
        if (typeof lat === 'number' && typeof lng === 'number') {
          return { lat, lng };
        }
        return null;
      }
      const lat = point?.lat ?? point?.latitude;
      const lng = point?.lng ?? point?.lon ?? point?.longitude;
      if (typeof lat === 'number' && typeof lng === 'number') {
        return { lat, lng };
      }
      return null;
    })
    .filter(Boolean) as PolylinePoint[];
};

const resolveRoutePolyline = (route: VehicleRoute): PolylinePoint[] => {
  const candidateSources = [
    route?.polyline,
    (route as any)?.path,
    (route as any)?.points,
    (route as any)?.coordinates
  ];
  for (const source of candidateSources) {
    const normalized = normalizePolyline(source);
    if (normalized.length >= 2) {
      // 현재는 네비게이션 수준의 정교한 경로 대신
      // 출발지-도착지를 직선으로 잇는 단순 표현만 사용한다.
      return [normalized[0], normalized[normalized.length - 1]];
    }
    if (normalized.length === 1) return normalized;
  }
  const fallbackStart = (route as any)?.start;
  const fallbackEnd = (route as any)?.end;
  if (fallbackStart && fallbackEnd) {
    const normalized = normalizePolyline([fallbackStart, fallbackEnd]);
    if (normalized.length) return normalized;
  }
  return [];
};

const getInitialCenter = (routeList: VehicleRoute[]): { lat: number; lng: number } => {
  for (const route of routeList) {
    const normalized = resolveRoutePolyline(route);
    if (normalized.length > 0) {
      return normalized[0];
    }
  }
  return DEFAULT_CENTER;
};

export default function KakaoMapPlaceholder({
  className = 'h-[500px]',
  showControls = true,
  routes = []
}: KakaoMapPlaceholderProps) {
  const [activeVehicles, setActiveVehicles] = useState<string[]>(() =>
    routes.map((route) => route.vehicleId)
  );
  const [showRouteComparison, setShowRouteComparison] = useState(false);
  const [mapLayers, setMapLayers] = useState<MapLayersState>({
    traffic: false,
    satellite: false,
    terrain: false
  });
  const [map, setMap] = useState<any>(null);
  const [isSdkReady, setIsSdkReady] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const mapContainer = useRef<HTMLDivElement>(null);
  const overlaysRef = useRef<{ polylines: any[]; markers: any[] }>({
    polylines: [],
    markers: []
  });

  const kakaoAppKey =
    process.env.NEXT_PUBLIC_KAKAO_MAP_API_KEY ||
    process.env.NEXT_PUBLIC_KAKAO_MAP_APP_KEY;
  const sdkUrl = kakaoAppKey
    ? `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${kakaoAppKey}&autoload=false&libraries=services`
    : null;

  const clearMapDrawings = () => {
    overlaysRef.current.polylines.forEach((polyline) => polyline.setMap(null));
    overlaysRef.current.markers.forEach((marker) => marker.setMap(null));
    overlaysRef.current = { polylines: [], markers: [] };
  };

  const handleSdkLoad = () => {
    if (!window.kakao?.maps) {
      setLoadError('카카오 지도 SDK를 불러오지 못했습니다.');
      return;
    }
    window.kakao.maps.load(() => {
      setLoadError(null);
      setIsSdkReady(true);
    });
  };

  useEffect(() => {
    if (!routes.length) {
      setActiveVehicles([]);
      return;
    }
    setActiveVehicles(routes.map((route) => route.vehicleId));
  }, [routes]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (window.kakao?.maps) {
      setIsSdkReady(true);
    }
  }, []);

  useEffect(() => {
    return () => {
      clearMapDrawings();
    };
  }, []);

  useEffect(() => {
    if (!isSdkReady || map || !mapContainer.current || !window.kakao?.maps) {
      return;
    }
    const center = getInitialCenter(routes);
    const mapInstance = new window.kakao.maps.Map(mapContainer.current, {
      center: new window.kakao.maps.LatLng(center.lat, center.lng),
      level: 6
    });
    setMap(mapInstance);
  }, [isSdkReady, map, routes]);

  useEffect(() => {
    if (!map || !window.kakao?.maps) return;

    map.setMapTypeId(
      mapLayers.satellite ? window.kakao.maps.MapTypeId.HYBRID : window.kakao.maps.MapTypeId.ROADMAP
    );

    const overlayConfigs = [
      { active: mapLayers.traffic, id: window.kakao.maps.MapTypeId.TRAFFIC },
      { active: mapLayers.terrain, id: window.kakao.maps.MapTypeId.TERRAIN }
    ];

    overlayConfigs.forEach(({ active, id }) => {
      if (active) {
        map.addOverlayMapTypeId(id);
      } else {
        map.removeOverlayMapTypeId(id);
      }
    });
  }, [map, mapLayers]);

  useEffect(() => {
    if (!map || !window.kakao?.maps) return;

    clearMapDrawings();
    const targetRoutes = routes.filter(
      (route) => !activeVehicles.length || activeVehicles.includes(route.vehicleId)
    );
    if (!targetRoutes.length) return;

    const { LatLng, LatLngBounds, Point, Size, MarkerImage, Marker, Polyline } = window.kakao.maps;
    const bounds = new LatLngBounds();
    let hasBounds = false;

    const createMarker = (position: any, label: string, type: 'start' | 'end') => {
      const imageSrc = type === 'start' ? START_MARKER_IMAGE_SRC : END_MARKER_IMAGE_SRC;
      const size = new Size(34, 39);
      const offset = new Point(12, 39);
      const markerImage = new MarkerImage(imageSrc, size, { offset });
      return new Marker({
        position,
        title: label,
        image: markerImage,
        zIndex: type === 'start' ? 3 : 2
      });
    };

    targetRoutes.forEach((route, index) => {
      const normalized = resolveRoutePolyline(route);
      if (!normalized.length) return;

      const pathLatLng = normalized.map(({ lat, lng }) => new LatLng(lat, lng));
      pathLatLng.forEach((point) => {
        bounds.extend(point);
        hasBounds = true;
      });

      if (pathLatLng.length >= 2) {
        const polyline = new Polyline({
          map,
          path: pathLatLng,
          strokeWeight: 4,
          strokeColor: ROUTE_STROKE_COLORS[index % ROUTE_STROKE_COLORS.length],
          strokeOpacity: 0.85,
          strokeStyle: 'solid'
        });
        overlaysRef.current.polylines.push(polyline);
      }

      const startMarker = createMarker(
        pathLatLng[0],
        `${route.vehicleName || route.vehicleId} 출발`,
        'start'
      );
      const endMarker = createMarker(
        pathLatLng[pathLatLng.length - 1] ?? pathLatLng[0],
        `${route.vehicleName || route.vehicleId} 도착`,
        'end'
      );

      startMarker.setMap(map);
      endMarker.setMap(map);
      overlaysRef.current.markers.push(startMarker, endMarker);
    });

    if (hasBounds) {
      map.setBounds(bounds, 32, 32, 32, 32);
    }
  }, [map, routes, activeVehicles]);

  const toggleVehicle = (vehicleId: string) => {
    setActiveVehicles((prev) =>
      prev.includes(vehicleId)
        ? prev.filter((id) => id !== vehicleId)
        : [...prev, vehicleId]
    );
  };

  const toggleLayer = (layer: keyof MapLayersState) => {
    setMapLayers((prev) => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

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

  const moveToCurrentLocation = () => {
    if (navigator.geolocation && map && window.kakao?.maps) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const lat = position.coords.latitude;
          const lng = position.coords.longitude;
          const newPosition = new window.kakao.maps.LatLng(lat, lng);
          map.setCenter(newPosition);
          map.setLevel(6);
        },
        (error) => {
          console.error('현재 위치를 가져오지 못했습니다:', error);
        }
      );
    }
  };

  const vehicleMeta = routes.map((route, index) => ({
    id: route.vehicleId,
    name: route.vehicleName || route.vehicleId,
    color: FALLBACK_BADGE_COLORS[index % FALLBACK_BADGE_COLORS.length]
  }));

  return (
    <div className={`relative rounded-lg border overflow-hidden ${className}`}>
      {sdkUrl && (
        <Script
          src={sdkUrl}
          strategy="afterInteractive"
          onLoad={handleSdkLoad}
          onError={() => setLoadError('카카오 지도 SDK를 불러오지 못했습니다.')}
        />
      )}
      <div ref={mapContainer} className="w-full h-full absolute inset-0" />

      {!sdkUrl && (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-100 text-sm text-slate-600">
          Kakao Maps API 키를 설정해주세요.
        </div>
      )}

      {loadError && (
        <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur px-4 py-2 rounded-lg shadow text-sm text-red-600 z-10">
          {loadError}
        </div>
      )}

      {showControls && (
        <>
          <div className="absolute top-4 left-4 right-4 flex flex-wrap gap-2 z-10">
            <div className="flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <Car className="w-4 h-4 text-slate-600" />
              {vehicleMeta.length === 0 && (
                <span className="text-xs text-muted-foreground">표시할 차량이 없습니다</span>
              )}
              {vehicleMeta.map((vehicle) => (
                <Badge
                  key={vehicle.id}
                  variant={activeVehicles.includes(vehicle.id) ? 'default' : 'secondary'}
                  className={`cursor-pointer transition-all hover:scale-105 ${
                    activeVehicles.includes(vehicle.id) ? `${vehicle.color} text-white` : 'bg-slate-200'
                  }`}
                  onClick={() => toggleVehicle(vehicle.id)}
                >
                  {vehicle.name}
                </Badge>
              ))}
            </div>

            <div className="flex items-center gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <RouteIcon className="w-4 h-4 text-slate-600" />
              <Label htmlFor="route-comparison" className="text-sm">
                A/B 경로 비교
              </Label>
              <Switch
                id="route-comparison"
                checked={showRouteComparison}
                onCheckedChange={setShowRouteComparison}
                size="sm"
              />
            </div>

            <div className="flex itemsender gap-2 bg-white/90 backdrop-blur rounded-lg p-2 shadow-md">
              <Layers className="w-4 h-4 text-slate-600" />
              <div className="flex gap-1">
                {Object.entries(mapLayers).map(([layer, active]) => (
                  <Badge
                    key={layer}
                    variant={active ? 'default' : 'secondary'}
                    className="cursor-pointer text-xs"
                    onClick={() => toggleLayer(layer as keyof MapLayersState)}
                  >
                    {layer === 'traffic' ? '교통' : layer === 'satellite' ? '위성' : '지형'}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          <div className="absolute bottom-4 right-4 flex flex-col gap-1 z-10">
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur" onClick={zoomIn}>
              <ZoomIn className="w-4 h-4" />
            </Button>
            <Button variant="secondary" size="sm" className="bg-white/90 backdrop-blur" onClick={zoomOut}>
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
