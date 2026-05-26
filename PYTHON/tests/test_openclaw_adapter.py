"""
Test: openclaw_adapter (router + skill loader)
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from openclaw_adapter.agent_router import OpenClawRouter
from openclaw_adapter.skill_loader import SkillLoader, OpenClawSkill


class TestOpenClawRouter:
    def test_register_and_route(self):
        router = OpenClawRouter()
        router.register_agent("echo", lambda p: {"msg": p.get("text", "")})
        router.map_channel("telegram", "echo")
        result = router.route("telegram", "echo", {"text": "hello"})
        assert result["ok"] is True
        assert result["result"]["msg"] == "hello"

    def test_route_missing_agent(self):
        router = OpenClawRouter()
        result = router.route("unknown", "missing", {})
        assert result["ok"] is False
        assert "No agent registered" in result["error"]

    def test_list_agents(self):
        router = OpenClawRouter()
        router.register_agent("a", lambda x: x)
        router.register_agent("b", lambda x: x)
        assert sorted(router.list_agents()) == ["a", "b"]


class TestSkillLoader:
    def test_load_from_string(self):
        md = """
# Skill: signal_scan
## Setup
Scan BIST universe for signals.
## Parameters
- symbols: str = THYAO,GARAN
- interval: str = 1d
## Handler
paper_trading.signal_engine:SignalEngine.run_scan
"""
        loader = SkillLoader()
        skill = loader.load_from_string(md)
        assert skill is not None
        assert skill.name == "signal_scan"
        assert skill.handler == "paper_trading.signal_engine:SignalEngine.run_scan"
        assert "symbols" in skill.parameters
        assert skill.parameters["symbols"]["default"] == "THYAO,GARAN"

    def test_load_invalid(self):
        loader = SkillLoader()
        assert loader.load_from_string("") is None

    def test_discover_skills(self, tmp_path):
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("# Skill: test\n## Setup\nTest.\n## Handler\nhandler")
        loader = SkillLoader()
        skills = loader.discover_skills(skill_dir)
        assert len(skills) == 1
        assert skills[0].name == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
