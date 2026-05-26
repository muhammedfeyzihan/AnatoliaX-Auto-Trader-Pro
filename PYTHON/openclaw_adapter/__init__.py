"""
AnatoliaX OpenClaw Adapter — Multi-agent routing + skill loader.

OpenClaw (https://github.com/openclaw/openclaw) is a local-first
AI assistant framework. This adapter exposes AnatoliaX agents as
OpenClaw-compatible skills and routes incoming requests.

Usage:
    from openclaw_adapter.agent_router import OpenClawRouter
    router = OpenClawRouter()
    router.register_agent("signal", signal_agent)
    response = router.route(channel="telegram", message="Sinyal THYAO")
"""
