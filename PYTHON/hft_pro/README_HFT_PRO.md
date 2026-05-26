# HFT Pro Ultra-Low-Latency Execution Engine

**Versiyon:** 1.0.0 | **Modul:** `PYTHON/hft_pro/`

## Ozet

HFT Pro, BIST icin ultra-dusuk gecikmeli algoritmik ticaret motorudur.

## Bilesenler

- `core/` — Temel altyapi: nanosaniye saat, kilitsiz halka arabellek, bellek havuzu, olay dongusu
- `feed/` — Piyasa verisi: UDP parser, L3 emir defteri rekonstruksiyonu
- `execution/` — Akilli emir yonlendirici (coklu mekan)
- `risk/` — On-ticaret risk ve acil durum anahtari
- `latency/` — Uctan-uca gecikme profilleme (P50/P95/P99/P999)
- `strategy/` — Piyasa yapici strateji (envanter egimi)
- `backtest/` — Deterministik tekrar motoru + BIST kayma modeli
- `gpu/` — GPU zaman serisi regim tespiti (CuPy + ONNX Runtime)

## Kural Uyumu

- K142-K148: BIST duzenlemeleri
- K94: Sembol basina maksimum %2
- K95: Gunluk maksimum kayip %3
