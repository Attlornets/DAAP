"""
Genetic Algorithm (GA) Solver for VRPTW.

Features:
- Heuristic initialization (Greedy Earliest-Deadline + Nearest Neighbor)
- Order Crossover (OX) with route repair
- Intra-route 2-Opt and Inter-route Relocate/Swap mutations
- Convergence telemetry tracking cost, distance, violations, and runtime
"""
import copy
import random
import time
from typing import Any, Dict, List, Tuple

from app.algorithms.vrptw_models import VRPTWProblem, evaluate_solution


class VRPTWGeneticAlgorithm:
    def __init__(
        self,
        problem: VRPTWProblem,
        population_size: int = 40,
        generations: int = 80,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.25,
        tournament_size: int = 3,
        random_seed: Optional[int] = 42
    ):
        self.problem = problem
        self.population_size = max(10, population_size)
        self.generations = max(10, generations)
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        if random_seed is not None:
            random.seed(random_seed)

    def _generate_greedy_edf_individual(self) -> List[List[int]]:
        """Sorts stops by earliest deadline and greedily assigns to vehicles."""
        sorted_indices = sorted(
            range(len(self.problem.stops)),
            key=lambda i: self.problem.stops[i].earliest_arrival_s
        )
        routes: List[List[int]] = [[] for _ in range(self.problem.fleet_size)]
        loads = [0.0] * self.problem.fleet_size

        for idx in sorted_indices:
            stop = self.problem.stops[idx]
            # Find vehicle with least load that has capacity
            assigned = False
            for v in range(self.problem.fleet_size):
                if loads[v] + stop.demand <= self.problem.vehicle_capacity:
                    routes[v].append(idx)
                    loads[v] += stop.demand
                    assigned = True
                    break
            if not assigned:
                # Assign to vehicle with smallest current load
                min_v = loads.index(min(loads))
                routes[min_v].append(idx)
                loads[min_v] += stop.demand

        return [r for r in routes if r]

    def _generate_random_individual(self) -> List[List[int]]:
        indices = list(range(len(self.problem.stops)))
        random.shuffle(indices)

        routes: List[List[int]] = [[] for _ in range(self.problem.fleet_size)]
        if not indices:
            return routes

        # Randomly distribute stops across vehicles
        for idx in indices:
            v = random.randint(0, self.problem.fleet_size - 1)
            routes[v].append(idx)

        # Ensure no empty routes if we have fewer vehicles than stops
        routes = [r for r in routes if r]
        return routes if routes else [indices]

    def _tournament_select(self, population: List[List[List[int]]], costs: List[float]) -> List[List[int]]:
        candidates = random.sample(range(len(population)), min(self.tournament_size, len(population)))
        best_idx = min(candidates, key=lambda i: costs[i])
        return copy.deepcopy(population[best_idx])

    def _crossover(self, parent1: List[List[int]], parent2: List[List[int]]) -> List[List[int]]:
        """
        Order Crossover adapted for multi-route partitions.
        Takes a route from parent1, and fills remaining stops using parent2's order.
        """
        if random.random() > self.crossover_rate or not parent1:
            return copy.deepcopy(parent1)

        # Pick one donor route from parent1
        donor_route = random.choice(parent1)
        selected_stops = set(donor_route)

        child_routes: List[List[int]] = [list(donor_route)]

        # Collect unassigned stops preserving parent2 order
        unassigned = []
        for r in parent2:
            for s in r:
                if s not in selected_stops:
                    unassigned.append(s)

        # Distribute remaining stops across up to (fleet_size - 1) additional routes
        rem_vehicles = max(1, self.problem.fleet_size - 1)
        bucket_size = max(1, len(unassigned) // rem_vehicles) if unassigned else 0

        curr_bucket: List[int] = []
        for s in unassigned:
            curr_bucket.append(s)
            if len(curr_bucket) >= bucket_size and len(child_routes) < self.problem.fleet_size:
                child_routes.append(curr_bucket)
                curr_bucket = []
        if curr_bucket:
            if len(child_routes) < self.problem.fleet_size:
                child_routes.append(curr_bucket)
            else:
                child_routes[-1].extend(curr_bucket)

        return [r for r in child_routes if r]

    def _mutate(self, routes: List[List[int]]) -> List[List[int]]:
        if random.random() > self.mutation_rate or not routes:
            return routes

        mutated = [list(r) for r in routes]
        move_type = random.choice(["2opt", "swap", "relocate"])

        if move_type == "2opt":
            # Reverse a segment in a random route
            r = random.choice(mutated)
            if len(r) > 2:
                i, j = sorted(random.sample(range(len(r)), 2))
                r[i:j+1] = reversed(r[i:j+1])

        elif move_type == "swap":
            # Swap two stops between or within routes
            all_stops = [(r_idx, s_idx) for r_idx, r in enumerate(mutated) for s_idx in range(len(r))]
            if len(all_stops) >= 2:
                (r1, s1), (r2, s2) = random.sample(all_stops, 2)
                mutated[r1][s1], mutated[r2][s2] = mutated[r2][s2], mutated[r1][s1]

        elif move_type == "relocate":
            # Move a stop from one route to another
            non_empty = [r_idx for r_idx, r in enumerate(mutated) if len(r) > 1]
            if non_empty:
                src_r_idx = random.choice(non_empty)
                stop = mutated[src_r_idx].pop(random.randrange(len(mutated[src_r_idx])))
                # Insert into another route or new route
                if len(mutated) < self.problem.fleet_size and random.random() < 0.2:
                    mutated.append([stop])
                else:
                    tgt_r_idx = random.randrange(len(mutated))
                    insert_pos = random.randint(0, len(mutated[tgt_r_idx]))
                    mutated[tgt_r_idx].insert(insert_pos, stop)

        return [r for r in mutated if r]

    def solve(self) -> Dict[str, Any]:
        start_time = time.perf_counter()

        # Initialize population
        population: List[List[List[int]]] = []
        population.append(self._generate_greedy_edf_individual())

        while len(population) < self.population_size:
            population.append(self._generate_random_individual())

        convergence_history: List[Dict[str, Any]] = []

        best_solution: Optional[List[List[int]]] = None
        best_eval: Optional[Dict[str, Any]] = None
        best_cost = float("inf")

        for gen in range(self.generations):
            evals = [evaluate_solution(self.problem, ind) for ind in population]
            costs = [e["total_cost"] for e in evals]

            # Find generation best
            gen_best_idx = min(range(len(costs)), key=lambda i: costs[i])
            if costs[gen_best_idx] < best_cost:
                best_cost = costs[gen_best_idx]
                best_solution = copy.deepcopy(population[gen_best_idx])
                best_eval = evals[gen_best_idx]

            avg_cost = sum(costs) / len(costs)

            # Record telemetry
            convergence_history.append({
                "generation": gen + 1,
                "best_cost": round(best_cost, 2),
                "avg_cost": round(avg_cost, 2),
                "best_distance_m": best_eval["total_distance_m"] if best_eval else 0.0,
                "best_duration_s": best_eval["total_duration_s"] if best_eval else 0.0,
                "lateness_s": best_eval["total_lateness_s"] if best_eval else 0.0,
                "capacity_excess": best_eval["total_capacity_excess"] if best_eval else 0.0,
                "is_feasible": best_eval["is_feasible"] if best_eval else False,
                "active_vehicles": best_eval["active_vehicles"] if best_eval else 0
            })

            # Create next generation with elitism (keep top 2)
            sorted_indices = sorted(range(len(costs)), key=lambda i: costs[i])
            next_generation = [
                copy.deepcopy(population[sorted_indices[0]]),
                copy.deepcopy(population[sorted_indices[1]])
            ]

            while len(next_generation) < self.population_size:
                p1 = self._tournament_select(population, costs)
                p2 = self._tournament_select(population, costs)
                child = self._crossover(p1, p2)
                child = self._mutate(child)
                next_generation.append(child)

            population = next_generation

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "algorithm": "genetic_algorithm",
            "execution_time_ms": round(elapsed_ms, 2),
            "generations_run": self.generations,
            "population_size": self.population_size,
            "best_solution_routes": best_solution,
            "evaluation": best_eval,
            "convergence_history": convergence_history
        }
