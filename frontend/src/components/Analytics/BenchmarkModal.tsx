import React, { useState } from "react";
import {
  X,
  Play,
  Zap,
  BarChart2,
  TrendingUp,
  Cpu,
  Layers,
  Award,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from "recharts";
import {
  CostMetric,
  RoutingBenchmarkResponse,
  TransportMode,
} from "../../types";
import { benchmarkVRPTW, runRoutingBenchmark } from "../../services/api";

interface BenchmarkModalProps {
  isOpen: boolean;
  onClose: () => void;
  mode: TransportMode;
  departureTime: string;
  costMetric: CostMetric;
}

export const BenchmarkModal: React.FC<BenchmarkModalProps> = ({
  isOpen,
  onClose,
  mode,
  departureTime,
  costMetric,
}) => {
  const [activeTab, setActiveTab] = useState<"routing" | "vrptw">("routing");
  const [pairCount, setPairCount] = useState(25);
  const [isRoutingRunning, setIsRoutingRunning] = useState(false);
  const [routingData, setRoutingData] = useState<RoutingBenchmarkResponse | null>(null);

  const [isVRPRunning, setIsVRPRunning] = useState(false);
  const [vrpBenchData, setVrpBenchData] = useState<any | null>(null);

  if (!isOpen) return null;

  const handleRunRouting = async () => {
    setIsRoutingRunning(true);
    try {
      const res = await runRoutingBenchmark(pairCount, mode, departureTime, costMetric);
      setRoutingData(res);
    } catch (err) {
      console.error(err);
      alert("Routing benchmark failed to execute.");
    } finally {
      setIsRoutingRunning(false);
    }
  };

  const handleRunVRP = async () => {
    setIsVRPRunning(true);
    try {
      const res = await benchmarkVRPTW();
      setVrpBenchData(res);
    } catch (err) {
      console.error(err);
      alert("VRPTW benchmark failed to execute.");
    } finally {
      setIsVRPRunning(false);
    }
  };

  // Prepare chart data for Routing Benchmark
  const routingChartData = routingData
    ? [
        {
          name: "Dijkstra",
          latency_ms: routingData.metrics.dijkstra?.avg_latency_ms || 0,
          settled_nodes: routingData.metrics.dijkstra?.avg_nodes_settled || 0,
          speedup: "1.0x",
        },
        {
          name: "A* Search",
          latency_ms: routingData.metrics.astar?.avg_latency_ms || 0,
          settled_nodes: routingData.metrics.astar?.avg_nodes_settled || 0,
          speedup: `${routingData.metrics.astar?.speedup_vs_dijkstra || 1}x`,
        },
        {
          name: "Contraction Hierarchies",
          latency_ms: routingData.metrics.contraction_hierarchies?.avg_latency_ms || 0,
          settled_nodes: routingData.metrics.contraction_hierarchies?.avg_nodes_settled || 0,
          speedup: `${routingData.metrics.contraction_hierarchies?.speedup_vs_dijkstra || 1}x`,
        },
      ]
    : [];

  // Prepare chart data for VRPTW Convergence
  const vrpConvergenceData = [];
  if (vrpBenchData) {
    const gaConv = vrpBenchData.genetic?.convergence || [];
    const saConv = vrpBenchData.simulated_annealing?.convergence || [];
    const maxLen = Math.max(gaConv.length, saConv.length);

    for (let i = 0; i < maxLen; i++) {
      vrpConvergenceData.push({
        step: i + 1,
        GA_BestCost: gaConv[i] ? gaConv[i].best_cost : undefined,
        SA_BestCost: saConv[i] ? saConv[i].best_cost : undefined,
      });
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-6">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="p-6 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 rounded-xl">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Algorithm & Benchmark Analytics Lab</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                  REAL-TIME
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Empirical latency, graph node settlement, and metaheuristic convergence comparison.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Tab switch */}
            <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                onClick={() => setActiveTab("routing")}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  activeTab === "routing"
                    ? "bg-cyan-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Routing: Dijkstra vs A* vs CH
              </button>
              <button
                onClick={() => setActiveTab("vrptw")}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  activeTab === "vrptw"
                    ? "bg-emerald-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                VRPTW: Genetic vs Simulated Annealing
              </button>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-200 rounded-xl bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {activeTab === "routing" ? (
            <div className="space-y-6">
              {/* Controls bar */}
              <div className="flex items-center justify-between bg-slate-950 p-4 rounded-2xl border border-slate-800">
                <div className="flex items-center space-x-4 text-xs">
                  <span className="text-slate-400">Random Test Queries:</span>
                  <div className="flex space-x-2">
                    {[10, 25, 50].map((count) => (
                      <button
                        key={count}
                        onClick={() => setPairCount(count)}
                        className={`px-2.5 py-1 rounded-lg border font-mono font-bold ${
                          pairCount === count
                            ? "bg-cyan-600 border-cyan-500 text-white"
                            : "bg-slate-900 border-slate-800 text-slate-400"
                        }`}
                      >
                        {count} Pairs
                      </button>
                    ))}
                  </div>
                  <span className="text-slate-500">|</span>
                  <span className="text-slate-400">
                    Mode: <span className="font-bold text-slate-200 capitalize">{mode}</span> &bull; Departure:{" "}
                    <span className="font-mono text-cyan-300">{departureTime}</span>
                  </span>
                </div>

                <button
                  onClick={handleRunRouting}
                  disabled={isRoutingRunning}
                  className="bg-gradient-to-r from-cyan-600 to-emerald-600 hover:from-cyan-500 hover:to-emerald-500 disabled:opacity-50 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center space-x-2 shadow-lg shadow-cyan-600/20"
                >
                  {isRoutingRunning ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-white" />
                      <span>Execute Comparative Benchmark</span>
                    </>
                  )}
                </button>
              </div>

              {routingData ? (
                <>
                  {/* KPI Cards */}
                  <div className="grid grid-cols-3 gap-4">
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                      <span className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                        <Award className="w-4 h-4 text-amber-400" />
                        <span>CH Speedup vs Dijkstra</span>
                      </span>
                      <span className="text-2xl font-black text-amber-400 font-mono">
                        {routingData.metrics.contraction_hierarchies?.speedup_vs_dijkstra || 1}x
                      </span>
                      <span className="text-[11px] text-slate-500 block mt-1">
                        Faster than baseline Dijkstra
                      </span>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                      <span className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                        <Zap className="w-4 h-4 text-cyan-400" />
                        <span>CH Average Latency</span>
                      </span>
                      <span className="text-2xl font-black text-cyan-400 font-mono">
                        {routingData.metrics.contraction_hierarchies?.avg_latency_ms || 0} ms
                      </span>
                      <span className="text-[11px] text-slate-500 block mt-1">
                        vs {routingData.metrics.dijkstra?.avg_latency_ms || 0} ms (Dijkstra)
                      </span>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                      <span className="text-xs text-slate-400 flex items-center space-x-1.5 mb-1">
                        <Layers className="w-4 h-4 text-emerald-400" />
                        <span>Nodes Settled Reduction</span>
                      </span>
                      <span className="text-2xl font-black text-emerald-400 font-mono">
                        {routingData.metrics.contraction_hierarchies?.avg_nodes_settled || 0}{" "}
                        <span className="text-xs font-normal text-slate-500">nodes</span>
                      </span>
                      <span className="text-[11px] text-slate-500 block mt-1">
                        vs {routingData.metrics.dijkstra?.avg_nodes_settled || 0} nodes (Dijkstra)
                      </span>
                    </div>
                  </div>

                  {/* Dual Bar Charts */}
                  <div className="grid grid-cols-2 gap-4">
                    {/* Latency Chart */}
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                        Average Query Latency (ms) - Lower is Faster
                      </h4>
                      <div className="h-48 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={routingChartData}>
                            <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                            <YAxis stroke="#64748b" fontSize={10} />
                            <Tooltip
                              contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                            />
                            <Bar dataKey="latency_ms" fill="#06b6d4" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>

                    {/* Settled Nodes Chart */}
                    <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                      <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                        Nodes Settled - Search Space Efficiency
                      </h4>
                      <div className="h-48 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={routingChartData}>
                            <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                            <YAxis stroke="#64748b" fontSize={10} />
                            <Tooltip
                              contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                            />
                            <Bar dataKey="settled_nodes" fill="#10b981" radius={[6, 6, 0, 0]} />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-slate-950 border border-dashed border-slate-800 rounded-2xl p-12 text-center text-slate-500">
                  <BarChart2 className="w-10 h-10 mx-auto mb-2 text-slate-600" />
                  <p className="text-sm font-semibold text-slate-400">No benchmark results yet</p>
                  <p className="text-xs mt-1">
                    Click "Execute Comparative Benchmark" to generate empirical runtime profiles across algorithms.
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {/* VRPTW Metaheuristic Controls */}
              <div className="flex items-center justify-between bg-slate-950 p-4 rounded-2xl border border-slate-800">
                <div className="text-xs text-slate-300">
                  <span>Compare </span>
                  <span className="font-bold text-emerald-400">Genetic Algorithm (OX Crossover + 2-Opt)</span>
                  <span> vs </span>
                  <span className="font-bold text-cyan-400">Simulated Annealing (Metropolis Cooling)</span>
                </div>

                <button
                  onClick={handleRunVRP}
                  disabled={isVRPRunning}
                  className="bg-gradient-to-r from-emerald-600 to-cyan-600 hover:from-emerald-500 hover:to-cyan-500 disabled:opacity-50 text-white font-bold px-4 py-2 rounded-xl text-xs flex items-center space-x-2 shadow-lg shadow-emerald-600/20"
                >
                  {isVRPRunning ? (
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-white" />
                      <span>Run Metaheuristic Comparison</span>
                    </>
                  )}
                </button>
              </div>

              {vrpBenchData ? (
                <>
                  {/* Summary Comparison Grid */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-slate-950 p-4 rounded-2xl border border-emerald-900/40">
                      <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">
                        Genetic Algorithm
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Objective Cost</span>
                          <span className="text-base font-bold text-white">
                            {vrpBenchData.genetic.total_cost}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Execution Time</span>
                          <span className="text-base font-bold text-emerald-400">
                            {vrpBenchData.genetic.execution_time_ms} ms
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Fleet Distance</span>
                          <span className="text-slate-200">
                            {(vrpBenchData.genetic.distance_m / 1000).toFixed(1)} km
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Delay / Penalty</span>
                          <span className="text-slate-200">
                            {(vrpBenchData.genetic.lateness_s / 60).toFixed(1)}m late
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-slate-950 p-4 rounded-2xl border border-cyan-900/40">
                      <h4 className="text-xs font-bold text-cyan-400 uppercase tracking-wider mb-2">
                        Simulated Annealing
                      </h4>
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Objective Cost</span>
                          <span className="text-base font-bold text-white">
                            {vrpBenchData.simulated_annealing.total_cost}
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Execution Time</span>
                          <span className="text-base font-bold text-cyan-400">
                            {vrpBenchData.simulated_annealing.execution_time_ms} ms
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Fleet Distance</span>
                          <span className="text-slate-200">
                            {(vrpBenchData.simulated_annealing.distance_m / 1000).toFixed(1)} km
                          </span>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-400 block font-sans">Delay / Penalty</span>
                          <span className="text-slate-200">
                            {(vrpBenchData.simulated_annealing.lateness_s / 60).toFixed(1)}m late
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Convergence Trajectory Chart */}
                  <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
                      Convergence Trajectory (Objective Cost vs Iteration Step)
                    </h4>
                    <div className="h-56 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={vrpConvergenceData}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="step" stroke="#64748b" fontSize={10} />
                          <YAxis stroke="#64748b" fontSize={10} />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", borderRadius: "0.75rem" }}
                          />
                          <Legend wrapperStyle={{ fontSize: "11px" }} />
                          <Line
                            type="monotone"
                            dataKey="GA_BestCost"
                            name="Genetic Algorithm"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={false}
                          />
                          <Line
                            type="monotone"
                            dataKey="SA_BestCost"
                            name="Simulated Annealing"
                            stroke="#06b6d4"
                            strokeWidth={2}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                </>
              ) : (
                <div className="bg-slate-950 border border-dashed border-slate-800 rounded-2xl p-12 text-center text-slate-500">
                  <TrendingUp className="w-10 h-10 mx-auto mb-2 text-slate-600" />
                  <p className="text-sm font-semibold text-slate-400">No VRPTW convergence curves yet</p>
                  <p className="text-xs mt-1">
                    Click "Run Metaheuristic Comparison" to compute multi-vehicle routes using GA and SA.
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
