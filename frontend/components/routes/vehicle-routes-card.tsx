'use client';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger
} from '@/components/ui/accordion';
import { Car, Clock, Fuel, Route as RouteIcon } from 'lucide-react';

import type { VehicleRoute } from '@/lib/types';

interface VehicleRoutesCardProps {
  routes?: VehicleRoute[]; // ✅ optional
}

const formatDistance = (value: number | undefined | null): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0 km';
  return `${value.toFixed(1)} km`;
};

const formatCo2Kg = (value: number | undefined | null): string => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0 kg CO₂';
  return `${value.toFixed(2)} kg CO₂`;
};

export default function VehicleRoutesCard({
  routes = [] // ✅ 기본값 []
}: VehicleRoutesCardProps) {
  const vehicleCount = routes.length;
  const headerLabel =
    vehicleCount > 0
      ? `차량별 경로 (Kakao, ORS)`
      : '차량별 경로 (경로 없음)';

  const routesWithSteps = routes.filter(
    (route) => Array.isArray(route.steps) && route.steps.length > 0
  );

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Car className="w-5 h-5" />
          {headerLabel}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {routes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            차량별 경로 데이터가 없습니다. 최적화를 수행한 후 확인해주세요.
          </p>
        ) : (
          <div className="space-y-3">
            {routes.map((route) => (
              <div
                key={route.vehicleId}
                className="flex items-center justify-between rounded-md border bg-muted/40 px-4 py-3"
              >
                <div>
                  <p className="text-sm font-semibold">
                    {route.vehicleName || route.vehicleId}
                  </p>
                  <p className="text-xs text-muted-foreground">{route.vehicleId}</p>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span>{formatDistance(route.distanceKm)}</span>
                  <span>{formatCo2Kg(route.emissionKg)}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {routesWithSteps.length > 0 && (
          <Accordion type="single" collapsible className="space-y-2">
            {routesWithSteps.map((route) => (
              <AccordionItem
                key={`${route.vehicleId}-detail`}
                value={route.vehicleId}
              >
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center justify-between w-full mr-4">
                    <div className="flex items-center gap-3">
                      <Badge variant="secondary">{route.vehicleId}</Badge>
                      <span className="text-sm text-muted-foreground">
                        {route.vehicleName || '차량 정보 없음'}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>{formatDistance(route.distanceKm)}</span>
                      <span>{formatCo2Kg(route.emissionKg)}</span>
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3 pl-4">
                    {(route.steps ?? []).map((step, index) => (
                      <div
                        key={`${route.vehicleId}-${index}`}
                        className="flex items-center gap-4 p-3 bg-muted rounded-lg"
                      >
                        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-sm font-medium">
                          {step.order ?? index + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium">
                            {step.name ||
                              step.address ||
                              step.sectorId ||
                              `경유지 ${index + 1}`}
                          </p>
                          <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
                            {(step.arrivalTime || step.departureTime) && (
                              <span className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {step.arrivalTime ?? '-'} ~{' '}
                                {step.departureTime ?? '-'}
                              </span>
                            )}
                            {typeof step.distanceKm === 'number' && (
                              <span className="flex items-center gap-1">
                                <RouteIcon className="w-3 h-3" />
                                {step.distanceKm} km
                              </span>
                            )}
                            {typeof step.emissionKg === 'number' && (
                              <span className="flex items-center gap-1">
                                <Fuel className="w-3 h-3" />
                                {step.emissionKg} kg
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </CardContent>
    </Card>
  );
}

