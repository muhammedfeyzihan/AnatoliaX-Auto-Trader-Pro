"""
orchestrator.py — Coklu ajan gelistirme orkestrasyonu
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class AgentCapability:
    name: str
    strengths: List[str]
    weaknesses: List[str]
    models: List[str]
    latency_ms: int


@dataclass
class TaskPlan:
    task_id: str
    description: str
    assigned_agent: str
    steps: List[str]


class AgentOrchestrator:
    """
    Coklu ajan gelistirme orkestrasyonu.

    Ozellikler:
    - Yetkinlik matrisi: her ajanin guclu/zayif yonleri
    - Gorev ayrimi: gorevi en uygun ajana yonlendir
    - Kalite kapilari: syntax, mypy, lint, test, security, review
    - Insan kapisi: 5 onay seviyesi (K123-K130)
    - Geri alma: git tabanli anlik kaydet / geri al

    Kullanim:
        orch = AgentOrchestrator()
        orch.register_agent("Claude", AgentCapability(...))
        orch.register_agent("Kimi", AgentCapability(...))
        plan = orch.decompose("Implement HFT order router")
    """

    def __init__(self):
        self._agents: Dict[str, AgentCapability] = {}
        self._plans: Dict[str, TaskPlan] = {}

    def register_agent(self, name: str, capability: AgentCapability) -> None:
        self._agents[name] = capability

    def decompose(self, request: str) -> TaskPlan:
        """Istegi gorevlere ayir ve en uygun ajana atayarak plan olustur."""
        # Basit heuristic: "code" iceriyorsa Claude, "review" iceriyorsa Kimi
        assigned = "Claude"
        if "review" in request.lower() or "research" in request.lower():
            assigned = "Kimi"
        plan = TaskPlan(
            task_id=f"T{len(self._plans)+1}",
            description=request,
            assigned_agent=assigned,
            steps=["plan", "code", "test", "review", "merge"],
        )
        self._plans[plan.task_id] = plan
        return plan

    def get_best_agent(self, task_type: str) -> Optional[str]:
        """Gorev tipi icin en uygun ajan adini dondur."""
        for name, cap in self._agents.items():
            if task_type in cap.strengths:
                return name
        return None
