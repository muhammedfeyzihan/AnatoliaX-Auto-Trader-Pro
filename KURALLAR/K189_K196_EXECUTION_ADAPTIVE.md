# K189-K196 — Execution ve Adaptive Learning Kuralları

**Versiyon:** 3.2  
**Tarih:** 2026-05-22  
**Kapsam:** Paper/live ayrımı, execution kalite skoru, online learning, concept drift.

---

## K179-K183: Paper/Live Separator + Execution Quality Score

### K179 — Paper/Live Motor Ayrımı
Paper trading ve live trading ayrı motorlarda çalışır. Aynı sinyal girdisi her iki motora beslenir.

### K180 — Paper/Live PnL Reconciliation
Her gün paper PnL ile live PnL karşılaştırılır. Fark > %1 → günlük uyarı.

### K181 — Live Latency İzleme
Emir gönderimden fill'e kadar geçen süre P50/P95/P99 olarak izlenir.

### K182 — Execution Quality Score (EQS)
`EQS = 0.30×fill_rate + 0.25×(1-slippage) + 0.25×(1-latency/max) + 0.20×(1-market_impact)`

### K183 — EQS Eşiği
EQS < 70 → broker değerlendirmesi yapılır.

---

## K175-K178: Adaptive Online Learning

### K175 — Incremental Online Learning
Her işlem sonrası model tek örnek ile güncellenir. Batch learning yasak.

### K176 — Concept Drift Detection
ADWIN benzeri pencereleme ile P&L ortalaması kayması tespit edilir. Threshold = %5.

### K177 — PnL-Driven Feature Importance
Her feature'ın kazançlı/zararlı işlemlere katkısı ağırlıklandırılır. Ağırlığı düşen feature'lar otomatik atılır.

### K178 — Model Reset
Drift tespit edilirse model sıfırlanır ve 100 örnek beklemeden yeni sinyal üretilmez.

---

## K189-K192: Realistic Fee Simulation (Devam)

### K189 — BIST İşlem Ücreti
%0.0035 her yön.

### K190 — Takasbank Ücreti
%0.001 her yön.

### K191 — Tiered Brokerage
Hacme göre değişen komisyon oranları.

### K192 — Toplam Round-Trip
Min %0.50 maliyet.

---

## K193-K196: Advanced Position Sizing (Devam)

### K193 — Fractional Kelly
Default fraction 0.25.

### K194 — Optimal f
Ralph Vince geometrik ortalama maksimizasyonu.

### K195 — Volatility Targeting
Hedef yıllık volatilite %10.

### K196 — Pozisyon Sınırı
Max %2 equity.

---

*AnatoliaX Trading System v3.2 — K189-K196*
