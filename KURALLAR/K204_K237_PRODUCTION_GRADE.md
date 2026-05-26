# K204-K237 — Uretim Seviyesi (Production-Grade) Modul Kurallari

**Versiyon:** 3.3
**Tarih:** 2026-05-22
**Kapsam:** 20 kritik uretim modulu — risk, yurutme, AI, altyapi, guvenlik, CI/CD.

---

## K204 — Merkezi Risk Motoru (UnifiedRiskEngine)

Tek bir sinif (`UnifiedRiskEngine`) tum risk kontrollerini birlestirir:
- Kill Switch (gunluk max drawdown)
- Concurrent pozisyon limiti
- Single / total / sektor exposure limitleri
- Portfolio heat (risk per share * size / capital)
- Consecutive losses cooldown
- Drawdown-based position scaling (0.5x, 0.25x)
- Dynamic SL multiplier (tighter stops in high risk)

**Entegrasyon:** `PYTHON/risk/unified_risk_engine.py`

---

## K205 — Birlesik Strateji Kosucu (UnifiedStrategyRunner)

Ayni strateji kodu backtest, paper ve live'da kosar. `ExecutionContext` mode-aware doldurma, slippage/fee modelleri ile calisir.

**Entegrasyon:** `PYTHON/execution/unified_strategy_runner.py`

---

## K206 — Async Event Bus (AsyncEventBus)

Asenkron event bus: priority queue, backpressure (max_queue_size), async/sync handler destegi. Redis Stream opsiyonel.

**Entegrasyon:** `PYTHON/common/async_event_bus.py`

---

## K207 — Pozisyon Yasam Dongusu (PositionLifecycleManager)

Partial TP (3 kademe), breakeven SL cekme, trailing stop (EMA9 takip), pyramiding (max 2 eklem). Her asama `LifecycleStage` ile takip edilir.

**Entegrasyon:** `PYTHON/execution/position_lifecycle.py`

---

## K208 — Exchange Adapter (Binance/Bybit/OKX)

Birlesik kripto borsa adaptoru: ticker, balance, order, cancel. BIST icin sadece data feed modu. Mock fallback zorunlu.

**Entegrasyon:** `PYTHON/adapters/exchange_adapter.py`

---

## K209 — Saglam Emir Yoneticisi (OrderManagerV2)

Retry + exponential backoff, stale order recovery, slippage tolerance check, partial fill timeout, event callback destegi.

**Entegrasyon:** `PYTHON/execution/order_manager_v2.py`

---

## K210 — Strateji Kayit Defteri (StrategyRegistry)

Dinamik strateji yukleme/unloading: dosya yolundan, modulden, veya manuel kayit. Auto-discover `run/execute` metodu.

**Entegrasyon:** `PYTHON/strategy/strategy_registry.py`

---

## K211 — Walk-Forward Optimizasyon (WalkForwardOptimizer)

Rolling window parametre optimizasyonu: IS'de optimize, OOS'de validate. Degradation limiti (%20) ve min Sharpe (0.5) zorunlu.

**Entegrasyon:** `PYTHON/backtest/walk_forward_optimizer.py`

---

## K212 — Kalici Ajan Hafizasi (PersistentAgentMemory)

SQLite + ChromaDB birlesimi: per-agent decision storage, semantic search, TTL-based forgetting, category filtreleme.

**Entegrasyon:** `PYTHON/agents/persistent_memory.py`

---

## K213 — AI Rejim Detektoru (AIRegimeDetector)

ML-based piyasa rejimi: bull / bear / sideways / volatile / low_vol. Feature: trend, volatility, momentum. K-means clustering (sklearn fallback: pure-python).

**Entegrasyon:** `PYTHON/agents/ai_regime_detector.py`

---

## K214 — Gozlemlenebilirlik Dashboard (ObservabilityDashboard)

Grafana-compatible JSON export: P50/P95/P99 latency, daily PnL, active positions, kill switch status, win rate. `export_grafana()` ile JSON uretir.

**Entegrasyon:** `PYTHON/observability/dashboard.py`

---

## K215 — Deterministik Replay Motoru (DeterministicReplayEngine)

Tick-by-tick deterministik replay: ayni CSV/DF + seed = ayni sonuc. Handler callback, progress tracking, slice destegi.

**Entegrasyon:** `PYTHON/backtest/replay_engine.py`

---

## K216 — Sifreli Secret Yonetimi (EncryptedSecretManager)

Fernet sifreleme (fallback: XOR+base64). TTL rotation, silme, listeleme. `MASTER_KEY` env var zorunlu.

**Entegrasyon:** `PYTHON/risk/encrypted_secrets.py`

---

## K217 — Hassasiyetli Latency Export (LatencyPrecisionExport)

Millisecond precision JSON/CSV/Prometheus export. `LatencyMonitor` uzerine minor enhancement.

**Entegrasyon:** `PYTHON/execution/latency_precision.py`

---

## K218 — Portfoy Orkestrasyonu (PortfolioOrchestrator)

Dinamik sermaye dagilimi: momentum score * sharpe / vol. Min/max weight clamping, rebalance threshold. Risk-parity benzeri.

**Entegrasyon:** `PYTHON/strategy/portfolio_orchestrator.py`

---

## K219 — Monte Carlo Risk Wrapper (MonteCarloRiskWrapper)

Probabilistic risk: VaR-95, CVaR-95, prob_positive, prob_breach (%20 DD). Bootstrap sampling ile 10,000 simulasyon.

**Entegrasyon:** `PYTHON/backtest/monte_carlo_risk.py`

---

## K220 — Crash Recovery (CrashRecoveryManager)

JSON checkpoint + otomatik recovery. Max 10 checkpoint, interval 60 sn. Tag-based recover destegi.

**Entegrasyon:** `PYTHON/execution/crash_recovery.py`

---

## K221 — Feature Store (FeatureStore)

Shared SQLite tabanli feature store: symbol x feature_name x timestamp. Latest lookup, history, metadata destegi.

**Entegrasyon:** `PYTHON/agents/feature_store.py`

---

## K222 — Aciklanabilir AI (ExplainableAI)

SHAP-benzeri feature importance: impact = abs(value) * weight. Trade explanation + rejection explanation. Natural language summary.

**Entegrasyon:** `PYTHON/agents/explainable_ai.py`

---

## K223 — CI/CD Pipeline (GitHub Actions)

`.github/workflows/ci.yml` ile: pytest, lint, secret-scan, docker-build. Docker Compose + Dockerfile zorunlu.

**Entegrasyon:** `.github/workflows/ci.yml`

---

## K224-K237 Ozet Tablo

| Kural | Modul | Dosya | Kategori |
|-------|-------|-------|----------|
| K204 | UnifiedRiskEngine | `PYTHON/risk/unified_risk_engine.py` | Risk |
| K205 | UnifiedStrategyRunner | `PYTHON/execution/unified_strategy_runner.py` | Execution |
| K206 | AsyncEventBus | `PYTHON/common/async_event_bus.py` | Common |
| K207 | PositionLifecycleManager | `PYTHON/execution/position_lifecycle.py` | Execution |
| K208 | ExchangeAdapter | `PYTHON/adapters/exchange_adapter.py` | Adapter |
| K209 | OrderManagerV2 | `PYTHON/execution/order_manager_v2.py` | Execution |
| K210 | StrategyRegistry | `PYTHON/strategy/strategy_registry.py` | Strategy |
| K211 | WalkForwardOptimizer | `PYTHON/backtest/walk_forward_optimizer.py` | Backtest |
| K212 | PersistentAgentMemory | `PYTHON/agents/persistent_memory.py` | Agent |
| K213 | AIRegimeDetector | `PYTHON/agents/ai_regime_detector.py` | Agent |
| K214 | ObservabilityDashboard | `PYTHON/observability/dashboard.py` | Observability |
| K215 | DeterministicReplayEngine | `PYTHON/backtest/replay_engine.py` | Backtest |
| K216 | EncryptedSecretManager | `PYTHON/risk/encrypted_secrets.py` | Risk |
| K217 | LatencyPrecisionExport | `PYTHON/execution/latency_precision.py` | Execution |
| K218 | PortfolioOrchestrator | `PYTHON/strategy/portfolio_orchestrator.py` | Strategy |
| K219 | MonteCarloRiskWrapper | `PYTHON/backtest/monte_carlo_risk.py` | Backtest |
| K220 | CrashRecoveryManager | `PYTHON/execution/crash_recovery.py` | Execution |
| K221 | FeatureStore | `PYTHON/agents/feature_store.py` | Agent |
| K222 | ExplainableAI | `PYTHON/agents/explainable_ai.py` | Agent |
| K223 | CI/CD Pipeline | `.github/workflows/ci.yml` | DevOps |

---

## Test Hedefleri

- **Mevcut test:** 816 (v3.2)
- **Yeni test:** 153
- **Toplam:** 969+
- **Coverage:** %80+ korunur
- **Tum testler:** `pytest tests/ -v` 0 failure

---

*AnatoliaX Trading System v3.3 — Production Grade*
