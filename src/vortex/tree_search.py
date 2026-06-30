"""Tree search with archive-based evolution for VORTEX."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TreeNode:
    """A node in the search tree."""

    changes: list[dict] = field(default_factory=list)
    score_estimate: float = 0.0
    actual_score: float | None = None
    children: list[TreeNode] = field(default_factory=list)
    reflection: str | None = None
    depth: int = 0


class SearchArchive:
    """Archive of all explored nodes (inspired by DGM)."""

    def __init__(self):
        self.nodes: list[TreeNode] = []

    def add(self, node: TreeNode) -> None:
        """Add a node to the archive."""
        self.nodes.append(node)

    def get_best(self, n: int = 5) -> list[TreeNode]:
        """Return the top-N nodes by score estimate."""
        sorted_nodes = sorted(self.nodes, key=lambda n: n.score_estimate, reverse=True)
        return sorted_nodes[:n]

    def get_diverse(self, n: int = 5) -> list[TreeNode]:
        """Return diverse selections across score range."""
        if len(self.nodes) <= n:
            return self.nodes.copy()
        # Stratified sampling
        sorted_nodes = sorted(self.nodes, key=lambda n: n.score_estimate)
        step = max(1, len(sorted_nodes) // n)
        return [sorted_nodes[i * step] for i in range(n)]

    def sample_parent(self) -> TreeNode:
        """Weighted random selection biased toward higher scores."""
        if not self.nodes:
            raise ValueError("Archive is empty")
        # Weight by score (shift to make all positive)
        min_score = min(n.score_estimate for n in self.nodes)
        weights = [n.score_estimate - min_score + 1.0 for n in self.nodes]
        return random.choices(self.nodes, weights=weights, k=1)[0]


class TreeSearch:
    """Tree search with archive-based evolution."""

    def __init__(self, max_depth: int = 3, branching_factor: int = 3):
        self.max_depth = max_depth
        self.branching_factor = branching_factor
        self.archive = SearchArchive()

    def search(self, context: dict) -> list[dict]:
        """Explore the tree and return the best sequence of changes."""
        root = TreeNode(changes=[], score_estimate=0.0)
        best = self._dfs(root, context, depth=0)
        self.archive.add(best)
        return best.changes

    def _dfs(self, node: TreeNode, context: dict, depth: int) -> TreeNode:
        """Depth-first search with heuristic evaluation."""
        if depth >= self.max_depth:
            return node

        # Generate children
        children = self._generate_children(node, context)

        # Evaluate each child
        for child in children:
            child.score_estimate = self._evaluate(child, context)

        # Sort by score
        children.sort(key=lambda c: c.score_estimate, reverse=True)

        # Prune: keep top branching_factor
        children = children[: self.branching_factor]

        # Explore best child
        best = node
        for child in children:
            result = self._dfs(child, context, depth + 1)
            if result.score_estimate > best.score_estimate:
                best = result

        return best

    def _generate_children(self, node: TreeNode, context: dict) -> list[TreeNode]:
        """Generate child nodes via mutation and recombination."""
        children = []

        # Mutation: add a new change
        for _ in range(self.branching_factor):
            child = TreeNode(
                changes=node.changes.copy(),
                depth=node.depth + 1,
            )
            # Add a random change (placeholder — real impl uses LLM)
            child.changes.append({
                "file": f"file_{random.randint(0, 100)}.py",
                "description": f"Optimization at depth {child.depth}",
            })
            children.append(child)

        # Recombination from archive (if available)
        if self.archive.nodes:
            parent2 = self.archive.sample_parent()
            recombined = self.recombine(node, parent2)
            children.append(recombined)

        return children

    def _evaluate(self, node: TreeNode, context: dict) -> float:
        """Heuristic evaluation of a node."""
        # More changes = higher potential but higher risk
        n_changes = len(node.changes)
        base_score = 0.5
        # Bonus for moderate number of changes
        if 1 <= n_changes <= 3:
            base_score += 0.2
        elif n_changes > 3:
            base_score -= 0.1 * (n_changes - 3)
        return base_score

    def recombine(self, parent1: TreeNode, parent2: TreeNode) -> TreeNode:
        """Combine changes from two parents (inspired by EvoLLM)."""
        # Interleave changes from both parents
        combined = []
        max_len = max(len(parent1.changes), len(parent2.changes))
        for i in range(max_len):
            if i < len(parent1.changes) and random.random() < 0.5:
                combined.append(parent1.changes[i])
            elif i < len(parent2.changes):
                combined.append(parent2.changes[i])
            elif i < len(parent1.changes):
                combined.append(parent1.changes[i])

        return TreeNode(
            changes=combined,
            depth=max(parent1.depth, parent2.depth) + 1,
        )
