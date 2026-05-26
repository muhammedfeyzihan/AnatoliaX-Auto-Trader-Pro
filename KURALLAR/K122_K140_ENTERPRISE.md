# ANATOLIAX ENTERPRISE KURALLARI (K122-K140)
# v2.0 Mimari Kurallar - Design Patterns, Fail-Safe, Event-Driven

## K122: DESIGN PATTERNS (Zorunlu)
- Strategy Pattern: Her trade stratejisi ayni interface'i implemente eder.
- Observer Pattern: Sinyal aboneligi, loose coupling.
- Factory Pattern: Broker ve adapter nesneleri factory'den uretilir.
- State Machine: Piyasa rejimi ve sistem durumu state machine ile yonetilir.
- Singleton: Logger, EventBus, Config tek nesne.

## K123: ASENKRON MIMARI (Zorunlu)
- Tum I/O islemleri async/await ile yapilir.
- Blocking kod yasak.
- EventBus uzerinden moduller arasi iletisim.
- Promise hatalari .catch() ile yakalanir.

## K124: MERKEZI KONFIGURASYON (Zorunlu)
- .env + config.json. Hardcode yok.
- Siralama: env var > config.json > default.
- Config degisikligi restart gerektirir (hot-reload yok).
- Secret'lar env var'da, kodda yok.

## K125: STRUCTURED LOGGING (Zorunlu)
- JSON formatinda log. Seviyeler: fatal, error, warn, info, debug, trace.
- Her log: timestamp, level, msg, pid, module.
- Log dosyalari: {level}.log + combined.log
- Max boyut: 100MB. Rotation harici tool ile.

## K126: CIRCUIT BREAKER + RETRY (Zorunlu)
- Her dis servis cagrisi circuit breaker ile korunur.
- Retry: Exponential backoff + jitter.
- Max retry: 5. Base delay: 1s. Max delay: 30s.
- Fallback fonksiyonu zorunlu.

## K127: EVENT-DRIVEN EXECUTION (Zorunlu)
- Tum moduller EventBus uzerinden haberlesir.
- Event adlari BUYUK_HARF ile. Ornek: TICK_RECEIVED, ORDER_PLACED.
- Event handler'lar hata yakalamali.
- Event history son 1000 event tutulur.

## K128: RISK ENGINE (Zorunlu)
- Her islem oncesi risk engine calistirilir.
- Kontroller: dailyLoss, positionSize, maxPositions, R:R, correlation, sector.
- Risk engine RED derse islem ASLA gerceklesmez.
- Kelly, VaR, Sharpe, Expectancy hesaplanir.

## K129: BROKER ABSTRACTION (Zorunlu)
- Broker interface soyuttur.
- MockBroker test icin. Gercek broker sonrasi implemente edilir.
- Broker degisikligi sadece config'te.
- Her broker: connect, disconnect, placeOrder, cancelOrder, getPositions, getBalance, getQuote.

## K130: WEBSOCKET RECONNECT (Zorunlu)
- WebSocket koparsa otomatik reconnect.
- Exponential backoff: 1s, 2s, 4s... max 30s.
- Max deneme: 10. Asiri kopma = alert.
- Heartbeat: 30sn. Timeout = reconnect.

## K131: PERSISTENT STATE (Zorunlu)
- Her modul kendi state'ini JSON dosyaya kaydeder.
- Auto-save: 60sn. SIGINT/SIGTERM'de sync save.
- Crash sonrasi recovery: state dosyasindan yukle.
- State dizini: ./state/

## K132: AUDIT LOGGING (Zorunlu)
- Her karar, her islem, her onay JSONL olarak kaydedilir.
- Audit log degistirilemez, silinemez.
- Format: {id, timestamp, module, event, data, hash}
- Dizin: ./audit/

## K133: MONITORING (Zorunlu)
- Health check: 60sn aralikla tum moduller kontrol.
- 3 basarisiz check = ALERT.
- Dashboard: CLI + HTML.
- Metrikler: latency, error rate, throughput, position count.

## K134: LATENCY SIMULATION (Zorunlu)
- Backtest'te gercekci latency eklenir.
- Normal dagilim: mean=150ms, stdDev=50ms.
- Min: 50ms, Max: 500ms.
- Jitter: random delay.

## K135: SLIPPAGE/LIQUIDITY (Zorunlu)
- Hacme bagli slippage: dusuk hacim = yuksek slippage.
- Base slippage: %0.1. Max: %1.
- Liquidity check: orderValue < derinlik * 0.1.
- Spread maliyeti hesaba katilir.

## K136: REGIME DETECTION (Zorunlu)
- Piyasa rejimi: BULL, BEAR, SIDEWAYS, VOLATILE, CRASH.
- VIX + trend + breadth + volume kullanilir.
- Rejim degisikliginde event yayilir.
- Strateji rejime gore ayarlanir.

## K137: SECRET MANAGEMENT (Zorunlu)
- Token/sifreler .env + process.env.
- Kodda asla hardcoded secret yok.
- .env gitignore'da.
- Secret maskelenmis log (***).

## K138: CI/CD (Zorunlu)
- GitHub Actions: lint, test, build, secret-scan.
- Test coverage esik: %70 line, %50 branch.
- TruffleHog ile secret tarama.
- Her PR'de test calisir.

## K139: TEST COVERAGE (Zorunlu)
- Unit test: Jest. Her modul icin.
- Integration test: End-to-end akis.
- Mock external services.
- Coverage report artifact.

## K140: INVESTING.COM (Zorunlu)
- Investing.com ikincil kaynaktir.
- TradingView birincil (K91).
- Investing scraping + cache.
- Circuit breaker korur.

## K141: PIYASA TATILI ve ACILIK KONTROLU (Zorunlu)
- BIST resmi tatilleri, haftasonu ve yari gunler otomatik takip edilir.
- `BISTCalendar` sinifi: Sabit tatiller (1 Ocak, 23 Nisan, 1 Mayis, 19 Mayis, 15 Temmuz, 30 Agustos, 29 Ekim), dini bayramlar (manuel), haftasonu (Cumartesi/Pazar), yari gun (09:30-12:30).
- Tatil gununde `SignalEngine.run_scan()` calismaz, kullaniciya "Piyasa kapali" mesaji verir.
- Yari gun: Ogleden sonra (12:30 sonrasi) emir verilmez.
- Sonraki acik gun `next_open_day()` ile hesaplanir ve raporlanir.
- Piyasa saatleri: Normal gun 09:30-18:00, yari gun 09:30-12:30.
- Kirmizi cizgi: Tatil/haftasonu/yari gun islem = RED.

---

*Tum K122-K141 kurallari zorunludur. Ihlal = RED.*
*Versiyon: 2.2 | 19 Mayis 2026*
