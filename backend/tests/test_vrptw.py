"""
Unit tests for VRPTW Evaluator, Genetic Algorithm, and Simulated Annealing.
"""
import pytest
from app.algorithms.vrptw_ga import VRPTWGeneticAlgorithm
from app.algorithms.vrptw_models import DeliveryStop, Depot, VRPTWProblem, evaluate_solution
from app.algorithms.vrptw_sa import VRPTWSimulatedAnnealing
from app.data.preset_cities import generate_san_francisco_scenario


def test_vrptw_evaluation_and_violations():
    depot = Depot(id="dep", name="Depot", lat=0.0, lon=0.0, start_time_s=28800.0)
    stops = [
        DeliveryStop(id="s1", name="Stop 1", lat=0.01, lon=0.0, demand=40.0, earliest_arrival_s=28800.0, latest_arrival_s=30000.0),
        DeliveryStop(id="s2", name="Stop 2", lat=0.02, lon=0.0, demand=70.0, earliest_arrival_s=28800.0, latest_arrival_s=29000.0)
    ]
    # Small 3x3 matrix: depot=0, s1=1, s2=2
    # Distance in meters, travel time in seconds
    dist_mat = [
        [0.0, 1000.0, 2000.0],
        [1000.0, 0.0, 1000.0],
        [2000.0, 1000.0, 0.0]
    ]
    time_mat = [
        [0.0, 300.0, 600.0],
        [300.0, 0.0, 300.0],
        [600.0, 300.0, 0.0]
    ]

    # Vehicle capacity = 80. If both assigned to 1 vehicle, demand = 110 -> capacity violation = 30
    problem = VRPTWProblem(
        depot=depot,
        stops=stops,
        fleet_size=2,
        vehicle_capacity=80.0,
        dist_matrix=dist_mat,
        time_matrix=time_mat
    )

    # 1 vehicle serving both
    eval_viol = evaluate_solution(problem, [[0, 1]])
    assert eval_viol["total_capacity_excess"] == 30.0
    assert eval_viol["is_feasible"] is False

    # 2 vehicles serving separately -> demand 40 and 70 both <= 80 -> feasible!
    eval_feasible = evaluate_solution(problem, [[0], [1]])
    assert eval_feasible["total_capacity_excess"] == 0.0


def test_vrptw_ga_and_sa_solvers():
    _, problem, _ = generate_san_francisco_scenario()

    # Run GA
    ga = VRPTWGeneticAlgorithm(problem, population_size=20, generations=25, random_seed=42)
    res_ga = ga.solve()

    assert res_ga["algorithm"] == "genetic_algorithm"
    assert "evaluation" in res_ga
    assert res_ga["evaluation"]["active_vehicles"] <= problem.fleet_size
    assert len(res_ga["convergence_history"]) == 25

    # Run SA
    sa = VRPTWSimulatedAnnealing(problem, initial_temp=200.0, min_temp=5.0, iterations_per_temp=5, random_seed=42)
    res_sa = sa.solve()

    assert res_sa["algorithm"] == "simulated_annealing"
    assert "evaluation" in res_sa
    assert res_sa["evaluation"]["total_cost"] > 0
    assert len(res_sa["convergence_history"]) > 0
