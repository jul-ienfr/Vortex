"""Swarm exploration for VORTEX."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SwarmAgent:
    """An agent in the swarm."""

    id: str
    specialization: str
    mutations: list[dict] = field(default_factory=list)
    fitness: float = 0.0
    proposed_changes: list[dict] = field(default_factory=list)


SPECIALIZATIONS = [
    "config_optimization",
    "code_refactoring",
    "performance_tuning",
    "test_coverage",
    "documentation",
]


class SwarmExploration:
    """Distributed exploration of the change space using LLM."""

    def __init__(self, swarm_size: int = 3):
        self.swarm_size = swarm_size

    def create_swarm(self, context: dict | None = None) -> list[SwarmAgent]:
        """Create a population of agents."""
        agents = []
        for i in range(self.swarm_size):
            agent = SwarmAgent(
                id=f"swarm_{i}",
                specialization=SPECIALIZATIONS[i % len(SPECIALIZATIONS)],
                mutations=[],
                fitness=0.0,
            )
            agents.append(agent)
        return agents

    def run_generation(self, agents: list[SwarmAgent]) -> list[dict]:
        """Run one generation of the swarm using LLM for mutations."""
        results = []
        for agent in agents:
            # Use LLM to generate a real change
            change = self._generate_change_via_llm(agent)
            fitness = self._evaluate_change_via_llm(change)

            result = {
                "agent_id": agent.id,
                "specialization": agent.specialization,
                "changes": [change] if change else [],
                "fitness": fitness,
            }
            results.append(result)
        return results

    def evolve(self, parents: list[dict], generations: int = 3) -> list[dict]:
        """Evolve the swarm over N generations using LLM."""
        agents = self.create_swarm()
        for gen in range(generations):
            # Mutation: each agent proposes changes via LLM
            for agent in agents:
                if random.random() < 0.5:  # mutation rate
                    change = self._generate_change_via_llm(agent)
                    if change:
                        agent.mutations.append(change)
                        # Evaluate the mutation via LLM
                        agent.fitness = self._evaluate_change_via_llm(change)

            # Crossover: combine best agents
            if len(agents) >= 2:
                agents.sort(key=lambda a: a.fitness, reverse=True)
                for i in range(0, min(2, len(agents) - 1), 2):
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

    def _generate_change_via_llm(self, agent: SwarmAgent) -> dict | None:
        """Use LLM to generate a real change."""
        try:
            import litellm
            import os

            prompt = f"""You are a {agent.specialization} specialist.
Generate ONE specific optimization change for a Python project.
Output ONLY a JSON object: {{"file": "path/to/file.py", "description": "specific change"}}
Be specific and actionable."""

            model = "openai/mimo-v2.5"
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
                "max_tokens": 256,
            }
            kwargs["api_base"] = "http://192.168.31.59:4000/v1"
            if not os.environ.get("OPENAI_API_KEY"):
                kwargs["api_key"] = "not-needed"

            response = litellm.completion(**kwargs)
            msg = response.choices[0].message
            content = msg.content or ""
            if not content and hasattr(msg, 'reasoning_content') and msg.reasoning_content:
                content = msg.reasoning_content
            if not content:
                fields = getattr(msg, 'provider_specific_fields', {})
                details = fields.get('reasoning_details', [])
                if details:
                    content = details[0].get('text', '')

            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {"file": data.get("file", ""), "description": data.get("description", "")}
        except Exception as e:
            logger.warning("LLM change generation failed for %s: %s", agent.id, e)
        return None

    def _evaluate_change_via_llm(self, change: dict | None) -> float:
        """Use LLM to evaluate a change."""
        if not change:
            return 0.0

        try:
            import litellm
            import os

            prompt = f"""Evaluate this proposed change on a scale of 0.0 to 1.0:
File: {change.get('file', 'unknown')}
Description: {change.get('description', 'unknown')}

Consider: feasibility, impact, risk. Output ONLY a number."""

            model = "openai/deepseek-v4-flash"
            kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 10,
            }
            kwargs["api_base"] = "http://192.168.31.59:4000/v1"
            if not os.environ.get("OPENAI_API_KEY"):
                kwargs["api_key"] = "not-needed"

            response = litellm.completion(**kwargs)
            content = response.choices[0].message.content or "0.5"
            # Extract number from response
            import re
            num_match = re.search(r'(\d+\.?\d*)', content)
            if num_match:
                return min(1.0, max(0.0, float(num_match.group(1))))
        except Exception as e:
            logger.warning("LLM evaluation failed: %s", e)
        return 0.5

    def _crossover(self, parent1: SwarmAgent, parent2: SwarmAgent) -> SwarmAgent:
        """Combine two agents."""
        return SwarmAgent(
            id=f"child_{parent1.id}_{parent2.id}",
            specialization=random.choice([parent1.specialization, parent2.specialization]),
            mutations=parent1.mutations[:1] + parent2.mutations[:1],
            fitness=(parent1.fitness + parent2.fitness) / 2,
        )
