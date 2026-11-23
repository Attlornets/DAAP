import React from "react";
import {
  Navigation,
  Compass,
  Gauge,
  Clock,
  Zap,
  ArrowRight,
  TrendingDown,
  Layers,
} from "lucide-react";
import { CostMetric, RouteResponse, RoutingAlgorithm } from "../../types";

interface RoutingControlsProps {
  algorithm: RoutingAlgorithm;
  onSetAlgorithm: (algo: RoutingAlgorithm) => void;
  costMetric: CostMetric;
  onSetCostMetric: (metric: CostMetric) => void;
  startCoords: { lat: number; lon: number } | null;
  endCoords: { lat: number; lon: number } | null;
  onCalculateRoute: () => void;
  isLoading: boolean;
  activeRoute: RouteResponse | null;
  onSetDefaultStartEnd: () => void;
}

export const RoutingControls: React.FC<RoutingControlsProps> = ({
  algorithm,
  onSetAlgorithm,
  costMetric,
  onSetCostMetric,
  startCoords,
  endCoords,
  onCalculateRoute,
  isLoading,
  activeRoute,
  onSetDefaultStartEnd,
}) => {
  return (
    <div className="flex flex-col h-full space-y-4 overflow-y-auto pr-1">
      {/* Route Endpoints Box */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
            <Navigation className="w-3.5 h-3.5 text-cyan-400" />
            <span>Path Endpoints</span>
          </h2>
          <button
            onClick={onSetDefaultStartEnd}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            Load Sample Pair
          </button>
        </div>

        <div className="space-y-2 text-xs">
          <div className="flex items-center space-x-2 bg-slate-950 p-2.5 rounded-xl border border-slate-800">
            <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold flex items-center justify-center text-[10px]">
              A
            </span>
            <div className="flex-1 truncate">
              {startCoords ? (
                <span className="font-mono text-slate-200">
                  {startCoords.lat.toFixed(4)}, {startCoords.lon.toFixed(4)}
                </span>
              ) : (
                <span className="text-slate-500 italic">Click map to set start...</span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2 bg-slate-950 p-2.5 rounded-xl border border-slate-800">
            <span className="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 font-bold flex items-center justify-center text-[10px]">
              B
            </span>
            <div className="flex-1 truncate">
              {endCoords ? (
                <span className="font-mono text-slate-200">
                  {endCoords.lat.toFixed(4)}, {endCoords.lon.toFixed(4)}
                </span>
              ) : (
                <span className="text-slate-500 italic">Click map to set destination...</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Algorithm & Metric Choice */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
        <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span>Algorithm Selection</span>
        </h2>

        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "dijkstra", label: "Dijkstra", desc: "Baseline search" },
            { id: "astar", label: "A* Search", desc: "Goal heuristic" },
            { id: "ch", label: "CH", desc: "Contraction Hierarchies" },
          ].map((item) => {
            const isSelected = algorithm === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSetAlgorithm(item.id as RoutingAlgorithm)}
                className={`p-2 rounded-xl text-left border transition-all ${
                  isSelected
                    ? "bg-cyan-950/60 border-cyan-500 text-cyan-300 shadow-md shadow-cyan-950"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div className="font-bold text-xs">{item.label}</div>
                <div className="text-[10px] text-slate-500 truncate">{item.desc}</div>
              </button>
            );
          })}
        </div>

        {/* Cost Metric Toggle */}
        <div className="flex items-center justify-between pt-2 border-t border-slate-800 text-xs">
          <span className="text-slate-400">Optimization Goal:</span>
          <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-[11px]">
            <button
              onClick={() => onSetCostMetric("time")}
              className={`px-2 py-0.5 rounded ${
                costMetric === "time" ? "bg-slate-800 text-cyan-300 font-semibold" : "text-slate-500"
              }`}
            >
              Fastest (Traffic-Aware)
            </button>
            <button
              onClick={() => onSetCostMetric("distance")}
              className={`px-2 py-0.5 rounded ${
                costMetric === "distance" ? "bg-slate-800 text-cyan-300 font-semibold" : "text-slate-500"
              }`}
            >
              Shortest Distance
            </button>
          </div>
        </div>

        {/* Calculate Button */}
        <button
          onClick={onCalculateRoute}
          disabled={!startCoords || !endCoords || isLoading}
          className="w-full mt-3 bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 disabled:opacity-50 text-white font-bold py-2.5 px-4 rounded-xl shadow-lg shadow-cyan-600/20 text-xs transition-all flex items-center justify-center space-x-2"
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Zap className="w-4 h-4" />
              <span>Compute Optimal Route</span>
            </>
          )}
        </button>
      </div>

      {/* Path Performance Metrics Card */}
      {activeRoute && activeRoute.found && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
            <Gauge className="w-3.5 h-3.5 text-emerald-400" />
            <span>Path Analytics</span>
          </h2>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Total Distance</span>
              <span className="text-base font-bold text-white font-mono">
                {(activeRoute.distance_m / 1000).toFixed(2)}{" "}
                <span className="text-xs font-normal text-slate-400">km</span>
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Estimated Time</span>
              <span className="text-base font-bold text-cyan-400 font-mono">
                {(activeRoute.duration_s / 60).toFixed(1)}{" "}
                <span className="text-xs font-normal text-slate-400">min</span>
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Nodes Settled</span>
              <span className="text-base font-bold text-amber-400 font-mono">
                {activeRoute.nodes_settled}
              </span>
            </div>
            <div className="bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <span className="text-[10px] text-slate-400 block">Compute Latency</span>
              <span className="text-base font-bold text-emerald-400 font-mono">
                {activeRoute.execution_time_ms.toFixed(2)}{" "}
                <span className="text-xs font-normal text-slate-400">ms</span>
              </span>
            </div>
          </div>

          {/* Turn-by-Turn Legs List */}
          <div className="pt-2 border-t border-slate-800">
            <div className="text-[11px] font-semibold text-slate-300 mb-2">Step-by-Step Breakdown</div>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {activeRoute.legs.map((leg, i) => (
                <div
                  key={i}
                  className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 text-[11px] flex items-center justify-between"
                >
                  <div className="truncate mr-2">
                    <span className="font-semibold text-slate-200">{leg.road_name}</span>
                    <span className="text-[10px] text-slate-500 block">
                      {leg.from_node} &rarr; {leg.to_node}
                    </span>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="font-mono text-cyan-400 block">{leg.distance_m}m</span>
                    <span className="text-[10px] text-slate-400">{(leg.duration_s / 60).toFixed(1)}m</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
