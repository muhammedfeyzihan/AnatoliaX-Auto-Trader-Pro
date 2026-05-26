# AnatoliaX Trading System

**BIST (Istanbul Borsasi) icin profesyonel, cok ajanli AI trading sistemi.**

| | |
|---|---|
| **Versiyon** | 3.3 |
| **Tarih** | 2026-05-22 |
| **Ajanlar** | 3 (Sinyal / Risk / Strateji) + Telegram |
| **Test** | 1001+ test, %80+ coverage |
| **Lisans** | MIT |

---

## Sistem Ozeti

AnatoliaX, BIST 30/50/100 hisseleri icin gelistirilmis event-driven, cok ajanli bir trading sistemidir.

- **Sinyal Ajan** — Teknik analiz, haber, makro veri birlestirerek aday hisse uretir.
- **Risk Ajan** — Portfoy limitleri, Kelly, R:R, korelasyon, makro rejim kontrolu yapar.
- **Strateji Ajan** — 3/3 onay mekanizmasiyla nihai karari verir.
- **Telegram Bot** — Canli raporlama, sinyal bildirimleri, portfoy ozeti.

**HFT Modulu** (v3.1) — 1-dakika ve 1-saniye momentum yakalama, tick-level backtest, latency tracking.

**Gold Mining Stratejisi** (v3.2) — Kademeli tier sistemi: MS -> S1 -> M1 -> M5 -> M15 -> H1 -> D1. Otomatik tier gecisi, fallback, ve 7 zaman dilimli profesyonel scalping.

**Nautilus Trader Entegrasyonu** (v3.1, opsiyonel) — Event-driven MessageBus, PreTradeRiskEngine, FillModel, InstrumentProvider patternleri.

**Enterprise Modulleri** (v3.2) — BIST regülasyon uyumlulugu, davranissal finans kontrolleri, BIST ozel slippage, gercekci maliyet simulasyonu, OOS validasyon, temel analiz filtresi, piyasa mikro yapisi, CVaR ensemble optimizasyonu, online learning, paper/live ayrimi, ileri trade analitikleri, gelismis pozisyon olcekleme.

**Haftalik Strateji Konseyi** (v3.2) — Her cumartesi 3 ajan bir araya gelip gecen haftayi analiz eder: kazanc/zarar, en iyi setup, zaman dilimi, rejim tespiti. Matematiksel hedef carpani (1x->2x->4x->8x), 3/3 onay mekanizmasi, risk ayarlamalari ile yeni haftanin stratejisi belirlenir.

**Uretim Seviyesi Modulleri** (v3.3) — 20 kritik production-grade modul: Merkezi risk motoru (UnifiedRiskEngine), birlesik strateji kosucu (backtest/paper/live tek kod tabani), async event bus, pozisyon yasam dongusu yoneticisi (partial TP, trailing stop, pyramiding), kripto borsa adapteri (Binance/Bybit/OKX), saglam emir yoneticisi (retry + stale recovery), strateji kayit defteri (dinamik yukleme), walk-forward optimizasyon, kalici ajan hafizasi (SQLite + ChromaDB), AI rejim detektoru (bull/bear/sideways/volatile/low_vol), gozlemlenebilirlik dashboardu (Grafana export), deterministik replay motoru, sifreli secret yonetimi (Fernet + XOR fallback), hassasiyetli latency export, portfoy orkestrasyonu (momentum * sharpe / vol), Monte Carlo risk wrapper (VaR-95, CVaR-95), crash recovery (JSON checkpoint), feature store, aciklanabilir AI (SHAP-benzeri), Dockerized CI/CD pipeline.

**Maksimum Optimizasyon** (v3.3-opt) — Hizli cache (LRU + WAL SQLite), asenkron paralel veri cekme (asyncio.gather), vektorize backtest motoru (numpy, ~60x hizli), paralel sinyal tarayici (ThreadPoolExecutor), hizli tick depolama (buffered batch inserts + WAL), lazy indicator computation, vektorize Monte Carlo.

---

## Mimari

```
Veri Kaynaklari (Yahoo, TradingView, Bigpara, KAP)
         |
    FeedAggregator
         |
    +----+----+----+
    |    |    |    |
 Sinyal Risk Makro Haber
    |    |    |    |
    +----+----+----+
         |
    Strateji Ajan (3/3 onay)
         |
    +----+----+
    |         |
 Paper     Canli Emir
 Trading   (Broker API)
    |
 SQLite / PostgreSQL
```

---

## Kritik Kurallar (K1-K237)

- **K91** — TradingView birincil, Bigpara ikincil, biquote yardimci.
- **K92** — "Yalan asla yok." Her fiyat yani kaynak ve zaman damgasi.
- **K94** — Max pozisyon/hisse %2, gunluk max kayip %3, R:R min 1:2.
- **K141** — Piyasa kapali = islem yok. `BISTCalendar` kontrolu zorunlu.
- **K143** — Emir validasyonu zorunlu (`OrderValidator`).
- **K142-K148** — BIST regülasyon uyumlulugu (VBTS, devre kesici, short selling yasak).
- **K149-K154** — Davranissal finans kontrolleri (FOMO, loss aversion, cooldown).
- **K155-K158** — BIST ozel slippage modeli.
- **K159-K162** — OOS validasyon (walk-forward, overfitting tespiti).
- **K163-K166** — Temel analiz filtresi (P/E, P/B, KAP olaylari).
- **K167-K170** — Piyasa mikro yapisi (order book, market impact, VWAP).
- **K171-K174** — Ensemble optimizasyonu (CVaR, korelasyon, rejim agirliklari).
- **K175-K178** — Online learning ve concept drift.
- **K179-K183** — Paper/live ayrimi ve Execution Quality Score.
- **K184-K188** — Ileri trade analitikleri (Calmar, Omega, streak analysis).
- **K189-K192** — Gercekci maliyet simulasyonu (BIST, Takasbank, brokerage).
- **K193-K196** — Gelismis pozisyon olcekleme (Kelly, Optimal f, vol targeting).
- **K197-K203** — Haftalik Strateji Konseyi (cumartesi toplanti, hedef carpani, 3/3 onay, gecmis tecrube birlestirme).
- **K204-K237** — Uretim seviyesi modulleri (risk motoru, async event bus, pozisyon yasam dongusu, exchange adapter, emir yoneticisi, strateji kayit defteri, walk-forward optimizasyon, kalici ajan hafizasi, AI rejim detektoru, gozlemlenebilirlik dashboardu, deterministik replay, sifreli secret yonetimi, latency export, portfoy orkestrasyonu, Monte Carlo risk, crash recovery, feature store, aciklanabilir AI, CI/CD).
- **K238-K242** — Maksimum optimizasyon (hizli cache, asenkron paralel fetch, vektorize backtest, paralel tarayici, hizli tick depolama).
- **K243-K245** — Manipülasyon fallback ve çoklu piyasa geçisi (manipülasyon tespiti sonrasi BIST -> Kripto -> Forex otomatik geçis, dinamik sembol rotasyonu).
- **K95** — Parameter Registry: Regime-adaptive sinyal agirliklari, esikler, ATR multipliers, Kelly varsayimlari, macro/news penalty'ler. `ParameterRegistry.get_signal_config(regime, symbol)` ile dinamik parametre uzayi.
- **K246-K248** — Zaman bazli trading pencereleri ve uyari sistemi (8 pencere, dinamik risk carpani, EOD pozisyon kapatma, ogle arasi kacinma).

Tum kurallar: `KURALLAR/` dizini.

---

## Kurulum

### Gereksinimler
- Python 3.11+
- Node.js 18+ (opsiyonel)
- PostgreSQL 15+ (opsiyonel, SQLite fallback)
- Docker & Docker Compose (opsiyonel)

### Python
```bash
cd PYTHON
pip install -r requirements.txt
```

### Docker
```bash
docker-compose up -d
```

### Veritabani
```bash
python PYTHON/main.py --init-db
```

---

## Kullanim

### Sinyal Tarama
```bash
python PYTHON/main.py --scan THYAO,GARAN,ASELS
python PYTHON/main.py --scan-all
```

### Backtest
```bash
python PYTHON/main.py --backtest data/THYAO.csv --symbol THYAO
# Regime-adaptive backtest (K95)
python PYTHON/main.py --backtest data/THYAO.csv --symbol THYAO --regime bull
python PYTHON/main.py --backtest data/THYAO.csv --symbol THYAO --regime bear
```

### Portfoy Monitörü
```bash
python PYTHON/main.py --monitor
```

### HFT Backtest
```bash
python PYTHON/main.py --hft-backtest data/ticks.csv --hft-strategy m1_momentum
```

### HFT Canli Sinyal (Demo)
```bash
python PYTHON/main.py --hft-live THYAO,GARAN,ASELS
```

### Gold Mining Kademeli Strateji
```bash
python PYTHON/main.py --gold-mining
python PYTHON/main.py --gold-scan THYAO,GARAN,ASELS --gold-tier M1 --gold-capital 50000
```

### Yeni Enterprise Modülleri
```bash
# BIST regülasyon kontrolü
python -c "from PYTHON.risk.bist_regulations import BISTRegulatoryChecker; print(BISTRegulatoryChecker().validate_trade(symbol='THYAO', price=105, reference_price=100, index_level=10000, index_previous_close=10000, orders_today=30, trades_today=10, position_value=100000, cash=25000, side='BUY'))"

# Davranissal finans kontrolü
python -c "from PYTHON.risk.behavioral_finance import BehavioralFinanceGuard; print(BehavioralFinanceGuard().can_trade({}))"

# Temel analiz filtresi
python -c "from PYTHON.analytics.fundamental_filter import FundamentalFilter, FundamentalData; f=FundamentalFilter(); f.set_sector_benchmark('BANKA', pe=8, pb=1, ev_ebitda=6); print(f.score(FundamentalData('GARAN','BANKA',pe=7,pb=0.9,ev_ebitda=5,net_profit_growth_3y=0.1)))"

# Ensemble CVaR optimizasyonu
python -c "from PYTHON.strategy.ensemble_optimizer import EnsembleOptimizer; import pandas as pd, numpy as np; opt=EnsembleOptimizer(); df=pd.DataFrame({'a':np.random.normal(0.001,0.02,100),'b':np.random.normal(0.001,0.02,100)}); print(opt.cvar_optimize(df))"

# Paper/Live reconciliation
python -c "from PYTHON.execution.paper_live_separator import PaperLiveSeparator; sep=PaperLiveSeparator(); sep.run_paper({'symbol':'THYAO','side':'BUY','size':10,'price':100}); sep.run_live({'symbol':'THYAO','side':'BUY','size':10,'price':100}, filled_price=100.2, latency_ms=50); print(sep.reconcile())"

# OOS Walk-Forward validasyon
python -c "from PYTHON.backtest.oos_validator import OOSValidator; import pandas as pd, numpy as np; val=OOSValidator(); df=pd.DataFrame({'close':100+np.cumsum(np.random.randn(200)*0.5),'high':101+np.cumsum(np.random.randn(200)*0.5),'low':99+np.cumsum(np.random.randn(200)*0.5)}); print(val.regime_split_backtest(df, lambda d: {'sharpe':0.5}))"
```

### Uretim Seviyesi Modülleri (v3.3)
```bash
# Merkezi risk motoru
python -c "from PYTHON.risk.unified_risk_engine import UnifiedRiskEngine; e=UnifiedRiskEngine(capital=100000); e.update_capital(100000); print(e.check({'symbol':'THYAO','side':'BUY','size':100,'price':95,'sl':90}))"

# Birlesik strateji kosucu (backtest modu)
python -c "from PYTHON.execution.unified_strategy_runner import UnifiedStrategyRunner, ExecutionMode, ExecutionContext; r=UnifiedStrategyRunner(); ctx=ExecutionContext(mode=ExecutionMode.BACKTEST, capital=100000); def strat(c,p): return {'symbol':'THYAO','side':'BUY','size':10,'price':100,'sl':95}; print(r.run(ctx, strat, {}))"

# Async Event Bus
python -c "import asyncio; from PYTHON.common.async_event_bus import AsyncEventBus; bus=AsyncEventBus(); asyncio.run(bus.publish('test', {'x':1})); asyncio.run(bus.wait_until_empty()); print(bus.get_stats())"

# Pozisyon yasam dongusu
python -c "from PYTHON.execution.position_lifecycle import PositionLifecycleManager; m=PositionLifecycleManager(); m.open_position('THYAO', 100, 10, sl=95); m.update_price(106); print(m.get_stage())"

# Kripto borsa adapteri (mock)
python -c "from PYTHON.adapters.exchange_adapter import ExchangeAdapter; a=ExchangeAdapter('binance'); print(a.get_ticker('BTCUSDT'))"

# Saglam emir yoneticisi
python -c "from PYTHON.execution.order_manager_v2 import OrderManagerV2; o=OrderManagerV2(); print(o.submit({'symbol':'THYAO','side':'BUY','size':10,'price':100}, current_price=100))"

# Strateji kayit defteri (dinamik yukleme)
python -c "from PYTHON.strategy.strategy_registry import StrategyRegistry; r=StrategyRegistry(); print(r.list_strategies())"

# Walk-forward optimizasyon
python -c "from PYTHON.backtest.walk_forward_optimizer import WalkForwardOptimizer; import pandas as pd, numpy as np; w=WalkForwardOptimizer(); df=pd.DataFrame({'close':100+np.cumsum(np.random.randn(200)*0.5),'high':101+np.cumsum(np.random.randn(200)*0.5),'low':99+np.cumsum(np.random.randn(200)*0.5)}); print(w.optimize(df, lambda d,p: {'sharpe':0.5}, {'lookback':[10,20]}))"

# Kalici ajan hafizasi
python -c "from PYTHON.agents.persistent_memory import PersistentAgentMemory; m=PersistentAgentMemory(); m.store('Sinyal', 'THYAO al', {'confidence':0.8}); print(m.search('THYAO'))"

# AI rejim detektoru
python -c "from PYTHON.agents.ai_regime_detector import AIRegimeDetector; import pandas as pd, numpy as np; d=AIRegimeDetector(); close=100+np.linspace(0,200,100)+30*np.sin(np.linspace(0,4*np.pi,100)); df=pd.DataFrame({'close':close,'high':close+1,'low':close-1}); print(d.predict(df))"

# Gozlemlenebilirlik dashboardu
python -c "from PYTHON.observability.dashboard import ObservabilityDashboard; d=ObservabilityDashboard(); print(d.export_grafana())"

# Deterministik replay motoru
python -c "from PYTHON.backtest.replay_engine import DeterministicReplayEngine; import pandas as pd, numpy as np; e=DeterministicReplayEngine(); df=pd.DataFrame({'price':100+np.cumsum(np.random.randn(50)*0.5)}); e.load_df(df); print(e.step())"

# Sifreli secret yonetimi
python -c "import os; os.environ['MASTER_KEY']='test-key-32-bytes-long!!!!!'; from PYTHON.risk.encrypted_secrets import EncryptedSecretManager; s=EncryptedSecretManager(); s.set('API_KEY','secret123'); print(s.get('API_KEY'))"

# Hassasiyetli latency export
python -c "from PYTHON.execution.latency_precision import LatencyPrecisionExport; l=LatencyPrecisionExport(); print(l.export_json())"

# Portfoy orkestrasyonu
python -c "from PYTHON.strategy.portfolio_orchestrator import PortfolioOrchestrator; p=PortfolioOrchestrator(total_capital=100000); print(p.allocate([{'name':'trend','sharpe':1.5,'recent_pnl':5000,'volatility':0.15},{'name':'mean_rev','sharpe':0.8,'recent_pnl':2000,'volatility':0.10}]))"

# Monte Carlo risk wrapper
python -c "from PYTHON.backtest.monte_carlo_risk import MonteCarloRiskWrapper; import numpy as np; m=MonteCarloRiskWrapper(); print(m.analyze(np.random.normal(0.001,0.02,200)))"

# Crash recovery
python -c "from PYTHON.execution.crash_recovery import CrashRecoveryManager; c=CrashRecoveryManager(); c.checkpoint({'positions':[{'symbol':'THYAO','size':10}]}, tag='pre_market'); print(c.list_checkpoints())"

# Feature store
python -c "from PYTHON.agents.feature_store import FeatureStore; f=FeatureStore(); f.store('THYAO','rsi',65.5); print(f.get_latest('THYAO','rsi'))"

# Aciklanabilir AI
python -c "from PYTHON.agents.explainable_ai import ExplainableAI; e=ExplainableAI(); print(e.explain_trade({'rsi':65,'ema20':150,'volume_ratio':2.5}, 'BUY'))"
```

### Maksimum Optimizasyon (v3.3-opt)
```bash
# Paralel sinyal taramasi
python PYTHON/main.py --parallel-scan THYAO,GARAN,ASELS,ISCTR,AKBNK --workers 8

# Vektorize backtest
python PYTHON/main.py --backtest data/THYAO.csv --symbol THYAO --vectorized-backtest

# Hizli cache kullanimi
python -c "from PYTHON.optimization.fast_cache import FastCacheManager; c=FastCacheManager(); c.set('THYAO','1d',None); print(c.stats())"

# Paralel scanner
python -c "from PYTHON.optimization.parallel_scanner import ParallelScanner; s=ParallelScanner(max_workers=4); print(s.run_scan(['THYAO','GARAN']))"

# Vektorize backtest
python -c "from PYTHON.optimization.vectorized_backtest import VectorizedBacktestEngine; import pandas as pd, numpy as np; df=pd.DataFrame({'close':100+np.cumsum(np.random.randn(200)*0.5),'volume':np.random.randint(1000,10000,200)}); df.index=pd.date_range('2026-01-01',periods=200,freq='h'); df['Signal']=0; df.loc[df.index[10:20],'Signal']=2; print(VectorizedBacktestEngine(df).run()['metrics']['_summary'])"

# Hizli tick store
python -c "from PYTHON.optimization.batch_tick_store import BatchTickStore; t=BatchTickStore(batch_size=100); t.start(); t.insert_tick('THYAO',__import__('datetime').datetime.now(__import__('datetime').timezone.utc),100.0,1000); t.stop(); print(t.stats())"

# Manipülasyon fallback (BIST -> Kripto -> Forex)
python PYTHON/main.py --fallback-scan THYAO,GARAN,ASELS --enable-crypto-fallback

# Dinamik sembol rotasyonu
python PYTHON/main.py --auto-rotate-scan THYAO,GARAN,ASELS

# Fallback motoru dogrudan
python -c "from PYTHON.execution.manipulation_fallback import ManipulationFallbackRouter; r=ManipulationFallbackRouter(); r.blacklist_symbol('THYAO'); print(r.fallback('THYAO'))"

# Dinamik rotator dogrudan
python -c "from PYTHON.strategy.dynamic_symbol_rotator import DynamicSymbolRotator; rot=DynamicSymbolRotator(); rot.record_rotation('THYAO','GARAN','Test'); print(rot.get_rotation_history())"
```

### Zaman Bazli Trading (K246-K248)
```bash
# Aktif zaman penceresi ve trading durumu
python PYTHON/main.py --time-check

# Detayli zaman ozeti
python PYTHON/main.py --time-summary

# Dogrudan Python
python -c "from PYTHON.common.time_rules import TimeBasedTradingManager; tm=TimeBasedTradingManager(); print(tm.get_summary())"

# Optimal trading onerisi
python -c "from PYTHON.common.time_rules import TimeBasedTradingManager; tm=TimeBasedTradingManager(); s=tm.suggest_optimal_trading_time(); print(s)"

# Uyari kontrolu
python -c "from PYTHON.common.time_rules import TimeBasedTradingManager; tm=TimeBasedTradingManager(); alerts=tm.check_and_alert(); print([a.message for a in alerts])"
```

---

## Test

```bash
cd PYTHON
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
```

**Mevcut:** 1054+ test, %80+ coverage.

---

## Guvenlik

- **Asla** API key/token kodda yazmayin — `.env` kullanin.
- `risk/secret_manager.py` ile maskeleme ve validasyon.
- `risk/encrypted_secrets.py` ile Fernet sifreleme (fallback XOR+base64) ve TTL rotation.
- gRPC TLS opsiyonel (`GRPC_TLS_CERT`, `GRPC_TLS_KEY`).
- Cache SHA-256 + pickle (ic veri, dis kaynaktan gelmez).

---

## Dosya Yapisi

```
AnatoliaX-Trading-System/
├── LICENSE
├── README.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI/CD pipeline (K223)
├── PYTHON/
│   ├── main.py                    # CLI orchestrator
│   ├── requirements.txt
│   ├── backtest/                  # Vektorize + event-driven backtest + OOS + microstructure + replay + Monte Carlo + walk-forward
│   ├── paper_trading/             # Paper broker + signal engine
│   ├── hft/                       # HFT modulu (tick-level)
│   ├── data/                      # Fetcher, catalog, instrument provider
│   ├── risk/                      # Position, Account, PreTradeRiskEngine, BIST regs, behavioral, sizing, unified risk engine, encrypted secrets
│   ├── execution/                 # UnifiedExecutionEngine, order types, paper/live separator, unified strategy runner, position lifecycle, order manager v2, crash recovery, latency precision, manipulation fallback
│   ├── agents/                    # Orchestrator, Q-learning memory, adaptive learning, persistent memory, AI regime detector, explainable AI, feature store
│   ├── analytics/                 # Volume anomaly, BB+volume combo, fundamental filter, market microstructure, trade analytics
│   ├── telegram/                  # Reporter bot
│   ├── observability/             # JSON logging, Prometheus metrics, Grafana dashboard export
│   ├── anatoliax_grpc/            # gRPC server/client
│   ├── adapters/                  # NautilusAdapter (opsiyonel), ExchangeAdapter (Binance/Bybit/OKX)
│   ├── common/                    # MessageBus, events, validators, AsyncEventBus
│   ├── optimization/              # Fast cache, async feed, vectorized backtest, parallel scanner, batch tick store
│   └── tests/                     # 982+ pytest
├── SCRIPTS/                       # Node.js motor (legacy/opsiyonel)
├── KURALLAR/                      # K1-K245 kurallar
├── AJANLAR/                       # Ajan kurallari
├── STRATEJILER/                   # Strateji dokumanlari
└── CONFIG/                        # Yapilandirma
```

---

## Katkida Bulunma

1. Fork yapin
2. Feature branch olusturun (`git checkout -b feature/xyz`)
3. Testleri calistirin (`pytest tests/`)
4. Pull Request acin

---

## Sorumluluk Reddi

Bu sistem **egitim ve arastirma** amaclidir.
- Gercek para ile kullanmadan once paper trade yapin.
- Finansal tavsiye degildir.
- Tum risk kullaniciya aittir.

---

**AnatoliaX Trading System**  
*Sadakat. Guven. Kusursuzluk.*
