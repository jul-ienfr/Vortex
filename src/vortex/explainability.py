"""Explainability engine for VORTEX decisions."""

from __future__ import annotations

import json
from pathlib import Path


class ExplainabilityEngine:
    """Explains why the optimizer made a particular decision."""

    def __init__(self, project_path: Path):
        self.project_path = project_path

    def explain_cycle(self, cycle_data: dict) -> str:
        """Generate a human-readable explanation of a cycle."""
        decision = cycle_data.get("decision", "unknown")
        score_delta = cycle_data.get("score_delta", 0)
        hypothesis = cycle_data.get("hypothesis", "")
        files_changed = cycle_data.get("files_changed", [])

        if decision == "kept":
            return (
                f"✅ Changement accepté.\n"
                f"Hypothèse : {hypothesis}\n"
                f"Fichiers modifiés : {', '.join(files_changed)}\n"
                f"Score : +{score_delta:.3f} (amélioration)\n"
                f"Raison : Le changement a amélioré les métriques."
            )
        elif decision == "reverted":
            return (
                f"❌ Changement annulé (rollback).\n"
                f"Hypothèse : {hypothesis}\n"
                f"Score : {score_delta:.3f} (dégradation)\n"
                f"Raison : Le changement a dégradé les métriques. "
                f"Retour à la version précédente."
            )
        else:
            return f"ℹ️ Cycle terminé avec statut : {decision}"

    def explain_rollback(self, cycle_data: dict) -> str:
        """Explain why a rollback was performed."""
        return (
            f"Rollback effectué car le score a diminué de "
            f"{cycle_data.get('baseline_score', 0):.3f} à "
            f"{cycle_data.get('post_score', 0):.3f} "
            f"(-{abs(cycle_data.get('score_delta', 0)):.3f}). "
            f"Le changement \"{cycle_data.get('hypothesis', '')}\" "
            f"a dégradé les performances."
        )

    def explain_convergence(self, stats: dict) -> str:
        """Explain why the optimizer converged."""
        status = stats.get("convergence_status", "unknown")
        if status == "converged":
            return (
                f"🎯 Convergence atteinte après {stats.get('total_cycles', 0)} cycles.\n"
                f"Meilleur score : {stats.get('best_score', 0):.3f} (cycle {stats.get('best_cycle', 0)})\n"
                f"L'optimiseur ne s'améliore plus — le système est optimal."
            )
        elif status == "slowing":
            return (
                f"⏳ L'optimisation ralentit ({stats.get('no_improvement_count', 0)} cycles sans amélioration).\n"
                f"Meilleur score : {stats.get('best_score', 0):.3f}"
            )
        else:
            return f"📈 En cours d'optimisation — {stats.get('total_cycles', 0)} cycles effectués."

    def explain_debate(self, debate_result: dict) -> str:
        """Explain a debate result."""
        participants = debate_result.get("participants", [])
        consensus = debate_result.get("consensus")
        insights = debate_result.get("key_insights", [])

        lines = [f"🗣️ Débat entre {', '.join(participants)}:"]
        if consensus:
            lines.append(f"Consensus : {consensus}")
        if insights:
            lines.append("Insights clés :")
            for insight in insights:
                lines.append(f"  • {insight}")
        return "\n".join(lines)
