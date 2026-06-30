"""Tests for tree search."""

from vortex.tree_search import SearchArchive, TreeNode, TreeSearch


def test_tree_node_creation():
    """Test creating a tree node."""
    node = TreeNode(changes=[{"file": "test.py", "description": "test"}])
    assert len(node.changes) == 1
    assert node.score_estimate == 0.0


def test_archive_add():
    """Test adding nodes to archive."""
    archive = SearchArchive()
    node = TreeNode(score_estimate=0.5)
    archive.add(node)
    assert len(archive.nodes) == 1


def test_archive_get_best():
    """Test getting best nodes."""
    archive = SearchArchive()
    archive.add(TreeNode(score_estimate=0.3))
    archive.add(TreeNode(score_estimate=0.8))
    archive.add(TreeNode(score_estimate=0.5))
    best = archive.get_best(2)
    assert len(best) == 2
    assert best[0].score_estimate == 0.8


def test_archive_diverse():
    """Test diverse selection."""
    archive = SearchArchive()
    for i in range(10):
        archive.add(TreeNode(score_estimate=i * 0.1))
    diverse = archive.get_diverse(3)
    assert len(diverse) == 3


def test_archive_sample_parent():
    """Test weighted sampling."""
    archive = SearchArchive()
    archive.add(TreeNode(score_estimate=0.1))
    archive.add(TreeNode(score_estimate=0.9))
    parent = archive.sample_parent()
    assert isinstance(parent, TreeNode)


def test_tree_search_returns_changes():
    """Test that tree search returns changes."""
    search = TreeSearch(max_depth=2, branching_factor=2)
    changes = search.search({"metrics": {}})
    assert isinstance(changes, list)


def test_tree_search_respects_depth():
    """Test depth limit."""
    search = TreeSearch(max_depth=1, branching_factor=2)
    search.search({})
    # All nodes should be at depth <= 1
    for node in search.archive.nodes:
        assert node.depth <= 1


def test_tree_search_archive_grows():
    """Test that archive accumulates results."""
    search = TreeSearch(max_depth=2, branching_factor=2)
    search.search({})
    search.search({})
    assert len(search.archive.nodes) >= 2


def test_recombine():
    """Test recombination of two nodes."""
    search = TreeSearch()
    p1 = TreeNode(changes=[{"file": "a.py", "description": "change a"}])
    p2 = TreeNode(changes=[{"file": "b.py", "description": "change b"}])
    child = search.recombine(p1, p2)
    assert len(child.changes) > 0
