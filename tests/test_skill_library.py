"""Tests for skill library."""

from pathlib import Path

from vortex.skill_library import SkillLibrary


def test_create_skill(tmp_project: Path):
    """Test creating a skill."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "modify file.py")
    assert skill.name == "test"
    assert skill.id.startswith("skill_")


def test_record_success(tmp_project: Path):
    """Test recording a success."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "modify file.py")
    lib.record_success(skill.id, 0.5)
    updated = lib.get_skill(skill.id)
    assert updated.success_count == 1
    assert updated.consecutive_successes == 1


def test_crystallization(tmp_project: Path):
    """Test auto-crystallization after 3 consecutive successes."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "modify file.py")
    for _ in range(3):
        lib.record_success(skill.id, 0.5)
    updated = lib.get_skill(skill.id)
    assert updated.crystallized


def test_record_failure(tmp_project: Path):
    """Test recording a failure resets streak."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "modify file.py")
    lib.record_success(skill.id, 0.5)
    lib.record_success(skill.id, 0.5)
    lib.record_failure(skill.id, "broke something")
    updated = lib.get_skill(skill.id)
    assert updated.consecutive_successes == 0
    assert updated.failure_count == 1


def test_list_skills(tmp_project: Path):
    """Test listing skills."""
    lib = SkillLibrary(tmp_project)
    lib.create_skill("s1", "Skill 1", "template1")
    lib.create_skill("s2", "Skill 2", "template2")
    skills = lib.list_skills()
    assert len(skills) == 2


def test_crystallized_only(tmp_project: Path):
    """Test listing only crystallized skills."""
    lib = SkillLibrary(tmp_project)
    s1 = lib.create_skill("s1", "Skill 1", "template1")
    s2 = lib.create_skill("s2", "Skill 2", "template2")
    lib.record_success(s1.id, 0.5)
    lib.record_success(s1.id, 0.5)
    lib.record_success(s1.id, 0.5)  # crystallized
    crystallized = lib.list_skills(crystallized_only=True)
    assert len(crystallized) == 1
    assert crystallized[0].id == s1.id


def test_delete_skill(tmp_project: Path):
    """Test deleting a skill."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "template")
    lib.delete_skill(skill.id)
    assert lib.get_skill(skill.id) is None


def test_rejected_patterns(tmp_project: Path):
    """Test rejected patterns tracking."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "template")
    lib.record_failure(skill.id, "bad pattern")
    patterns = lib.get_rejected_patterns()
    assert "bad pattern" in patterns


def test_persistence(tmp_project: Path):
    """Test skills persist across instances."""
    lib1 = SkillLibrary(tmp_project)
    skill = lib1.create_skill("test", "Test skill", "template")
    lib2 = SkillLibrary(tmp_project)
    assert lib2.get_skill(skill.id) is not None


def test_prune(tmp_project: Path):
    """Test pruning old skills."""
    lib = SkillLibrary(tmp_project)
    skill = lib.create_skill("test", "Test skill", "template")
    # Non-crystallized, no uses — should be pruned
    pruned = lib.prune(min_uses=3, min_age_days=0)
    assert pruned == 1
