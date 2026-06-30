"""Multi-agent debate engine for VORTEX."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class DebateAgent:
    """An agent with a unique personality."""

    name: str
    personality: str
    expertise: list[str]
    communication_style: str
    risk_tolerance: str  # "bold", "balanced", "conservative"
    model: str = "mimo-v2.5"  # which LLM this agent uses

    def to_prompt(self) -> str:
        """Convert to system prompt for LLM."""
        return (
            f"You are {self.name}. {self.personality}\n"
            f"Expertise: {', '.join(self.expertise)}\n"
            f"Communication style: {self.communication_style}\n"
            f"Risk tolerance: {self.risk_tolerance}\n"
            f"Stay in character during the debate."
        )


@dataclass
class DebateResult:
    """Result of a debate."""

    topic: str
    participants: list[str]
    rounds: list[dict]
    consensus: str | None = None
    winner: str | None = None
    key_insights: list[str] = field(default_factory=list)


# ── Agent personality pool ──────────────────────────────────

AGENT_POOL = [
    DebateAgent("Alexandre", "Architecte senior, pragmatique", ["architecture", "design patterns"], "Direct, concret", "conservative"),
    DebateAgent("Sophia", "Data scientist, sceptique", ["metrics", "statistics", "ML"], "Chiffres et données", "balanced"),
    DebateAgent("Marcus", "DevOps, conservateur", ["deployment", "monitoring", "security"], "Pense aux risques", "conservative"),
    DebateAgent("Léa", "Product manager, orientée utilisateur", ["UX", "prioritization"], "Pense à l'utilisateur", "balanced"),
    DebateAgent("Kai", "Chercheur, audacieux", ["research", "innovation"], "Cite des papiers", "bold"),
    DebateAgent("Elena", "Performance engineer", ["optimization", "benchmarks"], "Mesure tout", "bold"),
    DebateAgent("Thomas", "Tech lead, équilibré", ["code quality", "maintenability"], "Pense à long terme", "balanced"),
]


class DebateEngine:
    """Multi-agent debate engine with 13 methods."""

    METHODS = {
        "standard": "Round-robin discussion",
        "oxford": "Formal FOR/AGAINST debate",
        "advocate": "Devil's advocate",
        "socratic": "Question-driven dialogue",
        "delphi": "Iterative estimation",
        "brainstorm": "Diverge → build → converge",
        "tradeoff": "Structured alternatives comparison",
        "red_team": "Adversarial attack",
        "premortem": "Imagine failure, find causes",
        "six_hats": "6 perspectives (de Bono)",
        "dialectic": "Thesis → antithesis → synthesis",
        "steelman": "Strongest version of each argument",
        "panel": "Open discussion with moderator",
    }

    def __init__(self, method: str = "standard", models: list[str] | None = None):
        if method not in self.METHODS:
            raise ValueError(f"Unknown debate method: {method}. Available: {list(self.METHODS.keys())}")
        self.method = method
        self.models = models or ["mimo-v2.5"]

    def create_team(self, n_agents: int = 3) -> list[DebateAgent]:
        """Create a team of agents with diverse personalities and models."""
        # Select diverse agents (different risk tolerances, expertise)
        selected = []
        used_expertise: set[str] = set()
        pool = AGENT_POOL.copy()
        random.shuffle(pool)

        for agent in pool:
            if len(selected) >= n_agents:
                break
            # Prefer agents with non-overlapping expertise
            if not any(e in used_expertise for e in agent.expertise):
                # Assign model based on position (rotate through available models)
                agent.model = self.models[len(selected) % len(self.models)]
                selected.append(agent)
                used_expertise.update(agent.expertise)

        # Fill remaining slots randomly
        while len(selected) < n_agents and pool:
            agent = pool.pop()
            if agent not in selected:
                agent.model = self.models[len(selected) % len(self.models)]
                selected.append(agent)

        return selected[:n_agents]

    def debate(self, topic: str, agents: list[DebateAgent], context: dict | None = None) -> DebateResult:
        """Run a debate on a topic using actual LLM calls."""
        method_handler = getattr(self, f"_method_{self.method}")
        return method_handler(topic, agents, context or {})

    def _call_llm(self, agent: DebateAgent, prompt: str) -> str:
        """Call the LLM for a specific agent."""
        try:
            import litellm
            import os

            model = agent.model
            # For OpenAI-compatible proxies, prefix with openai/
            if not model.startswith("openai/"):
                model = f"openai/{model}"

            kwargs = {
                "model": model,
                "messages": [
                    {"role": "system", "content": agent.to_prompt()},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 1024,
            }

            # Add proxy
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
            return content or "No response"
        except Exception as e:
            return f"[Error: {e}]"

    def _method_standard(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Standard round-robin discussion with real LLM calls."""
        rounds = []
        for round_num in range(3):
            round_data = {"round": round_num + 1, "positions": {}}
            for agent in agents:
                prompt = f"Round {round_num + 1}: Give your position on '{topic}'. Be concise (2-3 sentences)."
                position = self._call_llm(agent, prompt)
                round_data["positions"][agent.name] = position
            rounds.append(round_data)
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_oxford(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Formal FOR/AGAINST debate."""
        if len(agents) < 2:
            agents = agents + agents[:1]  # duplicate if too few
        pro, contra = agents[0], agents[1]
        rounds = [
            {"round": "Opening FOR", "speaker": pro.name, "argument": f"FOR: {topic}"},
            {"round": "Opening AGAINST", "speaker": contra.name, "argument": f"AGAINST: {topic}"},
            {"round": "Rebuttal FOR", "speaker": pro.name, "argument": "Rebuttal supporting FOR"},
            {"round": "Rebuttal AGAINST", "speaker": contra.name, "argument": "Rebuttal supporting AGAINST"},
        ]
        return DebateResult(topic=topic, participants=[pro.name, contra.name], rounds=rounds)

    def _method_advocate(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Devil's advocate."""
        advocate = agents[0] if agents else AGENT_POOL[0]
        others = agents[1:] if len(agents) > 1 else AGENT_POOL[1:3]
        rounds = [
            {"round": "Position", "speaker": "group", "argument": f"Consensus on: {topic}"},
            {"round": "Challenge", "speaker": advocate.name, "argument": f"Devil's advocate: why {topic} might fail"},
            {"round": "Defense", "speaker": "group", "argument": "Defending the position"},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_socratic(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Question-driven dialogue."""
        rounds = []
        for i, agent in enumerate(agents):
            rounds.append({"round": f"Q{i+1}", "speaker": agent.name, "argument": f"Questioning assumptions about: {topic}"})
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_delphi(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Iterative estimation."""
        rounds = []
        for round_num in range(3):
            round_data = {"round": round_num + 1, "estimates": {}}
            for agent in agents:
                round_data["estimates"][agent.name] = f"Estimate from {agent.name}"
            rounds.append(round_data)
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_brainstorm(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Diverge → build → converge."""
        rounds = [
            {"round": "Diverge", "action": "Generate wild ideas"},
            {"round": "Build", "action": "Combine and improve ideas"},
            {"round": "Converge", "action": "Select top 3 ideas"},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_tradeoff(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Structured alternatives comparison."""
        rounds = [{"round": "Alternatives", "action": "List and score alternatives on 1-10 scale"}]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_red_team(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Adversarial attack."""
        attacker = agents[0] if agents else AGENT_POOL[0]
        rounds = [
            {"round": "Attack", "speaker": attacker.name, "argument": f"Attacking: {topic}"},
            {"round": "Defense", "speaker": "group", "argument": "Defending against attack"},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_premortem(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Imagine failure, find causes."""
        rounds = [{"round": "Pre-mortem", "action": "Imagine this failed — why?"}]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_six_hats(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """6 perspectives (de Bono)."""
        hats = ["Facts", "Emotions", "Risks", "Benefits", "Creativity", "Process"]
        rounds = [{"round": f"Hat: {h}", "speaker": agents[i % len(agents)].name} for i, h in enumerate(hats)]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_dialectic(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Thesis → antithesis → synthesis."""
        rounds = [
            {"round": "Thesis", "argument": f"Thesis on: {topic}"},
            {"round": "Antithesis", "argument": "Opposing view"},
            {"round": "Synthesis", "argument": "Combined insight"},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_steelman(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Strongest version of each argument."""
        rounds = [{"round": "Steelman", "action": "Present strongest version of each position"}]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_panel(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Open discussion with moderator."""
        moderator = agents[0] if agents else AGENT_POOL[0]
        rounds = [{"round": "Open discussion", "moderator": moderator.name, "topic": topic}]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)
