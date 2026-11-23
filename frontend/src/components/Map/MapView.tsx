import React, { useEffect, useRef } from "react";
import L from "leaflet";
import {
  DeliveryStop,
  Depot,
  RoadEdgeViewport,
  RouteResponse,
  VRPTWSolutionResult,
} from "../../types";

interface MapViewProps {
  center: [number, number];
  zoom: number;
  viewportEdges: RoadEdgeViewport[];
  depot?: Depot;
  stops: DeliveryStop[];
  activeRoute?: RouteResponse | null;
  vrpSolution?: VRPTWSolutionResult | null;
  selectedStopId?: string | null;
  onMapClick?: (coords: { lat: number; lon: number }) => void;
  onStopSelect?: (stopId: string) => void;
  appMode: "routing" | "fleet";
  routeStart?: { lat: number; lon: number } | null;
  routeEnd?: { lat: number; lon: number } | null;
}

const VEHICLE_COLORS = [
  "#06b6d4", // cyan-500
  "#f59e0b", // amber-500
  "#a855f7", // purple-500
  "#10b981", // emerald-500
  "#ec4899", // pink-500
  "#3b82f6", // blue-500
];

export const MapView: React.FC<MapViewProps> = ({
  center,
  zoom,
  viewportEdges,
  depot,
  stops,
  activeRoute,
  vrpSolution,
  selectedStopId,
  onMapClick,
  onStopSelect,
  appMode,
  routeStart,
  routeEnd,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const edgesLayerRef = useRef<L.LayerGroup | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const routesLayerRef = useRef<L.LayerGroup | null>(null);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: center,
      zoom: zoom,
      zoomControl: false,
    });

    // Dark Matter basemap tiles (CartoDB)
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19,
      }
    ).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    edgesLayerRef.current = L.layerGroup().addTo(map);
    routesLayerRef.current = L.layerGroup().addTo(map);
    markersLayerRef.current = L.layerGroup().addTo(map);

    map.on("click", (e: L.LeafletMouseEvent) => {
      if (onMapClick) {
        onMapClick({
          lat: Number(e.latlng.lat.toFixed(6)),
          lon: Number(e.latlng.lng.toFixed(6)),
        });
      }
    });

    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update map view when center/zoom changes
  useEffect(() => {
    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView(center, zoom, { animate: true });
    }
  }, [center[0], center[1], zoom]);

  // Render Viewport Road Edges with Congestion Colors
  useEffect(() => {
    if (!edgesLayerRef.current) return;
    edgesLayerRef.current.clearLayers();

    viewportEdges.forEach((edge) => {
      let color = "#3b82f6"; // default blue
      let opacity = 0.45;
      let weight = 2.5;

      if (edge.road_type === "motorway" || edge.road_type === "trunk") {
        weight = 4;
      }

      // Congestion coloring
      if (edge.congestion_ratio > 1.5) {
        color = "#ef4444"; // heavy red
        opacity = 0.85;
      } else if (edge.congestion_ratio > 1.2) {
        color = "#f59e0b"; // moderate amber
        opacity = 0.7;
      } else {
        color = "#10b981"; // free-flow emerald
        opacity = 0.4;
      }

      const polyline = L.polyline(edge.coords, {
        color,
        weight,
        opacity,
      });

      polyline.bindTooltip(
        `<div class="p-1 text-xs">
          <div class="font-bold text-slate-100">${edge.source} &rarr; ${edge.target}</div>
          <div class="text-slate-300">Type: <span class="text-emerald-400 font-mono">${edge.road_type}</span></div>
          <div class="text-slate-300">Speed: <span class="font-mono text-cyan-300">${edge.speed_kmh} km/h</span></div>
          <div class="text-slate-300">Traffic Delay: <span class="font-mono font-bold ${
            edge.congestion_ratio > 1.4 ? "text-rose-400" : "text-emerald-400"
          }">${edge.congestion_ratio}x</span></div>
        </div>`,
        { sticky: true }
      );

      polyline.addTo(edgesLayerRef.current!);
    });
  }, [viewportEdges]);

  // Render Routes (Point-to-Point or Multi-Vehicle VRPTW)
  useEffect(() => {
    if (!routesLayerRef.current) return;
    routesLayerRef.current.clearLayers();

    // 1. Point-to-Point Route
    if (appMode === "routing" && activeRoute && activeRoute.found) {
      // Glow background line
      L.polyline(activeRoute.path_coords, {
        color: "#38bdf8",
        weight: 8,
        opacity: 0.35,
      }).addTo(routesLayerRef.current);

      // Core route line
      const mainLine = L.polyline(activeRoute.path_coords, {
        color: "#0284c7",
        weight: 4,
        opacity: 0.95,
      }).addTo(routesLayerRef.current);

      mainLine.bindPopup(
        `<div class="p-2 text-xs">
          <div class="font-bold text-sky-400 text-sm uppercase">${activeRoute.algorithm} Optimal Route</div>
          <div class="mt-1 text-slate-200">Distance: <b>${(activeRoute.distance_m / 1000).toFixed(2)} km</b></div>
          <div class="text-slate-200">Duration: <b>${(activeRoute.duration_s / 60).toFixed(1)} mins</b></div>
          <div class="text-slate-200">Settled Nodes: <b>${activeRoute.nodes_settled}</b></div>
          <div class="text-slate-200">Latency: <b>${activeRoute.execution_time_ms.toFixed(2)} ms</b></div>
        </div>`
      );
    }

    // 2. VRPTW Multi-Vehicle Routes
    if (appMode === "fleet" && vrpSolution && vrpSolution.evaluation) {
      vrpSolution.evaluation.vehicle_schedules.forEach((veh, idx) => {
        const color = VEHICLE_COLORS[idx % VEHICLE_COLORS.length];
        const coords: [number, number][] = [];

        veh.timeline.forEach((item) => {
          coords.push([item.lat, item.lon]);
        });

        if (coords.length > 1) {
          // Glow
          L.polyline(coords, {
            color,
            weight: 7,
            opacity: 0.3,
          }).addTo(routesLayerRef.current!);

          // Line
          const poly = L.polyline(coords, {
            color,
            weight: 3.5,
            dashArray: idx % 2 === 1 ? "6, 6" : undefined,
            opacity: 0.9,
          }).addTo(routesLayerRef.current!);

          poly.bindPopup(
            `<div class="p-2 text-xs">
              <div class="font-bold text-sm" style="color: ${color}">Vehicle #${veh.vehicle_id}</div>
              <div class="text-slate-200 mt-1">Stops: <b>${veh.stop_count}</b></div>
              <div class="text-slate-200">Distance: <b>${(veh.total_distance_m / 1000).toFixed(2)} km</b></div>
              <div class="text-slate-200">Duration: <b>${(veh.total_duration_s / 60).toFixed(1)} mins</b></div>
              <div class="text-slate-200">Load: <b>${veh.total_demand}/${veh.capacity} (${veh.capacity_utilization_pct}%)</b></div>
              ${veh.lateness_s > 0 ? `<div class="text-rose-400 font-bold mt-1">Late: ${(veh.lateness_s / 60).toFixed(1)}m</div>` : `<div class="text-emerald-400 font-semibold mt-1">All Stops On-Time</div>`}
            </div>`
          );
        }
      });
    }
  }, [appMode, activeRoute, vrpSolution]);

  // Render Markers (Depot, Stops, Route Start/End)
  useEffect(() => {
    if (!markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    // Point-to-Point Start Marker
    if (appMode === "routing" && routeStart) {
      const startIcon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="w-8 h-8 rounded-full bg-emerald-500 border-2 border-white shadow-lg flex items-center justify-center font-bold text-white text-xs">A</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
      L.marker([routeStart.lat, routeStart.lon], { icon: startIcon })
        .bindTooltip("Start Location", { permanent: false })
        .addTo(markersLayerRef.current);
    }

    // Point-to-Point End Marker
    if (appMode === "routing" && routeEnd) {
      const endIcon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="w-8 h-8 rounded-full bg-rose-500 border-2 border-white shadow-lg flex items-center justify-center font-bold text-white text-xs">B</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });
      L.marker([routeEnd.lat, routeEnd.lon], { icon: endIcon })
        .bindTooltip("Destination", { permanent: false })
        .addTo(markersLayerRef.current);
    }

    // Fleet Depot Marker
    if (depot) {
      const depotIcon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="flex items-center justify-center">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-600 to-amber-400 border-2 border-amber-200 shadow-xl flex items-center justify-center text-slate-950 font-black text-sm">
            HUB
          </div>
        </div>`,
        iconSize: [40, 40],
        iconAnchor: [20, 20],
      });

      const m = L.marker([depot.lat, depot.lon], { icon: depotIcon });
      m.bindPopup(
        `<div class="p-2 text-xs">
          <div class="font-bold text-amber-400 text-sm">${depot.name}</div>
          <div class="text-slate-300">Central Logistics Depot</div>
          <div class="text-slate-300 mt-1">Fleet Departure: <b>${depot.start_time}</b></div>
          <div class="text-slate-400 text-[10px] mt-1 font-mono">${depot.lat.toFixed(4)}, ${depot.lon.toFixed(4)}</div>
        </div>`
      );
      m.addTo(markersLayerRef.current);
    }

    // Fleet Delivery Stops
    stops.forEach((stop, index) => {
      const isSelected = selectedStopId === stop.id;
      
      // Determine if stop is served late in current solution
      let isLate = false;
      let assignedVehicle = null;

      if (vrpSolution && vrpSolution.evaluation) {
        for (const veh of vrpSolution.evaluation.vehicle_schedules) {
          const found = veh.timeline.find((t) => t.stop_id === stop.id);
          if (found) {
            isLate = found.is_late;
            assignedVehicle = veh.vehicle_id;
            break;
          }
        }
      }

      const badgeColor = isSelected
        ? "border-cyan-400 ring-4 ring-cyan-500/50"
        : isLate
        ? "border-rose-400 bg-rose-600"
        : assignedVehicle
        ? "border-emerald-400 bg-slate-800"
        : "border-slate-500 bg-slate-800";

      const stopIcon = L.divIcon({
        className: "custom-div-icon",
        html: `<div class="group relative flex items-center justify-center cursor-pointer">
          <div class="w-7 h-7 rounded-full ${badgeColor} border-2 shadow-lg flex items-center justify-center text-xs font-bold text-white transition-transform group-hover:scale-125">
            ${index + 1}
          </div>
          <span class="absolute -top-6 bg-slate-900 border border-slate-700 text-[10px] text-slate-200 px-1.5 py-0.5 rounded shadow pointer-events-none whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            ${stop.name} (${stop.demand}kg)
          </span>
        </div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon });

      marker.on("click", () => {
        if (onStopSelect) onStopSelect(stop.id);
      });

      marker.bindPopup(
        `<div class="p-2 text-xs">
          <div class="font-bold text-slate-100 text-sm">Stop #${index + 1}: ${stop.name}</div>
          <div class="mt-1 text-slate-300">Demand: <b class="text-amber-400">${stop.demand} kg</b></div>
          <div class="text-slate-300">Window: <b class="text-cyan-400">${stop.earliest_time} - ${stop.latest_time}</b></div>
          <div class="text-slate-300">Service: <b>${(stop.service_time_s / 60).toFixed(0)} mins</b></div>
          ${assignedVehicle ? `<div class="mt-1 text-emerald-400 font-semibold">Assigned to Vehicle #${assignedVehicle}</div>` : ""}
          ${isLate ? `<div class="text-rose-400 font-bold mt-1">Delivery Window Violated!</div>` : ""}
        </div>`
      );

      marker.addTo(markersLayerRef.current!);
    });
  }, [
    appMode,
    routeStart,
    routeEnd,
    depot,
    stops,
    selectedStopId,
    vrpSolution,
    onStopSelect,
  ]);

  return (
    <div className="relative w-full h-full">
      <div ref={mapContainerRef} className="w-full h-full z-0" />

      {/* Map Legend Overlay */}
      <div className="absolute bottom-6 left-6 z-10 bg-slate-900/90 backdrop-blur-md border border-slate-800 p-3 rounded-xl shadow-2xl text-xs space-y-2 pointer-events-auto max-w-xs">
        <div className="font-semibold text-slate-200 flex items-center justify-between">
          <span>Traffic & Road Legend</span>
          <span className="text-[10px] text-slate-400">Live Congestion</span>
        </div>
        <div className="grid grid-cols-3 gap-2 text-[11px] text-slate-300">
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
            <span>Free-Flow</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
            <span>Moderate</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span>Gridlock</span>
          </div>
        </div>
        <div className="pt-1 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
          <span>Click map to {appMode === "routing" ? "place endpoints" : "add delivery stop"}</span>
        </div>
      </div>
    </div>
  );
};
