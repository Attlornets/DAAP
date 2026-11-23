"""
Simulated Annealing (SA) Metaheuristic Solver for VRPTW.

Features:
- Geometric cooling schedule with adaptive restarts
- Multi-neighborhood operators (2-opt, relocate, swap, cross-exchange)
- Metropolis acceptance criterion
- Convergence telemetry tracking cost, temperature, distance, and violations
"""
import copy
import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from app.algorithms.vrptw_models import VRPTWProblem, evaluate_solution


class VRPTWSimulatedAnnealing:
    def __init__(
        self,
        problem: VRPTWProblem,
        initial_temp: float = 400.0,
        cooling_rate: float = 0.985,
        iterations_per_temp: int = 15,
        min_temp: float = 0.5,
        random_seed: Optional[int] = 42
    ):
        self.problem = problem
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.iterations_per_temp = iterations_per_temp
        self.min_temp = min_temp
        if random_seed is not None:
            random.seed(random_seed)

    def _initial_solution(self) -> List[List[int]]:
        """Greedy Earliest-Deadline initial partition."""
        sorted_indices = sorted(
            range(len(self.problem.stops)),
            key=lambda i: self.problem.stops[i].earliest_arrival_s
        )
        routes: List[List[int]] = [[] for _ in range(self.problem.fleet_size)]
        loads = [0.0] * self.problem.fleet_size

        for idx in sorted_indices:
            stop = self.problem.stops[idx]
            assigned = False
            for v in range(self.problem.fleet_size):
                if loads[v] + stop.demand <= self.problem.vehicle_capacity:
                    routes[v].append(idx)
                    loads[v] += stop.demand
                    assigned = True
                    break
            if not assigned:
                min_v = loads.index(min(loads))
                routes[min_v].append(idx)
                loads[min_v] += stop.demand

        return [r for r in routes if r]

    def _generate_neighbor(self, current_routes: List[List[int]]) -> List[List[int]]:
        neighbor = [list(r) for r in current_routes]
        if not neighbor:
            return neighbor

        operator = random.choice(["2opt", "relocate", "swap", "route_rebalance"])

        if operator == "2opt":
            # Pick a route and reverse a slice
            r_idx = random.randrange(len(neighbor))
            r = neighbor[r_idx]
            if len(r) > 2:
                i, j = sorted(random.sample(range(len(r)), 2))
                r[i:j+1] = reversed(r[i:j+1])

        elif operator == "relocate":
            # Move customer from one route to another (or new position)
            non_empty = [i for i, r in enumerate(neighbor) if len(r) > 1]
            if non_empty:
                src_idx = random.choice(non_empty)
                cust = neighbor[src_idx].pop(random.randrange(len(neighbor[src_idx])))
                if len(neighbor) < self.problem.fleet_size and random.random() < 0.15:
                    neighbor.append([cust])
                else:
                    tgt_idx = random.randrange(len(neighbor))
                    insert_pos = random.randint(0, len(neighbor[tgt_idx]))
                    neighbor[tgt_idx].insert(insert_pos, cust)

        elif operator == "swap":
            # Swap two customers between routes
            all_stops = [(r_i, s_i) for r_i, r in enumerate(neighbor) for s_i in range(len(r))]
            if len(all_stops) >= 2:
                (r1, s1), (r2, s2) = random.sample(all_stops, 2)
                neighbor[r1][s1], neighbor[r2][s2] = neighbor[r2][s2], neighbor[r1][s1]

        elif operator == "route_rebalance":
            # Merge smallest route if possible
            if len(neighbor) > 1:
                smallest_idx = min(range(len(neighbor)), key=lambda i: len(neighbor[i]))
                if len(neighbor[smallest_idx]) <= 2:
                    donor = neighbor.pop(smallest_idx)
                    for c in donor:
                        target = random.choice(neighbor)
                        target.append(c)

        return [r for r in neighbor if r]

    def solve(self) -> Dict[str, Any]:
        start_time = time.perf_counter()

        current_solution = self._initial_solution()
        current_eval = evaluate_solution(self.problem, current_solution)
        current_cost = current_eval["total_cost"]

        best_solution = copy.deepcopy(current_solution)
        best_eval = current_eval
        best_cost = current_cost

        temp = self.initial_temp
        step = 0
        convergence_history: List[Dict[str, Any]] = []

        while temp > self.min_temp:
            for _ in range(self.iterations_per_temp):
                step += 1
                neighbor = self._generate_neighbor(current_solution)
                neighbor_eval = evaluate_solution(self.problem, neighbor)
                neighbor_cost = neighbor_eval["total_cost"]

                delta = neighbor_cost - current_cost

                # Metropolis acceptance criterion
                if delta <= 0.0 or random.random() < math.exp(-delta / max(0.001, temp)):
                    current_solution = neighbor
                    current_eval = neighbor_eval
                    current_cost = neighbor_cost

                    if current_cost < best_cost:
                        best_cost = current_cost
                        best_solution = copy.deepcopy(current_solution)
                        best_eval = current_eval

            # Record telemetry per temperature cooling step
            convergence_history.append({
                "step": step,
                "temperature": round(temp, 2),
                "current_cost": round(current_cost, 2),
                "best_cost": round(best_cost, 2),
                "best_distance_m": best_eval["total_distance_m"],
                "best_duration_s": best_eval["total_duration_s"],
                "lateness_s": best_eval["total_lateness_s"],
                "capacity_excess": best_eval["total_capacity_excess"],
                "is_feasible": best_eval["is_feasible"],
                "active_vehicles": best_eval["active_vehicles"]
            })

            temp *= self.cooling_rate

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "algorithm": "simulated_annealing",
            "execution_time_ms": round(elapsed_ms, 2),
            "total_steps": step,
            "final_temperature": round(temp, 4),
            "best_solution_routes": best_solution,
            "evaluation": best_eval,
            "convergence_history": convergence_history
        }
