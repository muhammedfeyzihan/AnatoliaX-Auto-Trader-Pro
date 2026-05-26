# Claude ↔ Kimi Automation

**Versiyon:** 1.0.0 | **Modul:** `.agents/`

## Ozet

Coklu ajan gelistirme orkestrasyonu: Claude (kod/kodlama) ve Kimi (inceleme/arastirma) isbirligi.

## Bilesenler

- `orchestrator.py` — Yetkinlik matrisi, gorev ayrimi
- `claude_bridge.py` — Claude Code CLI sarmalayici
- `kimi_bridge.py` — Kimi API istemcisi
- `shared_memory.py` — SQLite + ChromaDB paylasimli bellek
- `task_queue.py` — SQLite gorev kuyrugu
- `quality_gates.py` — Syntax, mypy, lint, test, security, review
- `human_gate.py` — 5 seviyeli insan onayi
- `rollback_system.py` — Git tabanli geri alma
- `config/` — Yapilandirma sablonlari

## Kullanim

```python
from .agents.orchestrator import AgentOrchestrator
orch = AgentOrchestrator()
plan = orch.decompose("Implement GPU scheduler")
print(plan.assigned_agent, plan.steps)
```
