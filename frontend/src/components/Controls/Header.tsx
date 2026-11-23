import React from "react";
import {
  Car,
  Truck,
  Bike,
  Footprints,
  Clock,
  Layers,
  Zap,
  Activity,
  MapPin,
} from "lucide-react";
import { ScenarioInfo, TransportMode } from "../../types";

interface HeaderProps {
  scenarios: ScenarioInfo[];
  activeScenarioId: string;
  onSelectScenario: (id: string) => void;
  appMode: "routing" | "fleet";
  onSetAppMode: (mode: "routing" | "fleet") => void;
  transportMode: TransportMode;
  onSetTransportMode: (mode: TransportMode) => void;
  departureTime: string;
  onSetDepartureTime: (time: string) => void;
  onOpenBenchmark: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  scenarios,
  activeScenarioId,
  onSelectScenario,
  appMode,
  onSetAppMode,
  transportMode,
  onSetTransportMode,
  departureTime,
  onSetDepartureTime,
  onOpenBenchmark,
}) => {
  // Convert "HH:MM" to minutes for slider
  const [hours, minutes] = departureTime.split(":").map(Number);
  const totalMinutes = (hours || 0) * 60 + (minutes || 0);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    const h = Math.floor(val / 60);
    const m = val % 60;
    const formatted = `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}`;
    onSetDepartureTime(formatted);
  };

  // Determine current rush status
  const getTrafficStatus = (mins: number) => {
    const h = mins / 60;
    if (h >= 7.5 && h <= 9.5) return { label: "Morning Rush (2.2x delay)", color: "text-rose-400 bg-rose-500/10 border-rose-500/30" };
    if (h >= 16.5 && h <= 19.0) return { label: "Evening Rush (2.4x delay)", color: "text-rose-400 bg-rose-500/10 border-rose-500/30" };
    if (h >= 11.5 && h <= 13.5) return { label: "Midday Transit (1.3x)", color: "text-amber-400 bg-amber-500/10 border-amber-500/30" };
    return { label: "Free Flow (1.0x)", color: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30" };
  };

  const trafficInfo = getTrafficStatus(totalMinutes);

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between z-20 shrink-0">
      {/* Brand & Scenario */}
      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-cyan-500/20">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold tracking-tight text-white flex items-center space-x-2">
              <span>RouteForge</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                PROD
              </span>
            </h1>
            <p className="text-[10px] text-slate-400">Multi-Modal Logistics & VRPTW Optimizer</p>
          </div>
        </div>

        {/* Scenario Dropdown */}
        <div className="flex items-center space-x-2 bg-slate-800/80 px-2.5 py-1.5 rounded-lg border border-slate-700/60">
          <MapPin className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={activeScenarioId}
            onChange={(e) => onSelectScenario(e.target.value)}
            className="bg-transparent text-xs font-medium text-slate-200 outline-none cursor-pointer pr-1"
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id} className="bg-slate-900 text-slate-200">
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800">
        <button
          onClick={() => onSetAppMode("routing")}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            appMode === "routing"
              ? "bg-cyan-600 text-white shadow-md shadow-cyan-600/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Point-to-Point Lab</span>
        </button>
        <button
          onClick={() => onSetAppMode("fleet")}
          className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
            appMode === "fleet"
              ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Truck className="w-3.5 h-3.5" />
          <span>Fleet VRPTW Optimizer</span>
        </button>
      </div>

      {/* Traffic Time Slider & Transport Profiles */}
      <div className="flex items-center space-x-5">
        {/* Mode Selector */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800">
          {[
            { id: "driving", icon: Car, tip: "Passenger Car" },
            { id: "delivery_van", icon: Truck, tip: "Commercial Van" },
            { id: "cycling", icon: Bike, tip: "Cargo Bike" },
            { id: "walking", icon: Footprints, tip: "Courier On Foot" },
          ].map((item) => {
            const Icon = item.icon;
            const active = transportMode === item.id;
            return (
              <button
                key={item.id}
                title={item.tip}
                onClick={() => onSetTransportMode(item.id as TransportMode)}
                className={`p-1.5 rounded-md transition-all ${
                  active
                    ? "bg-slate-800 text-cyan-400 shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Icon className="w-4 h-4" />
              </button>
            );
          })}
        </div>

        {/* Departure Time & Traffic Slider */}
        <div className="flex items-center space-x-3 bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <div className="flex flex-col">
            <div className="flex items-center justify-between text-[11px] mb-0.5">
              <span className="font-mono text-cyan-300 font-semibold">{departureTime}</span>
              <span className={`text-[10px] px-1 rounded border ml-2 ${trafficInfo.color}`}>
                {trafficInfo.label}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={1439}
              step={15}
              value={totalMinutes}
              onChange={handleSliderChange}
              className="w-28 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
          </div>
        </div>

        {/* Benchmark Lab Button */}
        <button
          onClick={onOpenBenchmark}
          className="flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 px-3 py-2 rounded-xl text-xs font-semibold border border-slate-700 transition-colors shadow-sm"
        >
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          <span>Benchmark Lab</span>
        </button>
      </div>
    </header>
  );
};
