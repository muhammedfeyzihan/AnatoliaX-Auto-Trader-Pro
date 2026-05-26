# AnatoliaX Mimari Dokümantasyonu

## Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  CLI (main) │  │  Dashboard  │  │  Telegram   │  │  REST API   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    gRPC Server (port 50051)                         │    │
│  │  - AnalyzeSymbol  - GetPortfolio  - SubmitOrder  - CheckRisk       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                 REST API Server (port 3001)                         │    │
│  │  /api/v1/health, /api/v1/signals, /api/v1/orders, /api/v1/metrics  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │              WebSocket Server (port 8080)                           │    │
│  │  Real-time signals, trades, portfolio updates                       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CORE BUSINESS LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Sinyal    │  │    Risk     │  │  Strateji   │  │  Execution  │        │
│  │   Ajanı     │  │    Ajanı    │  │    Ajanı    │  │   Engine    │        │
│  │             │  │             │  │             │  │             │        │
│  │ - Teknik    │  │ - Portfolio │  │ - 3/3 Onay  │  │ - Order Mgr │        │
│  │ - Haber     │  │ - Kelly     │  │ - Konsey    │  │ - Lifecycle │        │
│  │ - Makro     │  │ - VaR/CVaR  │  │ - Haftalık  │  │ - Retry     │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          EVENT BUS LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                  AsyncEventBus (Common Module)                      │    │
│  │  - Event publishing/subscribing                                     │    │
│  │  - Event types: SignalEvent, OrderEvent, RiskEvent, TradeEvent     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA LAYER                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Yahoo     │  │  Bigpara    │  │ TradingView │  │    KAP      │        │
│  │  Finance    │  │  (15dk)     │  │  (Scrape)   │  │  (Bildirim) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                    Feed Aggregator + Validator                      │    │
│  │  - Multi-source fusion  - Quality check  - Fallback chain          │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PERSISTENCE LAYER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  PostgreSQL │  │   SQLite    │  │  ChromaDB   │  │    Redis    │        │
│  │  (Trades)   │  │  (Signals)  │  │  (Memory)   │  │   (Cache)   │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       MONITORING LAYER                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ Prometheus  │  │   Grafana   │  │  JSON Logs  │  │  Alerting   │        │
│  │  (Metrics)  │  │ (Dashboard) │  │   (ELK)     │  │  (Telegram) │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Modül İlişkileri

### Python Modülleri

```
PYTHON/
├── main.py                    # CLI orchestrator
│
├── agents/                    # AI Ajanları
│   ├── orchestrator.py        # Ajan koordinasyonu
│   ├── ai_regime_detector.py  # Piyasa rejimi (bull/bear/sideways)
│   ├── persistent_memory.py   # SQLite + ChromaDB hafıza
│   ├── feature_store.py       # Feature storage
│   └── explainable_ai.py      # SHAP-benzeri açıklamalar
│
├── strategy/                  # Stratejiler
│   ├── strategy_registry.py   # Dinamik strateji yükleme
│   ├── portfolio_orchestrator.py  # Portföy tahsisi
│   ├── ensemble_optimizer.py  # CVaR ensemble optimizasyon
│   ├── parameter_registry.py  # Rejim-adaptif parametreler
│   └── gold_mining/           # Kademeli altın stratejisi
│
├── risk/                      # Risk Yönetimi
│   ├── unified_risk_engine.py # Merkezi risk motoru
│   ├── bist_regulations.py    # BIST regülasyon kontrolü
│   ├── behavioral_finance.py  # Davranışsal finans
│   ├── position_sizing.py     # Kelly, Optimal f
│   └── encrypted_secrets.py   # Fernet şifreleme
│
├── execution/                 # Emir Yönetimi
│   ├── unified_strategy_runner.py  # Backtest/paper/live
│   ├── order_manager_v2.py    # Retry + stale recovery
│   ├── position_lifecycle.py  # Partial TP, trailing stop
│   ├── manipulation_fallback.py # BIST -> Kripto fallback
│   └── crash_recovery.py      # JSON checkpoint
│
├── backtest/                  # Backtest Motoru
│   ├── engine.py              # Event-driven backtest
│   ├── walk_forward_optimizer.py  # Walk-forward optimizasyon
│   ├── monte_carlo_risk.py    # VaR-95, CVaR-95
│   ├── oos_validator.py       # Out-of-sample validasyon
│   └── replay_engine.py       # Deterministik replay
│
├── data/                      # Veri Katmanı
│   ├── feed_aggregator.py     # Çoklu kaynak fusion
│   ├── yahoo_fetcher.py       # Yahoo Finance
│   ├── kap_fetcher.py         # KAP bildirimleri
│   ├── macro_fetcher.py       # USD/TRY, DXY, VIX
│   └── tick_store.py          # Tick storage (WAL)
│
├── optimization/              # Performans Optimizasyonu
│   ├── fast_cache.py          # LRU + WAL SQLite
│   ├── vectorized_backtest.py # NumPy vektorize (~60x)
│   ├── parallel_scanner.py    # ThreadPoolExecutor
│   └── batch_tick_store.py    # Buffered inserts
│
├── adapters/                  # Dış Sistem Adaptörleri
│   ├── exchange_adapter.py    # Binance/Bybit/OKX
│   ├── nautilus_adapter.py    # Nautilus Trader
│   └── worldmonitor_bridge.py # Worldmonitor entegrasyonu
│
└── observability/             # Gözlemlenebilirlik
    ├── dashboard.py           # Grafana export
    ├── metrics.py             # Prometheus metrics
    └── audit_log.py           # Immutable audit log
```

---

## Veri Akışı

### Sinyal Üretimi

```
1. FeedAggregator.fetch(symbol)
   ├─> Yahoo Finance (primary)
   ├─> Bigpara (secondary, fallback)
   └─> TradingView (tertiary)

2. Sinyal Ajanı.analyze()
   ├─> Teknik analiz (EMA, RSI, MACD, BB)
   ├─> Hacim anomalisi (Z-score > 3)
   ├─> Haber analizi (NLP sentiment)
   └─> Makro rejim (USD/TRY, VIX, DXY)

3. Risk Ajanı.check()
   ├─> Pozisyon limiti (%2 max/hisse)
   ├─> Günlük kayıp (%3 max)
   ├─> R:R kontrolü (min 1:2)
   ├─> Korelasyon (< 0.80)
   └─> BIST regülasyon (VBTS, devre kesici)

4. Strateji Ajanı.decide()
   ├─> 3/3 onay mekanizması
   ├─> Haftalık konsey (Cumartesi)
   ├─> Hedef çarpanı (1x -> 2x -> 4x -> 8x)
   └─> Nihai karar (BUY/SELL/WAIT)

5. Execution Engine.execute()
   ├─> Order Manager (retry logic)
   ├─> Position Lifecycle (open -> manage -> close)
   └─> Crash Recovery (checkpoint)
```

---

## Event Schema

```python
# Signal Event
@dataclass
class SignalEvent:
    event_id: str
    timestamp: datetime
    symbol: str
    signal: str  # BUY, SELL, WAIT
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    regime: str  # bull, bear, sideways, volatile
    source: str  # technical, news, macro

# Order Event
@dataclass
class OrderEvent:
    event_id: str
    timestamp: datetime
    order_id: str
    symbol: str
    side: str  # BUY, SELL
    size: int
    price: float
    status: str  # PENDING, FILLED, CANCELLED, REJECTED
    latency_ms: int
    slippage_bps: float

# Risk Event
@dataclass
class RiskEvent:
    event_id: str
    timestamp: datetime
    risk_type: str  # POSITION_LIMIT, DAILY_LOSS, CIRCUIT_BREAKER
    symbol: str
    current_value: float
    threshold: float
    action: str  # BLOCK, WARN, ALLOW

# Trade Event
@dataclass
class TradeEvent:
    event_id: str
    timestamp: datetime
    trade_id: str
    symbol: str
    side: str
    size: int
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    holding_period: timedelta
```

---

## Deployment Mimarisi

### Kubernetes

```yaml
# 5 Deployment
- anatoliax-core         (2 replica, HPA: 2-6 pod)
- anatoliax-paper        (1 replica)
- anatoliax-telegram     (1 replica)
- anatoliax-execution    (1 replica)
- anatoliax-scheduler    (1 replica)

# 4 StatefulSet
- postgres (RDS)
- redis (ElastiCache)
- chromadb
- prometheus

# 1 Ingress
- anatoliax.example.com (TLS, cert-manager)
```

### Docker Compose (Local)

```yaml
# 9 Servis
- anatoliax-node
- anatoliax-python
- anatoliax-paper
- anatoliax-telegram
- anatoliax-execution
- anatoliax-scheduler
- postgres
- chromadb
- redis
```

---

## Güvenlik Mimarisi

```
┌─────────────────────────────────────────┐
│         API Gateway (Auth)              │
│  - JWT validation                       │
│  - Rate limiting                        │
│  - IP whitelist                         │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│      Encrypted Secrets (Fernet)         │
│  - Master key (env var)                 │
│  - TTL rotation (24h)                   │
│  - XOR fallback                         │
└─────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│       Audit Logging (Immutable)         │
│  - JSON structured                      │
│  - Trace ID                             │
│  - ELK ready                            │
└─────────────────────────────────────────┘
```

---

## Performans Metrikleri

| Metrik | Hedef | Mevcut |
|--------|-------|--------|
| Sinyal latency | < 100ms | ~45ms |
| Emir execution | < 500ms | ~200ms |
| Backtest (1 yıl) | < 10sn | ~8sn (vektörize) |
| Cache hit rate | > 80% | ~85% |
| Test coverage | > 80% | ~80% (1141 test) |
