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
        """Formal FOR/AGAINST debate with real LLM calls."""
        if len(agents) < 2:
            agents = agents + agents[:1]
        pro, contra = agents[0], agents[1]

        # Opening statements
        pro_opening = self._call_llm(pro, f"You argue FOR this topic: '{topic}'. Give your opening statement (2-3 sentences).")
        contra_opening = self._call_llm(contra, f"You argue AGAINST this topic: '{topic}'. Give your opening statement (2-3 sentences).")

        # Rebuttals
        pro_rebuttal = self._call_llm(pro, f"The opposing side said: '{contra_opening}'. Rebut their argument (2-3 sentences).")
        contra_rebuttal = self._call_llm(contra, f"The opposing side said: '{pro_opening}'. Rebut their argument (2-3 sentences).")

        rounds = [
            {"round": "Opening FOR", "speaker": pro.name, "argument": pro_opening},
            {"round": "Opening AGAINST", "speaker": contra.name, "argument": contra_opening},
            {"round": "Rebuttal FOR", "speaker": pro.name, "argument": pro_rebuttal},
            {"round": "Rebuttal AGAINST", "speaker": contra.name, "argument": contra_rebuttal},
        ]
        return DebateResult(topic=topic, participants=[pro.name, contra.name], rounds=rounds)

    def _method_advocate(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Devil's advocate with real LLM calls."""
        advocate = agents[0] if agents else AGENT_POOL[0]
        others = agents[1:] if len(agents) > 1 else [AGENT_POOL[1]]

        # Group consensus
        consensus = self._call_llm(others[0], f"Give a brief consensus position on: '{topic}' (2-3 sentences).")

        # Devil's advocate challenge
        challenge = self._call_llm(advocate, f"You are the devil's advocate. Challenge this consensus: '{consensus}'. Why might it fail? (2-3 sentences)")

        # Defense
        defense = self._call_llm(others[0], f"The devil's advocate challenges your position: '{challenge}'. Defend your position (2-3 sentences).")

        rounds = [
            {"round": "Position", "speaker": others[0].name, "argument": consensus},
            {"round": "Challenge", "speaker": advocate.name, "argument": challenge},
            {"round": "Defense", "speaker": others[0].name, "argument": defense},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_socratic(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Question-driven dialogue with real LLM calls."""
        rounds = []
        for i, agent in enumerate(agents):
            if i == 0:
                prompt = f"Ask a probing question about: '{topic}'. Be specific and insightful."
            else:
                prev_question = rounds[-1]["argument"] if rounds else topic
                prompt = f"The previous question was: '{prev_question}'. Ask a follow-up question that digs deeper."
            question = self._call_llm(agent, prompt)
            rounds.append({"round": f"Q{i+1}", "speaker": agent.name, "argument": question})
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_delphi(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Iterative estimation with real LLM calls."""
        rounds = []
        estimates = {}
        for round_num in range(3):
            round_data = {"round": round_num + 1, "estimates": {}}
            for agent in agents:
                if round_num == 0:
                    prompt = f"Give your estimate/opinion on: '{topic}' (2-3 sentences)."
                else:
                    prev = estimates.get(agent.name, topic)
                    prompt = f"Others have shared their views. Your previous view was: '{prev}'. Revise your estimate considering other perspectives (2-3 sentences)."
                estimate = self._call_llm(agent, prompt)
                estimates[agent.name] = estimate
                round_data["estimates"][agent.name] = estimate
            rounds.append(round_data)
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_brainstorm(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Diverge → build → converge with real LLM calls."""
        # Diverge: each agent generates ideas
        diverge_round = {"round": "Diverge", "ideas": {}}
        for agent in agents:
            ideas = self._call_llm(agent, f"Generate 3 wild, creative ideas for: '{topic}'. Be bold and unconventional.")
            diverge_round["ideas"][agent.name] = ideas

        # Build: combine ideas
        all_ideas = " ".join(diverge_round["ideas"].values())
        build_round = {"round": "Build", "combinations": {}}
        for agent in agents:
            combined = self._call_llm(agent, f"Here are various ideas: '{all_ideas}'. Combine the best ones into 2-3 actionable proposals.")
            build_round["combinations"][agent.name] = combined

        # Converge: vote on best
        all_proposals = " ".join(build_round["combinations"].values())
        converge_round = {"round": "Converge", "votes": {}}
        for agent in agents:
            vote = self._call_llm(agent, f"Here are the proposals: '{all_proposals}'. Which ONE do you think is best and why? (1-2 sentences)")
            converge_round["votes"][agent.name] = vote

        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=[diverge_round, build_round, converge_round])

    def _method_tradeoff(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Structured alternatives comparison with real LLM calls."""
        rounds = []
        # Each agent proposes alternatives
        alternatives_round = {"round": "Alternatives", "proposals": {}}
        for agent in agents:
            proposal = self._call_llm(agent, f"Propose 2-3 alternatives for: '{topic}'. For each, give a brief description and score it 1-10.")
            alternatives_round["proposals"][agent.name] = proposal
        rounds.append(alternatives_round)

        # Each agent evaluates all alternatives
        all_proposals = " ".join(alternatives_round["proposals"].values())
        evaluate_round = {"round": "Evaluate", "evaluations": {}}
        for agent in agents:
            eval_result = self._call_llm(agent, f"Here are the alternatives: '{all_proposals}'. Which alternative do you prefer and why? (2-3 sentences)")
            evaluate_round["evaluations"][agent.name] = eval_result
        rounds.append(evaluate_round)

        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_red_team(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Adversarial attack with real LLM calls."""
        attacker = agents[0] if agents else AGENT_POOL[0]
        defender = agents[1] if len(agents) > 1 else AGENT_POOL[1]

        # Attack
        attack = self._call_llm(attacker, f"You are a red team attacker. Find vulnerabilities and weaknesses in: '{topic}'. Be aggressive and specific (2-3 sentences).")

        # Defense
        defense = self._call_llm(defender, f"You are defending against this attack: '{attack}'. Defend the position (2-3 sentences).")

        # Counter-attack
        counter = self._call_llm(attacker, f"The defense said: '{defense}'. Counter-attack with a stronger argument (2-3 sentences).")

        rounds = [
            {"round": "Attack", "speaker": attacker.name, "argument": attack},
            {"round": "Defense", "speaker": defender.name, "argument": defense},
            {"round": "Counter-attack", "speaker": attacker.name, "argument": counter},
        ]
        return DebateResult(topic=topic, participants=[attacker.name, defender.name], rounds=rounds)

    def _method_premortem(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Imagine failure, find causes with real LLM calls."""
        rounds = []
        for agent in agents:
            analysis = self._call_llm(agent, f"Imagine that '{topic}' has failed catastrophically. What are the 3 most likely causes? Be specific (3-4 sentences).")
            rounds.append({"round": "Pre-mortem", "speaker": agent.name, "argument": analysis})
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_six_hats(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """6 perspectives (de Bono) with real LLM calls."""
        hats = {
            "White (Facts)": "Focus only on objective facts and data about",
            "Red (Emotions)": "Share your gut feelings and emotions about",
            "Black (Risks)": "Be the pessimist — what could go wrong with",
            "Yellow (Benefits)": "Be the optimist — what are the benefits of",
            "Green (Creativity)": "Think creatively — what wild ideas do you have for",
            "Blue (Process)": "Think about the process — how should we approach",
        }
        rounds = []
        for i, (hat_name, hat_instruction) in enumerate(hats.items()):
            agent = agents[i % len(agents)]
            response = self._call_llm(agent, f"{hat_instruction} '{topic}'. Be concise (2-3 sentences).")
            rounds.append({"round": f"Hat: {hat_name}", "speaker": agent.name, "argument": response})
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_dialectic(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Thesis → antithesis → synthesis with real LLM calls."""
        thesis_agent = agents[0] if agents else AGENT_POOL[0]
        antithesis_agent = agents[1] if len(agents) > 1 else AGENT_POOL[1]
        synthesis_agent = agents[2] if len(agents) > 2 else AGENT_POOL[2]

        thesis = self._call_llm(thesis_agent, f"Present a strong thesis for: '{topic}' (2-3 sentences).")
        antithesis = self._call_llm(antithesis_agent, f"The thesis is: '{thesis}'. Present a strong antithesis (2-3 sentences).")
        synthesis = self._call_llm(synthesis_agent, f"Thesis: '{thesis}'. Antithesis: '{antithesis}'. Synthesize both into a unified view (2-3 sentences).")

        rounds = [
            {"round": "Thesis", "speaker": thesis_agent.name, "argument": thesis},
            {"round": "Antithesis", "speaker": antithesis_agent.name, "argument": antithesis},
            {"round": "Synthesis", "speaker": synthesis_agent.name, "argument": synthesis},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents[:3]], rounds=rounds)

    def _method_steelman(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Strongest version of each argument with real LLM calls."""
        rounds = []
        for agent in agents:
            steelman = self._call_llm(agent, f"Present the STRONGEST possible argument for: '{topic}'. Steel-man the position — make it as compelling as possible, even if you disagree (3-4 sentences).")
            rounds.append({"round": "Steelman", "speaker": agent.name, "argument": steelman})

        # Final synthesis
        all_steelmans = " ".join([r["argument"] for r in rounds])
        synthesis_agent = agents[0] if agents else AGENT_POOL[0]
        synthesis = self._call_llm(synthesis_agent, f"Here are the strongest arguments: '{all_steelmans}'. Which is most compelling and why? (2-3 sentences)")
        rounds.append({"round": "Synthesis", "speaker": synthesis_agent.name, "argument": synthesis})

        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)

    def _method_panel(self, topic: str, agents: list[DebateAgent], ctx: dict) -> DebateResult:
        """Open discussion with moderator using real LLM calls."""
        moderator = agents[0] if agents else AGENT_POOL[0]
        panelists = agents[1:] if len(agents) > 1 else agents

        # Moderator opens
        opening = self._call_llm(moderator, f"You are moderating a panel discussion on: '{topic}'. Open the discussion with a brief framing question (2-3 sentences).")

        # Panelists respond
        responses = []
        for agent in panelists:
            response = self._call_llm(agent, f"The moderator asked: '{opening}'. Give your perspective on: '{topic}' (2-3 sentences).")
            responses.append({"speaker": agent.name, "argument": response})

        # Moderator synthesizes
        all_responses = " ".join([r["argument"] for r in responses])
        synthesis = self._call_llm(moderator, f"Panelist responses: '{all_responses}'. Synthesize the key points and conclude the discussion (2-3 sentences).")

        rounds = [
            {"round": "Opening", "speaker": moderator.name, "argument": opening},
            {"round": "Responses", "responses": responses},
            {"round": "Synthesis", "speaker": moderator.name, "argument": synthesis},
        ]
        return DebateResult(topic=topic, participants=[a.name for a in agents], rounds=rounds)
