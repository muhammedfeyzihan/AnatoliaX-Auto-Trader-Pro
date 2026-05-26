"""
orchestrator.py — Agent orchestration, planner/executor ayrimi, tool routing
"""
import json
import time
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AgentTask:
    id: str
    agent: str
    action: str
    params: dict = field(default_factory=dict)
    status: str = "pending"
    result: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None


class AgentOrchestrator:
    """
    Ajan orkestrasyonu v3.0:
    - 3 Ajan pipeline: Sinyal -> Risk -> Strateji
    - Enhancement module integration (Phase 1-5)
    - Geri bildirim: basari/basarisizlik kaydet
    """

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._tasks: List[AgentTask] = []
        self._feedback: Dict[str, List[dict]] = {}
        self._scoreboard: Dict[str, dict] = {}
        # Enhancement module references (wired externally)
        self._enhancements: Dict[str, Any] = {}

    def register_tool(self, agent: str, tool: Callable):
        self._tools[agent] = tool

    def attach_module(self, name: str, module: Any):
        """Wire an enhancement module into the orchestrator."""
        self._enhancements[name] = module

    def plan(self, symbol: str, context: dict) -> List[AgentTask]:
        """v3.0 3-agent pipeline planlama."""
        plan = [
            AgentTask(id=f"{symbol}_SINYAL", agent="Sinyal", action="analyze", params={"symbol": symbol, "context": context}),
            AgentTask(id=f"{symbol}_RISK", agent="Risk", action="check", params={"symbol": symbol, "context": context}),
            AgentTask(id=f"{symbol}_STRATEJI", agent="Strateji", action="decide", params={"symbol": symbol, "context": context}),
        ]
        self._tasks.extend(plan)
        return plan

    def execute(self, task: AgentTask) -> dict:
        """Tek bir gorevi calistir."""
        tool = self._tools.get(task.agent)
        if not tool:
            task.status = "error"
            task.result = {"error": f"Tool not found for agent {task.agent}"}
            return task.result

        try:
            task.status = "running"
            result = tool(task.params)
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            self._record_feedback(task, success=True)
        except Exception as e:
            task.status = "error"
            task.result = {"error": str(e)}
            self._record_feedback(task, success=False)
        return task.result

    def run_all(self, symbol: str, context: dict) -> dict:
        """v3.0 pipeline: Sinyal -> Risk -> Strateji -> Karar."""
        plan = self.plan(symbol, context)
        signal_task = next((t for t in plan if t.agent == "Sinyal"), None)
        risk_task = next((t for t in plan if t.agent == "Risk"), None)
        strategy_task = next((t for t in plan if t.agent == "Strateji"), None)

        signal_result = self.execute(signal_task) if signal_task else {}
        risk_result = self.execute(risk_task) if risk_task else {}
        strategy_result = self.execute(strategy_task) if strategy_task else {}

        # 3/3 onay: Sinyal ve Risk RED ise Strateji karar vermez
        if signal_result.get("status") == "RED" or risk_result.get("status") == "RED":
            return {"status": "REJECTED", "reason": "Sinyal/Risk RED", "signal": signal_result, "risk": risk_result}

        return strategy_result if strategy_result else {"status": "NO_DECISION"}

    def run_with_enhancements(self, symbol: str, context: dict) -> dict:
        """v3.0 pipeline with Phase 1-5 enhancement modules pre-flight."""
        # Pre-flight: microstructure, order book, liquidity check
        preflight = {}
        if "microstructure" in self._enhancements:
            preflight["microstructure"] = self._enhancements["microstructure"]
        if "liquidity_collapse" in self._enhancements:
            preflight["liquidity"] = self._enhancements["liquidity_collapse"].calculate_lcs()
        if "toxic_flow" in self._enhancements:
            preflight["toxicity"] = self._enhancements["toxic_flow"]

        if preflight.get("liquidity", 0) > 0.7:
            return {"status": "REJECTED", "reason": "Liquidity collapse predicted", "preflight": preflight}

        result = self.run_all(symbol, context)
        result["preflight"] = preflight
        return result

    def _record_feedback(self, task: AgentTask, success: bool):
        if task.agent not in self._feedback:
            self._feedback[task.agent] = []
        self._feedback[task.agent].append({
            "task": task.action,
            "success": success,
            "time": datetime.now(timezone.utc).isoformat(),
        })
        # Scoreboard guncelle
        if task.agent not in self._scoreboard:
            self._scoreboard[task.agent] = {"total": 0, "success": 0}
        self._scoreboard[task.agent]["total"] += 1
        if success:
            self._scoreboard[task.agent]["success"] += 1

    def get_scoreboard(self) -> dict:
        return {
            agent: {
                "total": s["total"],
                "success": s["success"],
                "rate": round(s["success"] / s["total"], 3) if s["total"] > 0 else 0,
            }
            for agent, s in self._scoreboard.items()
        }

    def get_pending_tasks(self) -> List[AgentTask]:
        return [t for t in self._tasks if t.status == "pending"]

    def get_completed_tasks(self) -> List[AgentTask]:
        return [t for t in self._tasks if t.status in ("completed", "error")]
