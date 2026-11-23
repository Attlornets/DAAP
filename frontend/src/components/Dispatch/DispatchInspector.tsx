import React, { useState } from "react";
import {
  Truck,
  CheckCircle2,
  AlertCircle,
  Clock,
  Package,
  Calendar,
  ChevronDown,
  ChevronUp,
  MapPin,
} from "lucide-react";
import { VRPTWSolutionResult, VehicleSchedule } from "../../types";

interface DispatchInspectorProps {
  solution: VRPTWSolutionResult;
  onClose?: () => void;
  onSelectStop?: (stopId: string) => void;
}

const VEHICLE_COLORS = [
  "#06b6d4", // cyan
  "#f59e0b", // amber
  "#a855f7", // purple
  "#10b981", // emerald
  "#ec4899", // pink
  "#3b82f6", // blue
];

export const DispatchInspector: React.FC<DispatchInspectorProps> = ({
  solution,
  onClose,
  onSelectStop,
}) => {
  const [expandedVehicles, setExpandedVehicles] = useState<Record<number, boolean>>({
    1: true,
  });

  const toggleVehicle = (id: number) => {
    setExpandedVehicles((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const evalData = solution.evaluation;

  return (
    <div className="bg-slate-900 border-t border-slate-800 p-4 shadow-2xl flex flex-col max-h-80 overflow-hidden">
      {/* KPI Top Bar */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-800 shrink-0">
        <div className="flex items-center space-x-3">
          <div className="p-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-lg">
            <Truck className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white uppercase tracking-wider">
              Fleet Dispatch & Route Inspector
            </h3>
            <span className="text-[10px] text-slate-400">
              Solver: <span className="text-emerald-400 capitalize">{solution.algorithm.replace("_", " ")}</span> &bull; Latency: {solution.execution_time_ms.toFixed(1)}ms
            </span>
          </div>
        </div>

        {/* Global KPIs */}
        <div className="flex items-center space-x-4 text-xs font-mono">
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block font-sans">Active Vans</span>
            <span className="font-bold text-slate-100">{evalData.active_vehicles}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block font-sans">Total Distance</span>
            <span className="font-bold text-cyan-400">
              {(evalData.total_distance_m / 1000).toFixed(1)} km
            </span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block font-sans">Total Time</span>
            <span className="font-bold text-amber-400">
              {(evalData.total_duration_s / 60).toFixed(0)} min
            </span>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block font-sans">Window Status</span>
            {evalData.total_lateness_s === 0 ? (
              <span className="font-bold text-emerald-400 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>100% On-Time</span>
              </span>
            ) : (
              <span className="font-bold text-rose-400 flex items-center space-x-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{(evalData.total_lateness_s / 60).toFixed(1)}m Late</span>
              </span>
            )}
          </div>
          {evalData.late_penalty_cost > 0 && (
            <div className="text-right">
              <span className="text-[10px] text-slate-400 block font-sans">Late Penalty</span>
              <span className="font-bold text-rose-400">${evalData.late_penalty_cost.toFixed(2)}</span>
            </div>
          )}
        </div>
      </div>

      {/* Per-Vehicle Schedules Carousel / List */}
      <div className="flex-1 overflow-y-auto mt-3 space-y-3 pr-1">
        {evalData.vehicle_schedules.map((veh: VehicleSchedule, idx: number) => {
          const color = VEHICLE_COLORS[idx % VEHICLE_COLORS.length];
          const isExpanded = !!expandedVehicles[veh.vehicle_id];

          return (
            <div
              key={veh.vehicle_id}
              className="bg-slate-950 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm transition-all"
            >
              {/* Vehicle Header Accordion */}
              <div
                onClick={() => toggleVehicle(veh.vehicle_id)}
                className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-900/60 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span
                    className="w-3 h-3 rounded-full shrink-0"
                    style={{ backgroundColor: color }}
                  />
                  <div>
                    <span className="font-bold text-xs text-slate-200">
                      Vehicle #{veh.vehicle_id}
                    </span>
                    <span className="text-[11px] text-slate-400 ml-2">
                      ({veh.stop_count} stops &bull; {(veh.total_distance_m / 1000).toFixed(1)}km &bull; {(veh.total_duration_s / 60).toFixed(0)}m)
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-4 text-xs font-mono">
                  {/* Load bar */}
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] text-slate-400">Load:</span>
                    <span className="font-bold text-slate-200">
                      {veh.total_demand}/{veh.capacity} kg
                    </span>
                    <span className="text-[10px] text-cyan-400">
                      ({veh.capacity_utilization_pct}%)
                    </span>
                  </div>

                  {veh.lateness_s > 0 ? (
                    <span className="text-rose-400 text-[11px] font-bold">
                      {(veh.lateness_s / 60).toFixed(1)}m Delay
                    </span>
                  ) : (
                    <span className="text-emerald-400 text-[11px]">On-Time</span>
                  )}

                  {isExpanded ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </div>

              {/* Stop Sequence Breakdown */}
              {isExpanded && (
                <div className="px-3 pb-3 pt-1 border-t border-slate-800/60 overflow-x-auto">
                  <div className="flex items-center space-x-2 min-w-max py-1">
                    {veh.timeline.map((stop, sIdx) => {
                      const isDepot = stop.type.startsWith("depot");
                      return (
                        <React.Fragment key={sIdx}>
                          <div
                            onClick={() => onSelectStop && onSelectStop(stop.stop_id)}
                            className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-transform hover:scale-105 ${
                              isDepot
                                ? "bg-amber-950/20 border-amber-800/60 text-amber-300"
                                : stop.is_late
                                ? "bg-rose-950/30 border-rose-600/80 text-rose-200"
                                : "bg-slate-900 border-slate-800 text-slate-200"
                            }`}
                          >
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-bold text-[11px] truncate max-w-[120px]">
                                {stop.name}
                              </span>
                              {!isDepot && (
                                <span className="text-[10px] font-mono ml-1 text-slate-400">
                                  {stop.demand}kg
                                </span>
                              )}
                            </div>

                            <div className="text-[10px] text-slate-400 font-mono space-y-0.5">
                              <div>
                                Arr: <span className="text-slate-200 font-semibold">{stop.arrival_time}</span>
                              </div>
                              <div>
                                Dep: <span className="text-slate-200 font-semibold">{stop.departure_time}</span>
                              </div>
                              {stop.waiting_s > 0 && (
                                <div className="text-cyan-400">
                                  Wait: {(stop.waiting_s / 60).toFixed(0)}m
                                </div>
                              )}
                              {stop.is_late && (
                                <div className="text-rose-400 font-bold">
                                  Late: {(stop.lateness_s / 60).toFixed(0)}m
                                </div>
                              )}
                            </div>
                          </div>

                          {sIdx < veh.timeline.length - 1 && (
                            <span className="text-slate-600 font-bold">&rarr;</span>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
