# K142-K170 — BIST Regülasyonları, Davranışsal Finans, Backtest Kuralları

**Versiyon:** 3.2  
**Tarih:** 2026-05-22  
**Kapsam:** BIST regülasyon otomasyonu, davranışsal finans kontrolleri, BIST özel slippage, gerçekçi maliyet simülasyonu, ileri pozisyon ölçekleme.

---

## K142-K148: BIST Regulatory Compliance (Otomatik)

### K142 — VBTS Kademe Kontrolü
Sistem, her sembol için aktif VBTS (Volatilite Bazlı Tedbir Sistemi) kademelerini otomatik kontrol eder. VBTS Tier 1-5'te olan sembollerde sinyal üretilmez.

### K143 — Kısa Satış Yasak
BIST spot piyasada açığa satış (short selling) tamamen yasaktır. `is_short_selling_allowed()` her sembol için `False` döner.

### K144 — Hisse Bazlı Devre Kesici
- Fiyat < 10 TL: ±%5
- 10-50 TL: ±%7.5
- > 50 TL: ±%10
Sınır aşılırsa işlem otomatik RED.

### K145 — Endeks Bazlı Devre Kesici
- BIST100 -%5 → 15 dakika durdurma
- BIST100 -%7 → gün sonuna kadar durdurma

### K146 — Emir/İşlem Oranı
Emir sayısı / işlem sayısı ≥ 3:1 olmalı. Altında ise sistem RED verir.

### K147 — Kredili İşlem Teminat Oranı
Kredili işlemde teminat/position_value ≥ %20 olmalı.

### K148 — Stopaj Vergisi
Temettü (kâr payı) üzerinden %15 stopaj otomatik kesilir.

---

## K149-K154: Behavioral Finance Circuit Breaker

### K149 — Üst Üste 3 Zarar Cooldown
Arka arkaya 3 zararlı işlem → 1 saat cooldown. Yeni sinyaller RED.

### K150 — FOMO Tespiti
Son 5 dakikada fiyat değişimi ≥ %2 ve hacim ortalamasının ≥ 3x üstünde ise pozisyon büyüklüğü %50 azaltılır.

### K151 — Kayıp Kaçınma Uyarısı
Kazançlı işlem süresi / zararlı işlem süresi < 0.5 ise sistem uyarı verir.

### K152 — Günlük Maksimum İşlem Sayısı
Bir günde en fazla 20 işlem. Aşılırsa yeni sinyaller RED.

### K153 — Drawdown Bazlı Pozisyon Ölçekleme
- Drawdown < %5 → 1.0x
- %5 ≤ DD < %10 → 0.5x
- DD ≥ %10 → 0.25x

### K154 — Aşırı Özgüven Kontrolü
Son 10 işlemde 8+ kazanç → bir sonraki işlem büyüklüğü %25 azaltılır.

---

## K155-K158: Advanced BIST Slippage

### K155 — Tick Size Bazlı Yayılma
BIST'te fiyata göre tick size belirlenir. Minimum spread = en az 1 tick.

### K156 — Seans Bazlı Slippage
- Açılış (09:30-09:45): slippage × 2.5
- Sürekli (09:45-17:45): normal
- Kapanış (17:45-18:00): slippage × 1.5

### K157 — Merkezi Limitli Piyasa Etkisi
Emir değeri ≥ 100.000 TL ise slippage %30 azaltılır (mid-point etkisi).

### K158 — Emir Defteri Derinliği
Derinlik < 5 emir → slippage × 1.5

---

## K189-K192: Realistic Fee Simulation

### K189 — BIST İşlem Ücreti
Her yön için %0.0035 BIST işlem ücreti hesaplanır.

### K190 — Takasbank Ücreti
Her yön için %0.001 Takasbank ücreti hesaplanır.

### K191 — Tiered Aracı Kurum Komisyonu
- Aylık hacim < 50.000 TL → %0.15
- 50.000-250.000 TL → %0.12
- > 250.000 TL → %0.10

### K192 — Toplam Round-Trip Maliyet
Minimum round-trip maliyet ≈ %0.50 (aracı kuruma ve hacme göre değişir).

---

## K193-K196: Advanced Position Sizing

### K193 — Fractional Kelly
Kelly kriteri çarpanı varsayılan 0.25'tir. `f* = (bp - q) / b × fraction`.

### K194 — Optimal f (Ralph Vince)
Geometrik ortalama maksimize eden f değeri hesaplanır. Negatif getiri yoksa f=0.

### K195 — Volatility Targeting
Hedef yıllık volatilite %10'dur. `size = base_size × (10% / realized_vol_20d)`.

### K196 — Pozisyon Sınırı
Tüm pozisyon büyüklükleri toplam equity'nin %2'sini geçemez.

---

## CLI Kullanımı

```python
# BIST regülasyon kontrolü
from PYTHON.risk.bist_regulations import BISTRegulatoryChecker
checker = BISTRegulatoryChecker()
result = checker.validate_trade(symbol="THYAO", price=105, reference_price=100, ...)

# Davranışsal kontrol
from PYTHON.risk.behavioral_finance import BehavioralFinanceGuard
guard = BehavioralFinanceGuard()
guard.can_trade(signal)

# BIST slippage
from PYTHON.backtest.bist_slippage import BISTSlippageModel
model = BISTSlippageModel()
slip = model.calculate(order_value=10000, avg_daily_volume=1e6, price=100, session_time="09:30")

# Gerçekçi maliyet
from PYTHON.backtest.fee_simulator import RealisticFeeSimulator
sim = RealisticFeeSimulator()
cost = sim.round_trip(entry_price=100, exit_price=110, size=10)

# Pozisyon ölçekleme
from PYTHON.risk.position_sizing import PositionSizer
sizer = PositionSizer()
size = sizer.size(equity=100000, price=100, method="fractional_kelly", win_rate=0.55, avg_win=100, avg_loss=50)
```

---

*AnatoliaX Trading System v3.2 — K142-K170*
