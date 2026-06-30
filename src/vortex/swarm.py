"""Swarm exploration for VORTEX."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class SwarmAgent:
    """An agent in the swarm."""

    id: str
    specialization: str
    mutations: list[dict] = field(default_factory=list)
    fitness: float = 0.0


class SwarmExploration:
    """Distributed exploration of the change space."""

    SPECIALIZATIONS = [
        "config_optimization",
        "code_refactoring",
        "performance_tuning",
        "test_coverage",
        "documentation",
    ]

    def __init__(self, swarm_size: int = 3):
        self.swarm_size = swarm_size

    def create_swarm(self, context: dict | None = None) -> list[SwarmAgent]:
        """Create a population of agents."""
        agents = []
        for i in range(self.swarm_size):
            agent = SwarmAgent(
                id=f"swarm_{i}",
                specialization=self.SPECIALIZATIONS[i % len(self.SPECIALIZATIONS)],
                mutations=[],
                fitness=random.random(),
            )
            agents.append(agent)
        return agents

    def run_generation(self, agents: list[SwarmAgent]) -> list[dict]:
        """Run one generation of the swarm."""
        results = []
        for agent in agents:
            # Each agent proposes changes
            result = {
                "agent_id": agent.id,
                "specialization": agent.specialization,
                "changes": [
                    {"file": f"file_{random.randint(0,100)}.py", "description": f"Change by {agent.specialization}"}
                ],
                "fitness": random.random(),
            }
            results.append(result)
        return results

    def evolve(self, parents: list[dict], generations: int = 3) -> list[dict]:
        """Evolve the swarm over N generations."""
        agents = self.create_swarm()
        for gen in range(generations):
            # Mutation
            for agent in agents:
                if random.random() < 0.3:  # mutation rate
                    agent.mutations.append({"type": "mutate", "gen": gen})
                    agent.fitness = min(1.0, agent.fitness + random.uniform(-0.1, 0.2))

            # Crossover
            if len(agents) >= 2:
                for i in range(0, len(agents) - 1, 2):
                    child = self._crossover(agents[i], agents[i + 1])
                    agents.append(child)

            # Selection: keep top N
            agents.sort(key=lambda a: a.fitness, reverse=True)
            agents = agents[: self.swarm_size]

        # Return best results
        return [
            {"agent_id": a.id, "specialization": a.specialization, "fitness": a.fitness}
            for a in agents
        ]

    def _crossover(self, parent1: SwarmAgent, parent2: SwarmAgent) -> SwarmAgent:
        """Combine two agents."""
        return SwarmAgent(
            id=f"child_{parent1.id}_{parent2.id}",
            specialization=random.choice([parent1.specialization, parent2.specialization]),
            mutations=parent1.mutations[:1] + parent2.mutations[:1],
            fitness=(parent1.fitness + parent2.fitness) / 2,
        )
