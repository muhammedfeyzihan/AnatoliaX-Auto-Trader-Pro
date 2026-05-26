"""
agent_router.py — OpenClaw-compatible multi-agent routing.

Routes incoming messages/channels to the correct AnatoliaX agent.
Mirrors OpenClaw's per-agent session and workspace isolation.

Usage:
    router = OpenClawRouter()
    router.register_agent("signal", SignalAgent())
    router.register_agent("risk", RiskAgent())
    result = router.route(channel="telegram", intent="signal", payload={"symbol": "THYAO"})
"""

from typing import Callable, Dict, Any


class OpenClawRouter:
    """
    Multi-agent router.
    Each agent is isolated; channels map to agent IDs.
    """

    def __init__(self):
        self._agents: Dict[str, Callable] = {}
        self._channel_map: Dict[str, str] = {}

    def register_agent(self, agent_id: str, handler: Callable):
        """Register an agent handler function."""
        self._agents[agent_id] = handler

    def map_channel(self, channel: str, agent_id: str):
        """Map a channel (telegram, discord, etc.) to an agent."""
        self._channel_map[channel] = agent_id

    def route(self, channel: str, intent: str, payload: Dict[str, Any]) -> dict:
        """Route a request to the appropriate agent."""
        agent_id = self._channel_map.get(channel, intent)
        handler = self._agents.get(agent_id)
        if handler is None:
            return {
                "ok": False,
                "error": f"No agent registered for '{agent_id}'",
                "agent": agent_id,
                "channel": channel,
            }
        try:
            result = handler(payload)
            return {"ok": True, "result": result, "agent": agent_id, "channel": channel}
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "agent": agent_id,
                "channel": channel,
            }

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def list_channels(self) -> dict:
        return self._channel_map.copy()
