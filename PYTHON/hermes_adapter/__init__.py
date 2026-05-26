"""
AnatoliaX Hermes Adapter — Pre-AI technical analysis filter + risk gates.

Inspired by hermes-trader's zero-cost TA gating pattern:
- Multi-timeframe indicators run locally (no LLM cost).
- Only CONFIRMED setups (score >= threshold) proceed to AI analysis.
- 10 independent risk gates block invalid orders before execution.

Usage:
    from hermes_adapter.ta_filter import TAFPreFilter
    from hermes_adapter.risk_gates import RiskGateEngine

    gate = TAFPreFilter(threshold=65)
    result = gate.evaluate(symbol="THYAO", timeframes=["1h","4h","1d"])
    if result.confirmed:
        ai_analysis(...)   # saves 80% token cost vs naive approach
"""
