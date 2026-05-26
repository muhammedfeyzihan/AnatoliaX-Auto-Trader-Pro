# GOLD_MINING.md — Altın Madeni Stratejisi Kuralları

**Versiyon:** 3.0  
**Tarih:** 2026-05-23  
**Amaç:** En hızlı ve en garanti yoldan profesyonel para kazanma. Kademeli ajan aktivasyonu ile riski minimize eder, verimi maksimize eder. Tüm borsa hisseleri, forex ve kripto paralar için geçerlidir.

---

## 1. Felsefe

> *"Borsayı yakalamak için çok ajan değil, doğru ajan ve doğru zamanda çalışmak gerekir."*

- **Maksimum 3 ajan.** Çok ajan = borsayı kaçırır.
- **Kademeli aktivasyon.** Sermaye büyüdükçe zaman dilimi ve ajan sayısı artar.
- **Otomatik geri çekilme (fallback).** Zarar zinciri oluşursa sistem bir alt kata iner.
- **Otomatik zaman dilimi seçimi.** Piyasa koşullarına göre en verimli tier otomatik seçilir.
- **Manuel çıkış.** Kullanıcı istediği zaman pozisyonu manuel kapatabilir.
- **Tüm hisseler, forex, kripto için geçerli.** Zaman dilimleri enstrümana göre uyarlanabilir.

---

## 2. Tier Sistemi (MS → S1 → M1 → M5 → M15 → M30 → H1 → H2 → D1)

| Tier | Zaman Dilimi | Hedef Kar | Tutma Süresi | Ajan Sayısı | Min Sermaye | Kazanma Serisi | Min WR |
|------|-------------|-----------|-------------|-------------|-------------|----------------|--------|
| **MS** | 500 ms (simüle) | %0.01–0.05 | 0.5–3 sn | 1 | 0 TL | 5 | %55 |
| **S1** | 1 saniye | %0.05–0.2 | 3–15 sn | 1 | 1.000 TL | 5 | %55 |
| **M1** | 1 dakika | %0.3–1.0 | 30–120 sn | 2 | 5.000 TL | 5 | %55 |
| **M5** | 5 dakika | %0.8–2.0 | 2–10 dk | 2 | 12.000 TL | 4 | %57 |
| **M15** | 15 dakika | %1.5–5.0 | 5–30 dk | 3 | 25.000 TL | 3 | %60 |
| **M30** | 30 dakika | %2.5–7.0 | 30 dk–2 saat | 3 | 37.500 TL | 3 | %60 |
| **H1** | 1 saat | %2.0–6.0 | 1–4 saat | 3 | 50.000 TL | 3 | %60 |
| **H2** | 2 saat | %4.0–10.0 | 2–8 saat | 3 | 75.000 TL | 2 | %62 |
| **D1** | 1 gün | %5.0–15.0 | 1–5 gün | 3 | 100.000 TL | 2 | %62 |

**Tier Geçişi (Graduation):**
- Bir üst tura geçmek için **tüm** şartlar sağlanmalı:
  1. `realized_pnl >= next_tier.min_capital`
  2. `consecutive_wins >= next_tier.required_consecutive_wins`
  3. `win_rate >= next_tier.required_win_rate`

**Geri Çekilme (Fallback):**
- `consecutive_losses >= 3` (tier M1 ve üstü)
- `drawdown >= %5` (peak equity'den)
- Fallback her zaman **bir** tier aşağıya iner.
- MS tier'dan daha aşağı inilemez.

---

## 3. Ajan Tanımları

| Tier | Ajan 1 | Ajan 2 | Ajan 3 |
|------|--------|--------|--------|
| **MS** | Sinyal (Order-flow imbalance) | — | — |
| **S1** | Sinyal (VWAP sapma + hacim) | — | — |
| **M1** | Sinyal (EMA 3/8 cross + hacim) | Risk (RSI onay) | — |
| **M5** | Sinyal (EMA 5/13 cross + hacim) | Risk (RSI + ATR vol) | — |
| **M15** | Sinyal (EMA 9/21 cross + hacim) | Risk (Makro rejim + sentiment) | Strateji (Confidence + Consensus) |
| **M30** | Sinyal (EMA 13/34 cross + hacim) | Risk (Makro rejim + adaptive RSI) | Strateji (Confidence + Consensus + ParameterRegistry) |
| **H1** | Sinyal (EMA 9/21 + MACD hist) | Risk (ATR + makro rejim) | Strateji (Confidence + Consensus) |
| **H2** | Sinyal (EMA 21/55 + RSI + BB) | Risk (Makro + sektör korelasyonu) | Strateji (Confidence + Kelly + Consensus + ParameterRegistry) |
| **D1** | Sinyal (EMA 21/50 + RSI + BB) | Risk (Makro + sektör korelasyonu) | Strateji (Confidence + Kelly + Consensus) |

**Byzantine Consensus (M15, H1, D1):**
- 3 ajanın oyu ağırlıklıdır (`AgentTrustScorer` ile).
- Trust skoru < 60 olan ajan susturulur.
- `consensus_required`: varsayılan %100 (unanimous), opsiyonel %67 (2/3).

---

## 4. Otomatik Zaman Dilimi Seçimi (AdaptiveTierSelector)

`AdaptiveTierSelector` piyasa koşullarını analiz ederek en verimli tier'i seçer:

| Piyasa Koşulu | Önerilen Tier | Neden |
|---------------|---------------|-------|
| Yüksek volatilite + yüksek hacim | M5 / S1 | Hızlı hareketleri yakalar |
| Orta volatilite + net trend | M15 / M30 / H1 | Trend takibi optimum |
| Düşük volatilite + yatay | M1 / S1 | Mean-reversion veya bekle |
| Güçlü trend (ADX > 35) | H2 / D1 | Büyük hareketleri yakalar |
| Güçlü trend (ADX 30-35) | H1 / M30 | Orta ölçekli trend yakalama |
| Ayı piyasası + düşük hacim | M1 / MS | Küçük scalp fırsatları |

**Kullanım:**
```python
from PYTHON.strategy.gold_mining import GoldMiningOrchestrator
engine = GoldMiningOrchestrator(rules={"auto_tier_switch": True})
engine.auto_select_tier(df, macro={"regime": "BULL"})
```

---

## 5. Manuel Çıkış Sistemi

Kullanıcı istediği zaman pozisyonu manuel kapatabilir:

```python
engine.manual_exit("THYAO", exit_price=105.0, reason="KAR_REALIZE")
engine.manual_exit("THYAO", exit_price=95.0, reason="ZARAR_DUR")
```

- SL/TP bypass edilir, anında kapanır.
- Sebep kaydedilir (`KAR_REALIZE`, `ZARAR_DUR`, `MANUEL`).
- P&L, streak ve kill switch güncellenir.

---

## 6. Risk Kuralları

### 6.1 Pozisyon Büyüklüğü
- Kelly Criterion × `kelly_fraction` (varsayılan 0.25).
- Maksimum sermayenin %2'sini geçemez.
- BIST lot büyüklüğü = 1 adet.

### 6.2 Stop Loss / Take Profit
- **MS:** SL %0.01, TP %0.03
- **S1:** SL %0.05, TP %0.10
- **M1:** SL %0.30, TP %0.50
- **M5:** SL %0.80, TP %1.50
- **M15:** SL %1.50, TP %3.00
- **M30:** SL %2.00, TP %4.00 (ATR-based adaptive via ParameterRegistry)
- **H1:** SL %2.00, TP %4.00
- **H2:** SL %3.00, TP %6.00 (ATR-based adaptive via ParameterRegistry)
- **D1:** SL %4.00, TP %10.00

### 6.3 Risk Kapıları (Risk Gates)
1. **Kill Switch:** Max drawdown %10, günlük kayıp %5, üst üste 5 zarar.
2. **Exposure Limiter:** Tek hisse %2, toplam 5 pozisyon.
3. **Cooldown:** İsteğe bağlı, işlemler arası bekleme süresi.
4. **Manipulation Check:** Çoklu zaman dilimi manipülasyon tespiti varsa RED.
5. **Piyasa Açık mı?:** BIST saatleri dışında emir yok (K141).

### 6.4 Komisyon + BSMV
- Her işlemde %0.4 round-trip maliyet hesaplanır.
- Girişte yarısı, çıkışta yarısı tahsil edilir.

---

## 7. Kullanıcı Özelleştirmesi (Rules)

Kullanıcı `GoldMiningOrchestrator(rules={...})` ile aşağıdaki kuralları değiştirebilir:

| Kural | Varsayılan | Açıklama |
|-------|------------|----------|
| `graduation_multiplier` | 1.0 | Min sermaye × çarpan = gerçek eşik |
| `fallback_drawdown_pct` | 0.05 | %5 drawdown → fallback |
| `fallback_consecutive_losses` | 3 | 3 üst üste zarar → fallback |
| `max_agents_override` | 3 | Hard ajan sınırı |
| `kelly_fraction` | 0.25 | Kelly çarpanı |
| `max_risk_per_trade_pct` | 0.02 | İşlem başına max risk (%2) |
| `require_manipulation_check` | True | Manipülasyon kontrolü zorunlu |
| `require_kill_switch` | True | Kill switch aktif |
| `cooldown_seconds` | 0.0 | İşlemler arası bekleme (sn) |
| `auto_tier_switch` | True | Otomatik zaman dilimi seçimi |

---

## 8. CLI Kullanımı

```bash
# BIST universe tamamı ile Gold Mining
python main.py --gold-mining

# Belirli semboller, S1 tier'dan başla, 50.000 TL sermaye
python main.py --gold-scan THYAO,GARAN,ASELS --gold-tier S1 --gold-capital 50000

# Kuralları değiştirerek (Python API)
python -c "
from PYTHON.strategy.gold_mining import GoldMiningOrchestrator
engine = GoldMiningOrchestrator(
    initial_capital=100000,
    rules={'cooldown_seconds': 60, 'max_risk_per_trade_pct': 0.01, 'auto_tier_switch': True}
)
print(engine.to_dict())
"
```

---

## 9. Entegrasyon Kuralları

1. **Mevcut stratejiler korunur.** Gold Mining bir *alternatif* stratejidir.
2. `SignalEngine` ve `PaperBroker` ile uyumlu çalışır.
3. `PreTradeRiskEngine` bus üzerinden emir onayı verir.
4. `AgentTrustScorer` ile ajan güven skorları dinamik güncellenir.
5. `MultiTFManipDetector` her tier'da veri kalitesini doğrular.
6. `AdaptiveTierSelector` otomatik tier seçimi yapar.
7. `manual_exit()` kullanıcı kontrolünü sağlar.

---

## 10. Matematiksel Doğruluk Kontrol Listesi

- [ ] `win_rate = winning_trades / total_trades` — sıfıra bölme kontrollü.
- [ ] `drawdown = (peak_equity - current_equity) / peak_equity` — peak sıfır kontrollü.
- [ ] `position_size = floor(equity × risk_pct / price)` — min 1 lot.
- [ ] `Kelly f* = (bp - q) / b` — negatif ise 0, pozitif ise kelly_fraction ile sınırlı.
- [ ] `consensus_pct = sum(votes) / len(votes)` — 0 ile 1 arasında.
- [ ] `confidence` — 0 ile 100 arasında clamp.
- [ ] `ATR` — `high`, `low`, `close` dizileri eşit uzunlukta.
- [ ] `EMA` — `alpha = 2 / (period + 1)` — standart.
- [ ] `VWAP = sum(price × volume) / sum(volume)` — sıfır hacim kontrollü.
- [ ] `ADX` — +DM, -DM, TR smoothing — standart Wilder.

---

## 11. Sık Karşılaşılan Sorunlar

| Sorun | Neden | Çözüm |
|-------|-------|-------|
| MS tier sinyal üretmiyor | Gerçek tick verisi yok; sentetik bar kullanılıyor | `FeedAggregator` 1m veriyi otomatik sentetik micro-bar'a çevirir |
| M1 secondary onay RED | RSI aşırı alım/satım bölgesinde | Trendin güçlendiği anları bekle |
| M15 consensus RED | Makro rejim veya sentiment ters | Günlük makro skoru kontrol et |
| Adaptive tier sürekli değişiyor | `auto_tier_switch` True ama piyasa çok dalgalı | `cooldown_seconds` ekle veya `auto_tier_switch` False yap |
| Fallback sürekli tetikleniyor | `fallback_drawdown_pct` çok dar | Kuralı %8'e yükselt |
| Kill Switch erken tetikleniyor | `consecutive_losses` limiti düşük | Kuralı 7'ye yükselt |

---

## 12. Geliştirici Notları

- Yeni tier eklenirse `TIER_DEFINITIONS` listesine ekle ve `orchestrator.py` `_strategies` dict'ine kat.
- Yeni ajan eklenirse `max_agents_override` 3'ü geçmemeli (Kural: max 3 ajan).
- Testler: `pytest tests/test_gold_mining.py -v`
- Backtest/live parity: Aynı `GoldMiningOrchestrator` nesnesi backtest ve live'da çalışmalı.
- Adaptive selector: `AdaptiveTierSelector.analyze()` piyasa verisini bozmadan çalışır.
