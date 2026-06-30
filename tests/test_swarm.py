"""Tests for swarm exploration."""

from vortex.swarm import SwarmAgent, SwarmExploration


def test_swarm_creation():
    """Test creating a swarm."""
    swarm = SwarmExploration(swarm_size=3)
    agents = swarm.create_swarm()
    assert len(agents) == 3
    assert all(isinstance(a, SwarmAgent) for a in agents)


def test_swarm_specializations():
    """Test that agents have different specializations."""
    swarm = SwarmExploration(swarm_size=3)
    agents = swarm.create_swarm()
    specs = [a.specialization for a in agents]
    assert len(set(specs)) == 3  # all different


def test_run_generation():
    """Test running a generation."""
    swarm = SwarmExploration(swarm_size=3)
    agents = swarm.create_swarm()
    results = swarm.run_generation(agents)
    assert len(results) == 3
    assert all("fitness" in r for r in results)


def test_evolve():
    """Test evolution over generations."""
    swarm = SwarmExploration(swarm_size=3)
    parents = [{"fitness": 0.5} for _ in range(3)]
    results = swarm.evolve(parents, generations=3)
    assert len(results) == 3
    assert all("fitness" in r for r in results)


def test_crossover():
    """Test crossover of two agents."""
    swarm = SwarmExploration()
    p1 = SwarmAgent(id="p1", specialization="code_refactoring", fitness=0.8)
    p2 = SwarmAgent(id="p2", specialization="performance_tuning", fitness=0.6)
    child = swarm._crossover(p1, p2)
    assert child.specialization in ["code_refactoring", "performance_tuning"]
    assert child.fitness == 0.7  # average
