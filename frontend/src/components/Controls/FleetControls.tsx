import React, { useState } from "react";
import {
  Truck,
  Package,
  Clock,
  Plus,
  Trash2,
  Sliders,
  Play,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { DeliveryStop, Depot, VRPAlgorithm } from "../../types";

interface FleetControlsProps {
  fleetSize: number;
  onSetFleetSize: (size: number) => void;
  vehicleCapacity: number;
  onSetVehicleCapacity: (cap: number) => void;
  depot: Depot;
  stops: DeliveryStop[];
  onAddStop: (stop: DeliveryStop) => void;
  onRemoveStop: (id: string) => void;
  onResetStops: () => void;
  algorithm: VRPAlgorithm;
  onSetAlgorithm: (algo: VRPAlgorithm) => void;
  onSolve: () => void;
  isLoading: boolean;
  selectedStopId?: string | null;
  onStopSelect?: (id: string) => void;
}

export const FleetControls: React.FC<FleetControlsProps> = ({
  fleetSize,
  onSetFleetSize,
  vehicleCapacity,
  onSetVehicleCapacity,
  depot,
  stops,
  onAddStop,
  onRemoveStop,
  onResetStops,
  algorithm,
  onSetAlgorithm,
  onSolve,
  isLoading,
  selectedStopId,
  onStopSelect,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [newStopName, setNewStopName] = useState("");
  const [newDemand, setNewDemand] = useState(15);
  const [newEarliest, setNewEarliest] = useState("08:30");
  const [newLatest, setNewLatest] = useState("10:00");

  const totalDemand = stops.reduce((sum, s) => sum + s.demand, 0);
  const totalFleetCapacity = fleetSize * vehicleCapacity;
  const isOverCapacity = totalDemand > totalFleetCapacity;

  const handleCreateStop = (e: React.FormEvent) => {
    e.preventDefault();
    // Offset slightly from depot for demo if not clicked
    const newStop: DeliveryStop = {
      id: `custom_stop_${Date.now()}`,
      name: newStopName || `Stop #${stops.length + 1}`,
      lat: Number((depot.lat + (Math.random() - 0.5) * 0.02).toFixed(6)),
      lon: Number((depot.lon + (Math.random() - 0.5) * 0.02).toFixed(6)),
      demand: Number(newDemand),
      service_time_s: 300,
      earliest_time: newEarliest,
      latest_time: newLatest,
    };
    onAddStop(newStop);
    setShowAddModal(false);
    setNewStopName("");
  };

  return (
    <div className="flex flex-col h-full space-y-4 overflow-y-auto pr-1">
      {/* Fleet & Capacity Config Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
        <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Truck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Fleet Parameters</span>
        </h2>

        {/* Fleet Size Slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Active Vehicles</span>
            <span className="font-bold font-mono text-emerald-400">{fleetSize} Vans</span>
          </div>
          <input
            type="range"
            min={1}
            max={6}
            value={fleetSize}
            onChange={(e) => onSetFleetSize(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
          />
        </div>

        {/* Vehicle Capacity Slider */}
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-slate-400">Capacity per Van</span>
            <span className="font-bold font-mono text-cyan-400">{vehicleCapacity} kg</span>
          </div>
          <input
            type="range"
            min={30}
            max={180}
            step={5}
            value={vehicleCapacity}
            onChange={(e) => onSetVehicleCapacity(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
          />
        </div>

        {/* Capacity Utilization Bar */}
        <div className="pt-2 border-t border-slate-800/80">
          <div className="flex justify-between text-[11px] mb-1">
            <span className="text-slate-400">Total Demand / Capacity:</span>
            <span className={`font-mono font-bold ${isOverCapacity ? "text-rose-400" : "text-slate-200"}`}>
              {totalDemand} / {totalFleetCapacity} kg
            </span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-2 border border-slate-800 overflow-hidden">
            <div
              className={`h-full transition-all ${
                isOverCapacity ? "bg-rose-500" : "bg-gradient-to-r from-cyan-500 to-emerald-500"
              }`}
              style={{ width: `${Math.min(100, (totalDemand / Math.max(1, totalFleetCapacity)) * 100)}%` }}
            />
          </div>
          {isOverCapacity && (
            <p className="text-[10px] text-rose-400 mt-1">
              Warning: Demand exceeds fleet capacity. Increase fleet size or van capacity!
            </p>
          )}
        </div>
      </div>

      {/* Metaheuristic Solver Selection */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3">
        <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
          <Sliders className="w-3.5 h-3.5 text-cyan-400" />
          <span>Metaheuristic Solver</span>
        </h2>

        <div className="grid grid-cols-2 gap-2 text-xs">
          {[
            { id: "genetic", label: "Genetic Algo", desc: "Population & OX crossover" },
            { id: "simulated_annealing", label: "Sim. Annealing", desc: "Adaptive cooling & 2-opt" },
          ].map((item) => {
            const isSelected = algorithm === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSetAlgorithm(item.id as VRPAlgorithm)}
                className={`p-2.5 rounded-xl text-left border transition-all ${
                  isSelected
                    ? "bg-emerald-950/60 border-emerald-500 text-emerald-300 shadow-md shadow-emerald-950"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                }`}
              >
                <div className="font-bold text-xs">{item.label}</div>
                <div className="text-[10px] text-slate-500 truncate">{item.desc}</div>
              </button>
            );
          })}
        </div>

        <button
          onClick={onSolve}
          disabled={isLoading || stops.length === 0}
          className="w-full mt-2 bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-50 text-white font-bold py-2.5 px-4 rounded-xl shadow-lg shadow-emerald-600/20 text-xs transition-all flex items-center justify-center space-x-2"
        >
          {isLoading ? (
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>Optimize Multi-Vehicle Schedule</span>
            </>
          )}
        </button>
      </div>

      {/* Delivery Stops Management Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-lg space-y-3 flex-1 flex flex-col min-h-[300px]">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
            <Package className="w-3.5 h-3.5 text-amber-400" />
            <span>Delivery Stops ({stops.length})</span>
          </h2>
          <div className="flex items-center space-x-2">
            <button
              onClick={onResetStops}
              title="Reset Preset Stops"
              className="p-1 rounded text-slate-400 hover:text-slate-200"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setShowAddModal(true)}
              className="flex items-center space-x-1 text-[11px] bg-slate-800 hover:bg-slate-700 text-cyan-300 px-2 py-1 rounded-lg border border-slate-700"
            >
              <Plus className="w-3 h-3" />
              <span>Add Stop</span>
            </button>
          </div>
        </div>

        {/* Stops List */}
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 max-h-[360px]">
          {stops.map((stop, index) => {
            const isSelected = selectedStopId === stop.id;
            return (
              <div
                key={stop.id}
                onClick={() => onStopSelect && onStopSelect(stop.id)}
                className={`p-2 rounded-xl border text-xs cursor-pointer transition-all flex items-center justify-between ${
                  isSelected
                    ? "bg-slate-800 border-cyan-500 shadow-sm"
                    : "bg-slate-950 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center space-x-2.5 truncate mr-2">
                  <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 text-slate-300 font-mono text-[10px] flex items-center justify-center shrink-0">
                    {index + 1}
                  </span>
                  <div className="truncate">
                    <span className="font-semibold text-slate-200 block truncate">{stop.name}</span>
                    <span className="text-[10px] text-slate-400 flex items-center space-x-2">
                      <span className="text-amber-400 font-mono">{stop.demand}kg</span>
                      <span>&bull;</span>
                      <span className="text-cyan-400 font-mono">
                        {stop.earliest_time} - {stop.latest_time}
                      </span>
                    </span>
                  </div>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveStop(stop.id);
                  }}
                  className="text-slate-500 hover:text-rose-400 p-1 rounded shrink-0 transition-colors"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Add Stop Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl space-y-4">
            <h3 className="text-sm font-bold text-white flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              <span>Create New Delivery Stop</span>
            </h3>
            <form onSubmit={handleCreateStop} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Stop / Client Name</label>
                <input
                  type="text"
                  placeholder="e.g. Retail Depot 4"
                  value={newStopName}
                  onChange={(e) => setNewStopName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Demand Weight (kg)</label>
                <input
                  type="number"
                  min={1}
                  max={80}
                  value={newDemand}
                  onChange={(e) => setNewDemand(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-slate-400 block mb-1">Window Open</label>
                  <input
                    type="time"
                    value={newEarliest}
                    onChange={(e) => setNewEarliest(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
                <div>
                  <label className="text-slate-400 block mb-1">Window Close</label>
                  <input
                    type="time"
                    value={newLatest}
                    onChange={(e) => setNewLatest(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-100 outline-none focus:border-cyan-500 font-mono"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-2 rounded-xl text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl font-bold shadow-md shadow-cyan-600/30"
                >
                  Add Stop
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
