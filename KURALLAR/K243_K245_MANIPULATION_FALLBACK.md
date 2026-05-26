# K243-K245 — Manipülasyon Fallback ve Çoklu Piyasa Geçisi Kurallari

**Versiyon:** 3.3  
**Tarih:** 2026-05-22  
**Kapsam:** Manipülasyon tespiti sonrasi otomatik alternatif piyasa/seçim geçisi.

---

## K243 — Manipülasyon Fallback Router (ManipulationFallbackRouter)

Manipülasyon tespit edildiginde sistem otomatik olarak en mantikli alternatife gecis yapar.

**Öncelik Sirasi:**
1. **Ayni borsa (BIST) farkli hisse** — En yüksek skorlu manipülasyonsuz hisse
2. **Kripto piyasasi** — Binance/Bybit/OKX (BTCUSDT, ETHUSDT, SOLUSDT, AVAXUSDT)
3. **Forex piyasasi** — Yahoo Finance (EURUSD, GBPUSD, USDJPY, XAUUSD)

**Davranis:**
- Manipülasyon tespit edilen sembol kara listeye alinir (TTL: 60 dk varsayilan).
- Kara listedeki semboller fallback zincirinde hariç tutulur.
- Fallback basarisiz olursa sistem bekler, islem yapmaz.
- Her gecis `FallbackResult` ile loglanir.

**Entegrasyon:** `PYTHON/execution/manipulation_fallback.py`

**Kullanim:**
```bash
# Fallback aktif tarama
python PYTHON/main.py --fallback-scan THYAO,GARAN,ASELS --enable-crypto-fallback
```

---

## K244 — Dinamik Sembol Rotasyonu (DynamicSymbolRotator)

Sürekli olarak tum sembollerin skorunu izler, mevcut sembolden daha iyi alternatif varsa otomatik rotasyon yapar.

**Rotasyon Tetikleyicileri:**
- Manipülasyon tespiti (anlik)
- Skor farki ≥ 15 puan (mevcut vs en iyi alternatif)
- Sembol skoru hesaplanamadi (veri yok)
- Kara listede olma

**Davranis:**
- `update_scores()` ile tum BIST universe skorlari periyodik guncellenir.
- `should_rotate()` rotasyon kararini verir.
- `get_rotation_target()` en iyi alternatifi dondurur.
- Rotasyon tarihcesi kaydedilir (`record_rotation()`).
- Max pozisyon sayisi asilmadan yeni pozisyon acilir.

**Entegrasyon:** `PYTHON/strategy/dynamic_symbol_rotator.py`

**Kullanim:**
```bash
# Dinamik rotasyon ile tarama
python PYTHON/main.py --auto-rotate-scan THYAO,GARAN,ASELS
```

---

## K245 — Strateji ve Sistem Entegrasyonu

### SignalEngine Entegrasyonu

`SignalEngine.analyze_symbol()` manipülasyon tespiti sonrasi:
1. Skor duserse `signal_threshold` altina
2. `fallback_router.fallback(symbol)` cagrilir
3. Eger fallback bulunursa, yeni sembol ile `analyze_symbol()` recursive cagrilir
4. Kara liste loglanir

`SignalEngine.run_scan_with_fallback()`:
- Her sembol icin fallback mekanizmasi calisir
- Fallback sayisi raporlanir

`SignalEngine.run_dynamic_rotation_scan()`:
- Tum sembol skorlari guncellenir
- Rotasyon gereken semboller otomatik degistirilir
- Rotasyon tarihcesi yazdirilir

### CLI Argümanlari

| Argüman | Açiklama |
|---|---|
| `--fallback-scan SYMBOLS` | Fallback aktif tarama |
| `--auto-rotate-scan SYMBOLS` | Dinamik rotasyon ile tarama |
| `--enable-crypto-fallback` | Kripto piyasasina gecis aktif |
| `--enable-forex-fallback` | Forex piyasasina gecis aktif |

### Kod Örnegi

```python
from PYTHON.execution.manipulation_fallback import ManipulationFallbackRouter
from PYTHON.strategy.dynamic_symbol_rotator import DynamicSymbolRotator

router = ManipulationFallbackRouter(enable_crypto=True, enable_forex=True)
result = router.fallback("THYAO", bist_universe=["GARAN","ASELS","ISCTR"])
print(result.fallback_symbol, result.fallback_market)

rotator = DynamicSymbolRotator(bist_universe=["THYAO","GARAN","ASELS"])
rotator.update_scores()
best = rotator.select_best_symbol()
should_rotate, reason = rotator.should_rotate("THYAO")
if should_rotate:
    target = rotator.get_rotation_target("THYAO")
    print(f"Dönüş: {target.fallback_symbol}")
```

---

## Kritik Kurallar

- **K243a** — Manipülasyon tespit edildiginde ayni sembolde islem YAPILMAZ.
- **K243b** — Fallback önceligi: BIST > Kripto > Forex.
- **K243c** — Kara liste TTL'si dolana kadar sembol pasif kalir.
- **K244a** — Rotasyon skor farki en az 15 puan olmali.
- **K244b** — Max pozisyon asilmadan yeni pozisyon acilabilir.
- **K244c** — Rotasyon tarihcesi gun sonu raporunda yer alir.
- **K245a** — Fallback her zaman `FallbackResult` ile loglanmali.
- **K245b** — Kripto/Forex gecislerinde `ExchangeAdapter` veya `YahooFetcher` kullanilmali.

---

## Test

- `pytest PYTHON/tests/test_manipulation_fallback.py` — 6 test
- `pytest PYTHON/tests/test_dynamic_symbol_rotator.py` — 7 test
- **Toplam:** 13 yeni test
- **Sistem toplami:** 995+ test

---

*AnatoliaX Trading System v3.3 — Manipülasyon Fallback*
