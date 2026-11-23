import React, { useEffect, useState } from "react";
import { Header } from "./components/Controls/Header";
import { RoutingControls } from "./components/Controls/RoutingControls";
import { FleetControls } from "./components/Controls/FleetControls";
import { MapView } from "./components/Map/MapView";
import { DispatchInspector } from "./components/Dispatch/DispatchInspector";
import { BenchmarkModal } from "./components/Analytics/BenchmarkModal";
import {
  computeRoute,
  fetchGraphViewport,
  fetchScenarios,
  selectScenario,
  solveVRPTW,
} from "./services/api";
import {
  CostMetric,
  DeliveryStop,
  Depot,
  RoadEdgeViewport,
  RouteResponse,
  RoutingAlgorithm,
  ScenarioInfo,
  TransportMode,
  VRPAlgorithm,
  VRPTWSolutionResult,
} from "./types";

export const App: React.FC = () => {
  // Scenario State
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [activeScenarioId, setActiveScenarioId] = useState<string>("san_francisco");
  const [center, setCenter] = useState<[number, number]>([37.7850, -122.4020]);
  const [zoom, setZoom] = useState<number>(14);
  const [bounds, setBounds] = useState<{ min_lat: number; min_lon: number; max_lat: number; max_lon: number }>({
    min_lat: 37.768,
    min_lon: -122.415,
    max_lat: 37.805,
    max_lon: -122.38,
  });

  // App & Transportation Modes
  const [appMode, setAppMode] = useState<"routing" | "fleet">("fleet");
  const [transportMode, setTransportMode] = useState<TransportMode>("driving");
  const [departureTime, setDepartureTime] = useState<string>("08:30");
  const [costMetric, setCostMetric] = useState<CostMetric>("time");

  // Road Network Viewport
  const [viewportEdges, setViewportEdges] = useState<RoadEdgeViewport[]>([]);

  // Depot & Stops State
  const [depot, setDepot] = useState<Depot>({
    id: "sf_depot_soma",
    name: "SoMa Dispatch Hub",
    lat: 37.7795,
    lon: -122.4025,
    start_time: "08:00",
  });
  const [stops, setStops] = useState<DeliveryStop[]>([]);
  const [selectedStopId, setSelectedStopId] = useState<string | null>(null);

  // Routing Lab State
  const [routingAlgorithm, setRoutingAlgorithm] = useState<RoutingAlgorithm>("astar");
  const [startCoords, setStartCoords] = useState<{ lat: number; lon: number } | null>({
    lat: 37.7795,
    lon: -122.4025,
  });
  const [endCoords, setEndCoords] = useState<{ lat: number; lon: number } | null>({
    lat: 37.7952,
    lon: -122.4028,
  });
  const [activeRoute, setActiveRoute] = useState<RouteResponse | null>(null);
  const [isRoutingLoading, setIsRoutingLoading] = useState<boolean>(false);

  // Fleet VRPTW State
  const [fleetSize, setFleetSize] = useState<number>(3);
  const [vehicleCapacity, setVehicleCapacity] = useState<number>(85.0);
  const [vrpAlgorithm, setVrpAlgorithm] = useState<VRPAlgorithm>("genetic");
  const [vrpSolution, setVrpSolution] = useState<VRPTWSolutionResult | null>(null);
  const [isVrpLoading, setIsVrpLoading] = useState<boolean>(false);

  // Modal State
  const [isBenchmarkOpen, setIsBenchmarkOpen] = useState<boolean>(false);

  // Load scenarios on mount
  useEffect(() => {
    fetchScenarios()
      .then((data) => {
        setScenarios(data.scenarios);
        if (data.scenarios.length > 0) {
          handleScenarioSelect(data.active_scenario || data.scenarios[0].id);
        }
      })
      .catch((err) => console.error("Error loading scenarios:", err));
  }, []);

  // Update viewport road edges when scenario, departure time, or mode changes
  useEffect(() => {
    if (!bounds) return;
    fetchGraphViewport(bounds, departureTime, transportMode)
      .then((vp) => setViewportEdges(vp.edges))
      .catch((err) => console.error("Error fetching road viewport:", err));
  }, [bounds, departureTime, transportMode]);

  const handleScenarioSelect = async (scenarioId: string) => {
    try {
      const res = await selectScenario(scenarioId);
      setActiveScenarioId(res.scenario_id);
      setDepot(res.depot);
      setStops(res.stops);
      setBounds(res.bounds);
      setCenter([
        (res.bounds.min_lat + res.bounds.max_lat) / 2,
        (res.bounds.min_lon + res.bounds.max_lon) / 2,
      ]);
      setZoom(res.metadata?.default_zoom || 14);
      if (res.metadata?.default_mode) {
        setTransportMode(res.metadata.default_mode);
      }
      // Reset active routes/solutions
      setActiveRoute(null);
      setVrpSolution(null);
      setSelectedStopId(null);

      // Default start/end points
      if (res.stops.length >= 2) {
        setStartCoords({ lat: res.depot.lat, lon: res.depot.lon });
        setEndCoords({ lat: res.stops[0].lat, lon: res.stops[0].lon });
      }
    } catch (err) {
      console.error("Failed to select scenario:", err);
    }
  };

  const handleCalculateRoute = async () => {
    if (!startCoords || !endCoords) return;
    setIsRoutingLoading(true);
    try {
      const res = await computeRoute(
        startCoords,
        endCoords,
        routingAlgorithm,
        transportMode,
        departureTime,
        costMetric
      );
      setActiveRoute(res);
    } catch (err) {
      console.error("Routing error:", err);
      alert("Failed to compute path. Ensure coordinates are within road bounds.");
    } finally {
      setIsRoutingLoading(false);
    }
  };

  const handleSolveVRPTW = async () => {
    if (stops.length === 0) return;
    setIsVrpLoading(true);
    try {
      const res = await solveVRPTW(
        vrpAlgorithm as "genetic" | "simulated_annealing",
        fleetSize,
        vehicleCapacity,
        depot,
        stops,
        80,
        40
      );
      if (res.solution) {
        setVrpSolution(res.solution);
      }
    } catch (err) {
      console.error("VRPTW Solve error:", err);
      alert("VRPTW optimization failed.");
    } finally {
      setIsVrpLoading(false);
    }
  };

  const handleMapClick = (coords: { lat: number; lon: number }) => {
    if (appMode === "routing") {
      // Toggle between setting start and end
      if (!startCoords || (startCoords && endCoords)) {
        setStartCoords(coords);
        setEndCoords(null);
        setActiveRoute(null);
      } else {
        setEndCoords(coords);
      }
    } else {
      // Add stop at clicked location
      const newStop: DeliveryStop = {
        id: `stop_clicked_${Date.now()}`,
        name: `Stop #${stops.length + 1} (${coords.lat.toFixed(3)}, ${coords.lon.toFixed(3)})`,
        lat: coords.lat,
        lon: coords.lon,
        demand: 15.0,
        service_time_s: 300,
        earliest_time: "08:30",
        latest_time: "10:30",
      };
      setStops((prev) => [...prev, newStop]);
    }
  };

  const handleAddStop = (stop: DeliveryStop) => {
    setStops((prev) => [...prev, stop]);
  };

  const handleRemoveStop = (id: string) => {
    setStops((prev) => prev.filter((s) => s.id !== id));
  };

  const handleResetStops = () => {
    handleScenarioSelect(activeScenarioId);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-slate-950 font-sans">
      {/* Header Bar */}
      <Header
        scenarios={scenarios}
        activeScenarioId={activeScenarioId}
        onSelectScenario={handleScenarioSelect}
        appMode={appMode}
        onSetAppMode={setAppMode}
        transportMode={transportMode}
        onSetTransportMode={setTransportMode}
        departureTime={departureTime}
        onSetDepartureTime={setDepartureTime}
        onOpenBenchmark={() => setIsBenchmarkOpen(true)}
      />

      {/* Main App Workspace */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Control Sidebar */}
        <div className="w-[380px] bg-slate-950 border-r border-slate-800 p-4 shrink-0 flex flex-col z-10 shadow-2xl overflow-hidden">
          {appMode === "routing" ? (
            <RoutingControls
              algorithm={routingAlgorithm}
              onSetAlgorithm={setRoutingAlgorithm}
              costMetric={costMetric}
              onSetCostMetric={setCostMetric}
              startCoords={startCoords}
              endCoords={endCoords}
              onCalculateRoute={handleCalculateRoute}
              isLoading={isRoutingLoading}
              activeRoute={activeRoute}
              onSetDefaultStartEnd={() => {
                if (stops.length >= 2) {
                  setStartCoords({ lat: depot.lat, lon: depot.lon });
                  setEndCoords({ lat: stops[0].lat, lon: stops[0].lon });
                }
              }}
            />
          ) : (
            <FleetControls
              fleetSize={fleetSize}
              onSetFleetSize={setFleetSize}
              vehicleCapacity={vehicleCapacity}
              onSetVehicleCapacity={setVehicleCapacity}
              depot={depot}
              stops={stops}
              onAddStop={handleAddStop}
              onRemoveStop={handleRemoveStop}
              onResetStops={handleResetStops}
              algorithm={vrpAlgorithm}
              onSetAlgorithm={setVrpAlgorithm}
              onSolve={handleSolveVRPTW}
              isLoading={isVrpLoading}
              selectedStopId={selectedStopId}
              onStopSelect={setSelectedStopId}
            />
          )}
        </div>

        {/* Center / Right: Interactive Map & Dispatch Inspector */}
        <div className="flex-1 flex flex-col relative overflow-hidden">
          {/* Map View */}
          <div className="flex-1 relative">
            <MapView
              center={center}
              zoom={zoom}
              viewportEdges={viewportEdges}
              depot={depot}
              stops={stops}
              activeRoute={activeRoute}
              vrpSolution={vrpSolution}
              selectedStopId={selectedStopId}
              onMapClick={handleMapClick}
              onStopSelect={setSelectedStopId}
              appMode={appMode}
              routeStart={startCoords}
              routeEnd={endCoords}
            />
          </div>

          {/* Bottom Drawer Dispatch Inspector (in Fleet Mode when solution exists) */}
          {appMode === "fleet" && vrpSolution && (
            <div className="shrink-0 z-20">
              <DispatchInspector
                solution={vrpSolution}
                onSelectStop={setSelectedStopId}
              />
            </div>
          )}
        </div>
      </div>

      {/* Benchmark Analytics Modal */}
      <BenchmarkModal
        isOpen={isBenchmarkOpen}
        onClose={() => setIsBenchmarkOpen(false)}
        mode={transportMode}
        departureTime={departureTime}
        costMetric={costMetric}
      />
    </div>
  );
};
export default App;
