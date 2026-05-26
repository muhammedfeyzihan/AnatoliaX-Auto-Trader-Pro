# AnatoliaX Trading System — Claude Context

> **Versiyon:** 3.0 | **Dil:** Türkçe (kod İngilizce) | **Platform:** Node.js + Python

## Proje Özeti

AnatoliaX, BIST 100 (İstanbul Borsası) için geliştirilmiş çok ajanlı (multi-agent) profesyonel AI trade sistemidir. 3 bağımsız AI ajanı (Sinyal, Risk, Strateji) çoklu yetkinlikleri birleştirerek çalışır ve **3/3 onay** mekanizmasıyla hisse önerir. Telegram ajanı canlı iletişim ve raporlama sağlar.

**Mimari:** Event-driven Node.js ana motor + Python analitik/backtest modülü.

---

## Kritik Kurallar (Asla İhlal Etme)

1. **Veri kaynağı hiyerarşisi (K91):** TradingView birincil → Bigpara ikincil (15dk gecikmeli) → biquote yardımcı.
2. **Canlı veri garantisi (K92):** "Yalan asla yok." Her fiyat yanında kaynak ve zaman damgası zorunlu.
3. **Risk limitleri:** Max pozisyon/hisse %2, günlük max kayıp %3, R:R min 1:2, korelasyon <0.80.
4. **Onay mekanizması:** 3/3 onay şartı. 1+ RED = hisse çıkar.
5. **Scalping alternatif:** Pozisyon trade'den bağımsız. Max SL %1.5, TP kademeli %1/%2/%3.
6. **Komisyon + BSMV:** Her işlemde %0.4 round-trip maliyet hesaplanmalı.
7. **Performans metrikleri (K114-K121):** 6/8 metrik geçmeden strateji onaylanmaz.

---

## Dosya Yapısı

```
AnatoliaX-Trading-System/
├── README.md                          # Proje dokümantasyonu
├── CLAUDE.md                          # Bu dosya (Claude context)
├── package.json                       # Node.js bağımlılıkları
├── .env.example                       # Çevre değişkenleri şablonu
├── Dockerfile / docker-compose.yml    # Docker altyapısı
├── PYTHON/                            # Python backtest & analitik
│   ├── requirements.txt
│   ├── main.py                        # Python CLI orchestrator
│   ├── backtest/
│   │   ├── engine.py                  # Vektörize backtest motoru
│   │   ├── indicators.py              # EMA, RSI, MACD, BB, VWAP, ATR
│   │   ├── signals.py                 # 5 setup tipi + kombinasyon skoru
│   │   ├── performance.py             # Sharpe, Sortino, Drawdown, Monte Carlo
│   │   ├── slippage.py               # Hacme bağlı slippage modeli
│   │   └── commission.py             # BIST komisyon + BSMV
│   ├── analytics/
│   │   ├── volume_anomaly.py         # Z-score > 3 hacim anomalisi
│   │   ├── bb_volume_combo.py       # BB squeeze + hacim patlaması
│   │   ├── kap_correlation.py       # KAP-fiyat korelasyonu
│   │   ├── error_analyzer.py        # Derinlemesine hata analizi
│   │   └── agent_scoring.py         # Ajan performans takibi
│   ├── data/
│   │   ├── yahoo_fetcher.py         # Yahoo Finance BIST verisi
│   │   ├── feed_aggregator.py       # Çoklu kaynak birleştirme
│   │   ├── cache_manager.py         # SQLite cache, TTL
│   │   ├── tick_store.py            # SQLite + Parquet + replay
│   │   ├── market_calendar.py       # BIST tatil takvimi
│   │   ├── websocket_client.py      # Heartbeat + auto-reconnect
│   │   ├── auto_validator.py        # TradingView doğrulama + SL/TP alarm
│   │   ├── kap_fetcher.py           # KAP.gov.tr bildirimleri
│   │   ├── macro_fetcher.py         # USD/TRY, DXY, VIX, altın, petrol, BIST100
│   │   └── news_fetcher.py          # Piyasa haberleri + Elon Musk tweetleri
│   ├── memory/
│   │   ├── chroma_store.py          # ChromaDB CRUD
│   │   ├── embedder.py              # sentence-transformers embedding
│   │   └── query.py                 # Benzer geçmiş analizleri
│   ├── risk/
│   │   ├── database.py              # SQLite/PostgreSQL
│   │   ├── models.py                # SQLAlchemy modelleri
│   │   ├── portfolio_monitor.py     # Canlı portföy takibi
│   │   ├── metrics.py               # K114-K121 metrikleri
│   │   ├── dashboard.py             # CLI tablo + HTML rapor
│   │   ├── kill_switch.py           # Max drawdown + circuit breaker
│   │   ├── exposure_limiter.py     # Tekli/toplam/sektör limiti
│   │   ├── volatility_throttle.py   # ATR bazlı pozisyon kısıtlama
│   │   ├── portfolio_heat.py        # Korelasyon + likidasyon mesafesi
│   │   └── secret_manager.py        # .env secret yönetimi + maskeleme
│   ├── execution/
│   │   ├── engine.py                # UnifiedExecutionEngine (backtest+live)
│   │   ├── order_manager.py         # Retry + backoff + partial fill
│   │   ├── reconnect.py             # WebSocketReconnectHandler + Failover
│   │   └── latency_monitor.py       # RTT P50/P95/P99 tracking
│   ├── observability/
│   │   ├── logger.py                # Structured JSON logging (ELK-ready)
│   │   ├── metrics.py               # Prometheus metrics pipeline
│   │   └── performance_logger.py    # İşlem sonuçları, ajan tahmin doğruluğu, öğrenme
│   ├── agents/
│   │   ├── orchestrator.py          # Plan/execute/run_all + scoreboard
│   │   └── memory.py                # Per-agent Q-learning + epsilon-greedy
│   └── tests/                       # pytest testleri (116 test, ≥%70 coverage)
├── SCRIPTS/                           # Node.js motor
│   ├── main.js                        # Ana orchestrator (v2.0)
│   ├── scalping_engine.js            # Scalping sinyal motoru
│   ├── webhook_server.js             # TradingView webhook
│   ├── biquote_signalr.js            # Real-time tick (SignalR)
│   ├── core/                          # Temel modüller
│   │   ├── config.js                  # Merkezi yapılandırma
│   │   ├── event_bus.js              # Event-driven pub/sub
│   │   ├── logger.js                 # Structured JSON logging
│   │   ├── state_manager.js          # Persistent state
│   │   ├── circuit_breaker.js        # Fail-safe circuit breaker
│   │   └── patterns/                  # Design patterns
│   │       ├── factory.js            # Broker & adapter factory
│   │       ├── strategy.js           # Strategy pattern
│   │       └── state_machine.js      # Market regime state machine
│   ├── data/                          # Veri adaptörleri
│   │   ├── broker_manager.js         # Broker seçimi + failover
│   │   ├── broker_matriks.js         # Matriks API
│   │   ├── broker_ideal.js           # İdealFX API
│   │   ├── broker_foreks.js          # Foreks API
│   │   ├── feed_aggregator.js        # Çoklu kaynak birleştirme
│   │   ├── quality_validator.js      # Fiyat tutarlılık kontrolü
│   │   ├── macro_fetcher.js          # Makro veri çekme
│   │   ├── macro_parser.js           # Makro veri işleme
│   │   ├── kap_adapter.js            # KAP bildirimleri
│   │   ├── tradingview_adapter.js    # TradingView scraping
│   │   ├── bigpara_adapter.js        # Bigpara scraping
│   │   └── biquote_adapter.js        # biquote SignalR
│   ├── risk/                          # Risk motoru
│   │   ├── risk_engine.js            # Gerçek zamanlı risk validasyonu
│   │   ├── position_sizer.js         # Kelly, fixed fractional
│   │   └── correlation_matrix.js     # Pearson korelasyon
│   ├── backtest/                      # Node.js backtest (legacy)
│   ├── monitor/                       # İzleme
│   │   ├── health_check.js           # Health check
│   │   ├── audit_logger.js           # Immutable audit log
│   │   ├── regime_detector.js        # Piyasa rejimi
│   │   └── telegram_reporter.js     # Telegram raporlama
│   └── tests/                         # Jest testleri
├── TELEGRAM/
│   └── telegram_listener.ps1         # Canlı Telegram bot (Ollama)
├── AJANLAR/                           # Ajan kuralları (RULES.md)
│   ├── Sinyal/
│   ├── Risk/
│   └── Strateji/
├── STRATEJILER/                       # Strateji dokümanları
├── KURALLAR/                          # Sistem kuralları (K1-K141)
│   ├── AGENTS.md                     # Ana konsey kuralları (v3.0 - 3 Ajan)
│   ├── SAAT_KURALLARI.md            # Saatlik çalışma akışı (v3.0)
│   ├── K122_K140_ENTERPRISE.md      # Enterprise mimari kuralları
│   └── HATA_ANALIZI_VE_GELISIM.md   # Hata kayıtları
└── CONFIG/                            # Boş (openclaw.json bekleniyor)
```

---

## Sık Kullanılan Komutlar

### Python Modülü
```bash
# Veritabanını başlat
cd PYTHON && python main.py --init-db

# Backtest çalıştır (CSV gerekli)
python main.py --backtest data/THYAO.csv --symbol THYAO

# Analitik modülleri
python main.py --analytics data/THYAO.csv

# Portföy monitörü
python main.py --monitor

# ChromaDB demo
python main.py --chroma-demo

# Hata analizi demo
python main.py --error-demo

# Tüm demolar
python main.py --all-demos

# Paper trading sinyal taramasi
AX_PAPER_TRADING=true python PYTHON/paper_trading/signal_engine.py

# Sinyal analizi (tek hisse)
python -c "from PYTHON.paper_trading.signal_engine import SignalEngine; e=SignalEngine(); print(e.analyze_symbol('THYAO'))"

# Forward test raporu
python PYTHON/paper_trading/forward_test.py --days 5

# Telegram rapor
python PYTHON/telegram/reporter.py --type evening

# Veri cekme (Yahoo)
python -c "from PYTHON.data.yahoo_fetcher import YahooFetcher; print(YahooFetcher().fetch('THYAO.IS').tail())"

# BIST tatil kontrolu
python -c "from PYTHON.data.market_calendar import BISTCalendar; c=BISTCalendar(); print(c.get_reason())"

# pytest (tum testler)
cd PYTHON && pytest tests/ -v

# pytest coverage
cd PYTHON && pytest tests/ --cov=. --cov-report=html
```

### Node.js Motoru
```bash
# Başlat
npm install
npm start

# Health check
npm run health

# Test
npm test
```

### Docker
```bash
# Tüm servisleri başlat
docker-compose up -d

# Logları izle
docker-compose logs -f anatoliax-node
docker-compose logs -f anatoliax-python
```

---

## Mimari Akış

```
┌─────────────────────────────────────────────────────────────┐
│  Veri Kaynakları                                              │
│  TradingView ─┬─→ feed_aggregator.js ──→ event_bus            │
│  Bigpara     ─┤                                               │
│  biquote     ─┤                    ┌──────────────────┐       │
│  KAP         ─┴─→ kap_adapter.js  │  Node.js Motor   │       │
│  Makro       ───→ macro_fetcher   │  main.js         │       │
│                                   │  risk_engine.js  │       │
│                                   │  scalping_engine │       │
│                                   └────────┬─────────┘       │
│                                            │                 │
│  ┌──────────────────┐              ┌───────┴───────┐         │
│  │  Broker Manager  │              │   Python      │         │
│  │  Matriks/İdeal/  │◄─────────────│   backtest/   │         │
│  │  Foreks          │  child_process│   analytics/  │         │
│  └──────────────────┘              │   memory/     │         │
│                                    └───────┬───────┘         │
│                                            │                 │
│                                    ┌───────┴───────┐         │
│                                    │   SQLite/     │         │
│                                    │   PostgreSQL  │         │
│                                    │   ChromaDB    │         │
│                                    └───────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## Önemli Entegrasyon Noktaları

### Node.js ↔ Python
- `main.js` `spawn('python3', ['PYTHON/main.py', ...])` ile Python modüllerini çağırır.
- `runBacktest(csvPath, symbol)` ve `runAnalytics(csvPath)` metotları sağlar.

### Broker Failover
- `BrokerManager` sırayla Matriks → İdealFX → Foreks dener.
- Başarısız broker otomatik atlanır, sonraki denenir.

### Veri Kalitesi
- `FeedAggregator` en az 1 kaynak gerektirir.
- `QualityValidator` kaynaklar arası %5'ten fazla sapmayı RED olarak işaretler.
- TradingView yoksa diğer kaynaklara düşer ama uyarı verir.

### Embedding Hafıza
- Her hisse analizi `sentence-transformers/all-MiniLM-L6-v2` ile embedding'e çevrilir.
- ChromaDB'de saklanır. Benzer durumlar sorgulanabilir.
- Varsayılan yol: `./chroma_db` (veya `CHROMA_PATH` env var).

---

## Kırmızı Çizgiler (Claude İçin)

1. **Kodda asla API key/token yazma** — `.env`'den çek (`SecretManager`).
2. **Mock veri kullanırken `getMockData` fonksiyonunu açıkça belirt.**
3. **Fiyat verirken kaynak ve zaman damgası zorunlu:** `"THYAO: 103.0 TL (TradingView, 2026-05-18 14:32)"`.
4. **"Tahminen", "civarı", "ortalama" kelimeleriyle fiyat verme.**
5. **24 saatten eski veri ile analiz yapma.**
6. **Komisyon + BSMV hesabını her zaman dahil et.** (~%0.4 round-trip)
7. **Slippage'i hacme bağlı hesapla.** (düşük hacimli hisselerde daha yüksek)
8. **BIST30/50 scalping için `AX_SCALPING_INDEX=BIST30` env var'ını kullan.**
9. **Piyasa kapalıyken (tatil/haftasonu) asla emir verme.** `BISTCalendar.is_market_open()` kontrolü zorunlu.
10. **Risk engine RED verdiyse emir asla geçmez.** KillSwitch, ExposureLimiter, CircuitBreaker check zorunlu.

---

## Geliştirme Notları

- **Yeni Python modülü eklerken:** `PYTHON/main.py`'ye argparse argümanı ve çalıştırma fonksiyonu ekle.
- **Yeni Node.js adaptörü eklerken:** `SCRIPTS/data/broker_manager.js`'ye failover zincirine dahil et.
- **Yeni kural eklerken:** `KURALLAR/AGENTS.md`'ye K numarası ver ve `README.md`'deki tabloyu güncelle.
- **Yeni ajan eklerken:** `AJANLAR/[Harf]-[Isim]/RULES.md` oluştur, `AGENTS.md`'deki tabloya ekle.
- **Docker değişikliği:** `docker-compose build --no-cache` ile yeniden oluştur.

---

## Bağımlılıklar

### Node.js (package.json)
- `@microsoft/signalr` — biquote SignalR
- `node-fetch` — HTTP scraping
- `ws` — WebSocket
- `jest` — Test

### Python (requirements.txt)
- `pandas`, `numpy` — Veri işleme
- `sqlalchemy` — ORM
- `chromadb` — Vektör DB
- `sentence-transformers` — Embedding
- `pytest` — Test
- `requests` — HTTP
- `python-dotenv` — Env var

---

## Ajan-Modül Eşleştirme Matrisi (v3.0)

Her ajanın sorumluluk alanına göre kullanması gereken modüller:

| Ajan | Rol | Birlesen Eski Ajalar | Python Modülleri | Node.js Modülleri | Komutlar |
|------|-----|---------------------|------------------|-------------------|----------|
| **Sinyal (Ajan-1)** | Teknik + Haber + Dedektif | B + C + F | `indicators.py`, `signals.py`, `volume_anomaly.py`, `bb_volume_combo.py`, `kap_correlation.py`, `error_analyzer.py`, `kap_fetcher.py`, `news_fetcher.py`, `macro_fetcher.py` | `feed_aggregator.js`, `kap_adapter.js`, `macro_fetcher.js` | `python main.py --analytics data/THYAO.csv` |
| **Risk (Ajan-2)** | Risk + Makro + Hesap | D + E + H | `portfolio_monitor.py`, `metrics.py`, `dashboard.py`, `commission.py`, `slippage.py`, `kill_switch.py`, `exposure_limiter.py`, `volatility_throttle.py`, `portfolio_heat.py`, `engine.py`, `performance.py`, `macro_fetcher.py` | `risk_engine.js`, `position_sizer.js`, `correlation_matrix.js` | `python main.py --monitor`, `python main.py --backtest data/THYAO.csv --symbol THYAO` |
| **Strateji (Ajan-3)** | Lider + Hafiza + Intraday | A + G + I | `chroma_store.py`, `embedder.py`, `query.py`, `agent_scoring.py`, `memory.py`, `orchestrator.py`, `performance.py`, `commission.py`, `volume_anomaly.py`, `slippage.py` | `broker_manager.js`, `main.js`, `scalping_engine.js` | `python main.py --monitor`, `python main.py --chroma-demo`, `AX_SCALPING_INDEX=BIST30 node SCRIPTS/scalping_engine.js` |
| **Telegram (Ajan-4)** | Canli iletisim | — | `performance_logger.py`, `auto_validator.py` | — | `python PYTHON/telegram/reporter.py --type evening` |

### Ajan-Ajan Veri Akışı (v3.0 - 3 Tur)
```
Sinyal (B+C+F) --adaylar + PS skoru + MiroFish--> Strateji (A+G+I)
Risk (D+E+H) --risk_etiketi + makro_rejim + 8_metrik--> Strateji (A+G+I)
Strateji --nihai_karar + rapor + dersler--> Telegram
Telegram --komutlar + abonelikler--> Sistem

Eski (9 tur): A<-B<-C<-D<-E<-F<-G<-H<-I --> Karar
Yeni (3 tur): Sinyal --> Risk --> Strateji --> Karar (3x daha hizli)
```

---

## Son Güncelleme

- **2026-05-18:** v2.0 — Python backtest, ChromaDB embedding, broker API'leri, Docker, slippage/komisyon, hacim anomalisi, KAP korelasyonu, derinlemesine hata analizi.
- **2026-05-18:** v2.1 — Paper trading motoru, forward test, unit testler (pytest), ücretsiz veri altyapısı (Yahoo/Investing/TradingView/Bigpara), Telegram canlı raporlama, Docker paper + telegram servisleri.
- **2026-05-19:** v2.2 — Execution Engine (UnifiedExecutionEngine, OrderManager, WebSocketReconnect), Risk Controls (KillSwitch, CircuitBreaker, VolatilityThrottle, ExposureLimiter, PortfolioHeat, SecretManager), Observability (Structured JSON logging, Prometheus metrics), Agent Orchestration (AgentOrchestrator, AgentMemory with Q-learning), Data Pipeline (FeedAggregator, CacheManager, TickStore, MarketCalendar, ReconnectingWebSocket), CI/CD (GitHub Actions), 116 pytest, BIST tatil takvimi.
- **2026-05-20:** v3.0 — Ajan yapısı 9>3 dönüşümü (Sinyal/Risk/Strateji + Telegram), otomatik veri doğrulama (AutoValidator), KAP fetcher, makro fetcher (USD/TRY, DXY, VIX, altın, petrol, BIST100), haber fetcher (Elon Musk tweetleri + sentiment), performans logger (SQLite tabanlı trade sonuçları + ajan doğruluk takibi), SAAT_KURALLARI.md ve AGENTS.md güncellemesi, Telegram SystemPrompt v3.0, kapanış raporu 18:00>17:30.

---

## Paper Trading (v2.1)

### Kullanim
```bash
# Paper trading aktif et
export AX_PAPER_TRADING=true
python PYTHON/paper_trading/signal_engine.py
```

### Moduller
| Modul | Dosya | Gorev |
|-------|-------|-------|
| Paper Broker | `PYTHON/paper_trading/paper_broker.py` | Sanal emir, pozisyon, P&L |
| Signal Engine | `PYTHON/paper_trading/signal_engine.py` | Canli sinyal + risk kontrolu |
| Forward Test | `PYTHON/paper_trading/forward_test.py` | Out-of-sample live test |
| Models | `PYTHON/paper_trading/models.py` | PaperTrade, PaperPortfolio, PaperSignal |

### Paper Trading Akisi
1. `FeedAggregator.fetch()` ile canli veri cek
2. `apply_all()` + `combined_signal()` ile sinyal skoru uret
3. Risk kontrolu: max pozisyon, gunluk kayip limiti, R:R, Kelly
4. `PaperBroker.place_order()` ile sanal emir ver
5. `PaperSignal` tablosuna kaydet
6. Gun sonu `PaperPortfolio` guncelle

### Forward Test Akisi
1. `SignalEngine.analyze_symbol()` ile sinyal uret
2. Sinyali `PaperSignal` olarak kaydet (outcome=PENDING)
3. N gun sonra gercek fiyatla karsilastir
4. `ForwardTest.generate_report()` ile In-Sample vs Out-of-Sample analiz

---

## Execution Engine (v2.2)

Birlesik emir motoru: backtest ve canli mod tek arayuzde.

| Modul | Dosya | Gorev |
|-------|-------|-------|
| UnifiedExecutionEngine | `PYTHON/execution/engine.py` | Backtest + live dual mode, OrderStatus enum |
| OrderManager | `PYTHON/execution/order_manager.py` | Retry + exponential backoff, partial fill tracking, reconciliation |
| WebSocketReconnect | `PYTHON/execution/reconnect.py` | Auto-reconnect, heartbeat, failover endpoint list |
| LatencyMonitor | `PYTHON/execution/latency_monitor.py` | RTT P50/P95/P99 + jitter tracking |

---

## Risk Controls (v2.2)

Genisletilmis risk motoru: kill switch, circuit breaker, exposure limit, volatility throttle, portfolio heat, secret manager.

| Modul | Dosya | Gorev |
|-------|-------|-------|
| KillSwitch | `PYTHON/risk/kill_switch.py` | Max drawdown, gunluk kayip, ust uste zarar limiti |
| CircuitBreaker | `PYTHON/risk/kill_switch.py` | Hata esigi + recovery timeout, 5 deneme |
| VolatilityThrottle | `PYTHON/risk/volatility_throttle.py` | ATR bazli pozisyon kucultme, 0.03 esik |
| ExposureLimiter | `PYTHON/risk/exposure_limiter.py` | Tek hisse/total/sektor limit kontrolu |
| PortfolioHeat | `PYTHON/risk/portfolio_heat.py` | Korelasyon riski, likidasyon mesafesi, heat skoru |
| SecretManager | `PYTHON/risk/secret_manager.py` | .env yukleme, runtime override, logda maskeleme |

---

## Observability & Monitoring (v2.2)

Structured logging + Prometheus metrik pipeline.

| Modul | Dosya | Gorev |
|-------|-------|-------|
| StructuredLogFormatter | `PYTHON/observability/logger.py` | JSON log (ELK-ready), trace_id, agent, symbol |
| MetricsCollector | `PYTHON/observability/metrics.py` | Gauge/Counter/Histogram, Prometheus format export |

---

## Agent Orchestration (v2.2)

Ajan planlayici, yurutucu, geri bildirim dongusu ve Q-learning hafiza.

| Modul | Dosya | Gorev |
|-------|-------|-------|
| AgentOrchestrator | `PYTHON/agents/orchestrator.py` | Plan/execute/run_all, tool routing, scoreboard |
| AgentMemory | `PYTHON/agents/memory.py` | Per-agent Q-table, epsilon-greedy action selection, feedback loop |

---

## Market Calendar (v2.2)

BIST resmi tatil takvimi ve piyasa acik/kapali kontrolu.

| Modul | Dosya | Gorev |
|-------|-------|-------|
| BISTCalendar | `PYTHON/data/market_calendar.py` | Sabit tatiller, dini bayramlar, haftasonu, yari gun. 09:30-18:00 acik |

### Kullanim
```python
from PYTHON.data.market_calendar import BISTCalendar
cal = BISTCalendar()
if cal.is_holiday():
    print(cal.get_reason())  # "Resmi tatil: 01.01.2026 (BIST kapali)"
print(cal.next_open_day())   # Bir sonraki acik gun
```

### Kural K141: Piyasa Kapali = Islem Yok
- Tatil/haftasonu/yari gun: Sistem otomatik olarak kullaniciya bilgi verir
- `SignalEngine.run_scan()` piyasa kapaliysa scan yapmaz, sebep dondurur
- Sonraki acik gun `next_open_day()` ile hesaplanir

---

## CI/CD (v2.2)

GitHub Actions pipeline: test, lint, secret-scan, docker-build, deploy-staging.

| Workflow | Dosya | Gorev |
|----------|-------|-------|
| CI/CD | `.github/workflows/ci.yml` | python-test, node-test, lint, secret-scan, docker-build, deploy-staging |

---

## Unit Testleri (v2.2)

### Calistirma
```bash
cd PYTHON
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
```

### Test Listesi
| Test | Dosya | Kapsam |
|------|-------|--------|
| Commission | `tests/test_commission.py` | Round-trip maliyet, net kar |
| Slippage | `tests/test_slippage.py` | Dusuk/yuksek hacim slip farki |
| Indicators | `tests/test_indicators.py` | EMA, RSI, MACD, Bollinger, ATR |
| Signals | `tests/test_signals.py` | SIGNAL_SCORE, STRONG BUY/WAIT/REJECT |
| Engine | `tests/test_engine.py` | Backtest SL/TP, partial exit, trailing |
| Performance | `tests/test_performance.py` | Sharpe, Sortino, MaxDD, PF, Monte Carlo |
| Portfolio | `tests/test_portfolio_monitor.py` | Trade kaydetme, close, alarm |
| Paper Broker | `tests/test_paper_broker.py` | Sanal emir, limit, P&L |
| Data Fetchers | `tests/test_data_fetchers.py` | Yahoo mock, cache TTL |
| Execution | `tests/test_execution.py` | Engine, OrderManager, LatencyMonitor |
| Kill Switch | `tests/test_kill_switch.py` | KillSwitch, CircuitBreaker, VolatilityThrottle, ExposureLimiter, PortfolioHeat |
| Observability | `tests/test_observability.py` | AuditLogger, MetricsCollector |
| Agents | `tests/test_agents.py` | Orchestrator, AgentMemory Q-learning |
| Tick Store | `tests/test_tick_store.py` | SQLite tick DB, Parquet archive, replay |
| Secret Manager | `tests/test_secret_manager.py` | .env yukleme, maskeleme, validasyon |
| Latency Simulator | `tests/test_latency_simulator.py` | Normal dagilim, Box-Muller |
| Market Calendar | `tests/test_market_calendar.py` | Tatil, haftasonu, yari gun, acik saat |
| Integration | `tests/test_integration.py` | End-to-end: sinyal > risk > execution > broker |

**Toplam:** 116 test, hedef coverage ≥%70.

---

## Telegram Raporlama (v2.1)

### Python Reporter
```bash
python PYTHON/telegram/reporter.py --type morning
python PYTHON/telegram/reporter.py --type opening
python PYTHON/telegram/reporter.py --type midday
python PYTHON/telegram/reporter.py --type evening
```

### PowerShell Bot Komutlari
| Komut | Islev |
|-------|-------|
| `/rapor [sabah/acilis/ogle/kapanis]` | Rapor gonder |
| `/sinyal THYAO` | Sinyal analizi |
| `/portfoy` | Paper portfoy ozeti |
| `/backtest THYAO` | Backtest calistir |
| `/status` | Docker sistem durumu |

---

## Ucretsiz Veri Kaynaklari Matrisi (v2.1)

| Kaynak | Hiz | Limit | Kalite | Kullanim |
|--------|-----|-------|--------|----------|
| **Yahoo Finance** | Hizli | 2000/saat | Yuksek | Birincil, gunluk + 15M |
| **TradingView** | Orta | 1/sn | Yuksek | Ikincil, BIST odakli |
| **Investing.com** | Yavas | 2/sn | Orta | Ucuncul, scraping |
| **Bigpara** | Hizli | 15dk gecikme | Orta | Anlik, ikincil |

### Fallback Zinciri
```
Yahoo Finance -> TradingView -> Investing.com -> Bigpara
```

### Cache Stratejisi
- `PYTHON/data/cache_manager.py` SQLite tabanli
- TTL: 1 saat (gunluk veri), 15 dk (anlik)
- Rate limit korumasi: `min_interval` + exponential backoff

### Data Pipeline Modulleri (v2.2)
| Modul | Dosya | Gorev |
|-------|-------|-------|
| YahooFetcher | `PYTHON/data/yahoo_fetcher.py` | `yfinance` ile BIST verisi (THYAO.IS), gunluk+15M |
| TradingViewScraper | `PYTHON/data/tradingview_scraper.py` | TradingView chart scraping, rate limit 1/sn |
| InvestingScraper | `PYTHON/data/investing_scraper.py` | Investing.com scraping, 2/sn limit |
| BigparaFetcher | `PYTHON/data/bigpara_fetcher.py` | Bigpara JSON API, 15dk gecikmeli |
| FeedAggregator | `PYTHON/data/feed_aggregator.py` | Tumu birlestir, kalite kontrol, fallback zinciri |
| CacheManager | `PYTHON/data/cache_manager.py` | SQLite cache, TTL, rate limit koruma |
| TickStore | `PYTHON/data/tick_store.py` | SQLite tick DB + Parquet arsiv + replay motoru |
| BISTCalendar | `PYTHON/data/market_calendar.py` | Tatil takvimi, piyasa acik/kapali |
| ReconnectingWebSocket | `PYTHON/data/websocket_client.py` | Heartbeat + auto-reconnect |

---

## Docker Servisleri (v2.2)

```bash
docker-compose up -d
```

| Servis | Gorev | Port |
|--------|-------|------|
| anatoliax-node | Node.js ana motor | 3001, 8080 |
| anatoliax-python | Python backtest & analitik | - |
| anatoliax-paper | Paper trading motoru | - |
| anatoliax-telegram | Telegram raporlama botu | - |
| anatoliax-execution | Canli emir motoru + retry/backoff | - |
| anatoliax-scheduler | Cron benzeri zamanlayici (raporlar) | - |
| postgres | Veritabani | 5432 |
| chromadb | Embedding vektor DB | 8000 |
| redis | Cache ve pub/sub | 6379 |
| prometheus | Metrik toplama | 9090 |
| grafana | Dashboard gorsellestirme | 3000 |

---

## Yeni Moduller (v3.3 Pro)

### HFT Pro Ultra-Low-Latency Execution Engine
| Modul | Dizin | Gorev |
|-------|-------|-------|
| Nanosecond Clock | `PYTHON/hft_pro/core/clock.py` | TSC/rdtsc ile nanosaniye saat |
| LockFree Ring Buffer | `PYTHON/hft_pro/core/ring_buffer.py` | mmap tabanli SPSC halka arabellek |
| Object Pool | `PYTHON/hft_pro/core/memory_pool.py` | Thread-local + global overflow bellek havuzu |
| BusySpin EventLoop | `PYTHON/hft_pro/core/event_loop.py` | 5-fazli adaptive spin, CPU affinity |
| Feed Handler | `PYTHON/hft_pro/feed/feed_handler.py` | UDP tick ayristirici |
| L3 OrderBook | `PYTHON/hft_pro/feed/book_reconstructor.py` | sortedcontainers L3 defter + spoofing tespiti |
| Smart Router | `PYTHON/hft_pro/execution/smart_router.py` | Coklu mekan akilli emir yonlendirici |
| KillSwitch | `PYTHON/hft_pro/risk/kill_switch.py` | mmap atomik bayrak, <50us tetikleme |
| Latency Profiler | `PYTHON/hft_pro/latency/profiler.py` | P50/P95/P99/P999 gecikme profilleme |
| Market Maker | `PYTHON/hft_pro/strategy/market_maker.py` | Envanter egimli cift tarafli kotasyon |
| Deterministic Replay | `PYTHON/hft_pro/backtest/replay_engine.py` | SHA-256 dogrulamali bit-ezsiz tekrar |
| BIST Slippage | `PYTHON/hft_pro/backtest/slippage_model.py` | Asamali kayma + hacim etkisi |
| GPU Pipeline | `PYTHON/hft_pro/gpu/gpu_pipeline.py` | 2000-tick regim tespiti (CuPy/ONNX) |
| CUDA Kernels | `PYTHON/hft_pro/gpu/cuda_kernels.py` | EMA/defter/korelasyon RawKernel |

### Real Broker BIST Integration
| Modul | Dizin | Gorev |
|-------|-------|-------|
| Broker Interface | `PYTHON/broker/core/broker_interface.py` | Soyut arayuz + emir/execution tipleri |
| Broker Factory | `PYTHON/broker/core/broker_factory.py` | Yapilandirmaya dayali fabrika |
| Order Validator | `PYTHON/broker/core/order_validator.py` | <10us on-gonderim dogrulama |
| FIX Session | `PYTHON/broker/protocols/fix_session.py` | 4.2/4.4 oturum, sira kurtarma, kalp atisi |
| FIX Message | `PYTHON/broker/protocols/fix_message.py` | Mesaj insa/ayristirma + checksum |
| WebSocket Client | `PYTHON/broker/protocols/websocket_client.py` | Emir WebSocket, auto-reconnect |
| REST Client | `PYTHON/broker/protocols/rest_client.py` | Rate-limit + retry REST istemcisi |
| Matriks Adapter | `PYTHON/broker/adapters/matriks_adapter.py` | Matriks API/FIX adaptoru |
| Gedik Adapter | `PYTHON/broker/adapters/gedik_adapter.py` | Gedik Yatirim REST/FIX adaptoru |
| IsYatirim Adapter | `PYTHON/broker/adapters/isyatirim_adapter.py` | Is Yatirim WebSocket/REST adaptoru |
| Mock Broker | `PYTHON/broker/adapters/mock_broker.py` | Deterministik test aracisi |
| Circuit Breaker | `PYTHON/broker/bist/circuit_breaker.py` | A/B/C grubu devre kesici |
| VBTS | `PYTHON/broker/bist/vbts.py` | Volatilite Bazli Tedbir Sistemi |
| ShortSellBan | `PYTHON/broker/bist/short_sell_ban.py` | Aciga satis yasak listesi |
| VIOP Margin | `PYTHON/broker/viop/margin_calculator.py` | SPAN tabanli marjin hesabi |
| VIOP Adapter | `PYTHON/broker/viop/viop_adapter.py` | VIOP emir adaptoru |
| PreTrade Risk | `PYTHON/broker/risk/pre_trade_check.py` | On-ticaret risk kontrolu |
| Reconciliation | `PYTHON/broker/reconciliation/position_recon.py` | Gun sonu konum uzlastirma |
| Tax Reporter | `PYTHON/broker/reporting/tax_report.py` | Turk vergi duzenlemeleri raporu |

### GPU/FPGA Acceleration
| Modul | Dizin | Gorev |
|-------|-------|-------|
| CUDA Context | `PYTHON/acceleration/gpu/cuda_context.py` | Akis + bellek havuzu yonetimi |
| RAPIDS Pipeline | `PYTHON/acceleration/gpu/rapids_pipeline.py` | cuDF EMA/RSI/MACD (CPU geri donus) |
| CUDA Kernels | `PYTHON/acceleration/gpu/cuda_kernels.py` | EMA/defter/korelasyon RawKernel |
| ONNX GPU | `PYTHON/acceleration/gpu/onnx_runtime.py` | TensorRT/CUDA/CPU saglayici |
| GPU Scheduler | `PYTHON/acceleration/gpu/gpu_scheduler.py` | Oncelikli kuyruk + akis atama |
| FPGA Interface | `PYTHON/acceleration/fpga/fpga_interface.py` | Xilinx Alveo pyxrt arayuzu |
| Verilog Stubs | `PYTHON/acceleration/fpga/verilog_stubs/` | feed_parser.v, order_book.v, top_level.v |
| C++ Shim | `PYTHON/acceleration/cpp_shim/` | pybind11 NanosecondClock, ParsedTick, OrderBook |
| Benchmarks | `PYTHON/acceleration/benchmarks/gpu_benchmark.py` | 3x+ hizlanma benchmark paketi |

### Claude↔Kimi Automation
| Modul | Dizin | Gorev |
|-------|-------|-------|
| Orchestrator | `.agents/orchestrator.py` | Yetkinlik matrisi + gorev ayrimi |
| Claude Bridge | `.agents/claude_bridge.py` | `claude dev` CLI sarmalayici |
| Kimi Bridge | `.agents/kimi_bridge.py` | OpenAI uyumlu inceleme/arastirma |
| Shared Memory | `.agents/shared_memory.py` | SQLite + ChromaDB + AsyncEventBus |
| Task Queue | `.agents/task_queue.py` | SQLite oncelikli gorev kuyrugu |
| Quality Gates | `.agents/quality_gates.py` | Syntax/mypy/lint/test/security/review |
| Human Gate | `.agents/human_gate.py` | 5 seviyeli onay (L1-L5) |
| Rollback | `.agents/rollback_system.py` | Git snapshot + geri alma |

### Unified CLI
`ash
python PYTHON/anatoliax_pro_cli.py hft-pro --config CONFIG/hft_pro.yaml
python PYTHON/anatoliax_pro_cli.py broker-trade --config CONFIG/broker.yaml
python PYTHON/anatoliax_pro_cli.py benchmark-gpu
python PYTHON/anatoliax_pro_cli.py dev-task "Implement GPU scheduler"
python PYTHON/anatoliax_pro_cli.py dev-status
python PYTHON/anatoliax_pro_cli.py dev-review PYTHON/hft_pro/core/clock.py
`

---

## Son Guncelleme

- **2026-05-26:** v3.3 Pro — HFT Pro, Real Broker BIST Integration, GPU/FPGA Acceleration, Claude↔Kimi Automation modulleri eklendi. Mevcut mimari bozulmadan yeni moduller eklendi. `PYTHON/anatoliax_pro_cli.py` birlesik CLI olusturuldu.
