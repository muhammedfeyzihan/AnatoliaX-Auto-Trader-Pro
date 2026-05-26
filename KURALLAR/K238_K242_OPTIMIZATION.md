# K238-K242 — Sistem Optimizasyonu Kurallari

**Versiyon:** 3.3-opt  
**Tarih:** 2026-05-22  
**Kapsam:** Maksimum performans icin I/O, compute, memory ve orkestrasyon katman optimizasyonlari.

---

## K238 — Hizli Cache Yonetimi (FastCacheManager)

`PYTHON/optimization/fast_cache.py`

- **LRU in-memory cache:** Hot data SQLite'a hic gitmez (50x+ hizli get).
- **Persistent connection + WAL mode:** Her op için open/close yok.
- **Buffered writes:** Otomatik batch insert (varsayilan: 100 kayit veya 5 sn).
- **Lazy TTL eviction:** SQLite'da expired row'lar lazy silinir.
- **Drop-in replacement:** `CacheManager` yerine `FastCacheManager` kullanilir.

**Kural:** Her yeni fetcher `FastCacheManager`'i tercih etmeli.

---

## K239 — Asenkron Paralel Veri Cekme (AsyncFeedAggregator)

`PYTHON/optimization/async_feed_aggregator.py`

- **asyncio.gather:** Semboller paralel cekilir (8x hizli multi-symbol).
- **ThreadPoolExecutor:** Sync fetcher'lar (yfinance, requests) async wrapper ile calisir.
- **Semaphore:** Max 8 eszamanli baglanti (rate limit koruma).
- **Retry + backoff:** 2 retry, 0.5s/1s/2s exponential backoff.
- **Timeout:** Her request 15 sn.

**Kural:** BIST universe taramasi `--parallel-scan` ile calistirilmali.

---

## K240 — Hizli Tick Depolama (BatchTickStore)

`PYTHON/optimization/batch_tick_store.py`

- **WAL + persistent connection:** Her tick icin open/close yok.
- **Buffered inserts:** Varsayilan 1000 tick veya 5 sn'de bir flush.
- **Background writer thread:** Insert non-blocking.
- **Parquet export:** zstd sikistirma ile gun sonu arsiv.
- **Numpy replay:** `df.iterrows()` yerine `to_records()` ile 10x+ hizli replay.

**Kural:** HFT ve tick-level sistemler `BatchTickStore` kullanmali.

---

## K241 — Vektorize Backtest Motoru (VectorizedBacktestEngine)

`PYTHON/optimization/vectorized_backtest.py`

- **NumPy arrays:** `df.iterrows()` yerine `close.to_numpy()` — ~60x hizli.
- **Pure Python loop:** Pozisyon yonetimi (SL/TP/partial) vektörize edilemez, ama pandas overhead'i kalkar.
- **Ayni API:** `BacktestEngine` ile ayni init/run signature.
- **Daily reset:** Tarih karsilastirmasi int (YYYYMMDD) olarak yapilir.

**Kural:** Buyuk veri setleri (100k+ bar) icin `--vectorized-backtest` kullanilmali.

---

## K242 — Paralel Sinyal Tarayici (ParallelScanner)

`PYTHON/optimization/parallel_scanner.py`

- **ThreadPoolExecutor:** Sembol analizi paralel calisir.
- **I/O + CPU ayrimi:** FeedAggregator I/O'su ThreadPool ile, indikator hesabi ana thread'de (veya ProcessPool).
- **Progress tracking:** `run_scan_with_progress()` ile istatistik.
- **Market open check:** Once piyasa acik mi kontrol edilir, sonra paralel tarama.

**Kural:** 10+ sembol taramasi her zaman `ParallelScanner` ile yapilmali.

---

## Ek Optimizasyonlar (Mevcut Modullerde)

### signals.py — Lazy Indicator Computation
- `combined_signal(df, indicators_needed=["ema","rsi"])` ile sadece gerekli indikatörler hesaplanir.
- Varsayilan `None` = tum indikatörler (geriye uyumlu).

### performance.py — Vektorize Monte Carlo
- `np.random.choice(arr, size=(simulations, n))` ile tek hamlede 10k simülasyon.
- ~100x hizli vs Python döngüsü.

### portfolio_monitor.py — In-Memory Cache
- Acik pozisyonlar memory'de tutulur, DB'ye sadece write/commit yapilir.
- Gunluk trade cache'i 30 sn TTL ile yenilenir.
- `_refresh_open_positions()` lazy calisir.

### main.py — Paralel CLI
- `--parallel-scan THYAO,GARAN,... --workers 8`
- `--vectorized-backtest` flag'i

---

## Test

- `pytest PYTHON/tests/test_fast_cache.py` — 5 test
- `pytest PYTHON/tests/test_vectorized_backtest.py` — 4 test
- `pytest PYTHON/tests/test_batch_tick_store.py` — 4 test
- **Toplam:** 13 yeni test
- **Toplam sistem:** 982+ test

---

*AnatoliaX Trading System v3.3 — Maximum Optimization*
