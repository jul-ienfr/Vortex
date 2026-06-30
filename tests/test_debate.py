"""Tests for the debate engine."""

from vortex.debate import DebateAgent, DebateEngine, DebateResult


def test_agent_creation():
    """Test creating a debate agent."""
    agent = DebateAgent("Test", "Test personality", ["expertise"], "style", "balanced")
    assert agent.name == "Test"
    assert "Test" in agent.to_prompt()


def test_engine_creation():
    """Test creating a debate engine."""
    engine = DebateEngine("standard")
    assert engine.method == "standard"


def test_invalid_method():
    """Test invalid debate method raises error."""
    try:
        DebateEngine("invalid_method")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_create_team():
    """Test team creation."""
    engine = DebateEngine()
    team = engine.create_team(3)
    assert len(team) == 3
    names = [a.name for a in team]
    assert len(set(names)) == 3  # all different


def test_debate_standard():
    """Test standard debate."""
    engine = DebateEngine("standard")
    team = engine.create_team(3)
    result = engine.debate("Test topic", team)
    assert isinstance(result, DebateResult)
    assert result.topic == "Test topic"
    assert len(result.rounds) == 3


def test_debate_oxford():
    """Test Oxford debate."""
    engine = DebateEngine("oxford")
    team = engine.create_team(2)
    result = engine.debate("Test topic", team)
    assert len(result.rounds) == 4  # opening + rebuttal for each side


def test_all_methods():
    """Test all 13 debate methods exist."""
    engine_methods = set(DebateEngine.METHODS.keys())
    expected = {
        "standard", "oxford", "advocate", "socratic", "delphi",
        "brainstorm", "tradeoff", "red_team", "premortem",
        "six_hats", "dialectic", "steelman", "panel",
    }
    assert engine_methods == expected


def test_all_methods_runnable():
    """Test that all methods can be called."""
    for method in DebateEngine.METHODS:
        engine = DebateEngine(method)
        team = engine.create_team(3)
        result = engine.debate("Test", team)
        assert isinstance(result, DebateResult)
