# K171-K188 — Analitik ve Strateji Kuralları

**Versiyon:** 3.2  
**Tarih:** 2026-05-22  
**Kapsam:** Ensemble optimizasyonu, temel analiz filtresi, piyasa mikro yapısı, OOS validasyon, ileri trade analitikleri.

---

## K171-K174: Multi-Strategy Ensemble Optimizer

### K171 — CVaR Optimizasyonu
Portföy ağırlıkları %95 güven aralığında Conditional Value at Risk'i minimize edecek şekilde optimize edilir.

### K172 — Strateji Korelasyonu
Stratejiler arası korelasyon matrisi sürekli izlenir. Korelasyon > 0.80 olan stratejiler birleştirilir veya RED olarak işaretlenir.

### K173 — Bull Rejim Ağırlıkları
Bull piyasada trend takibi stratejilerine %50, momentum %30, breakout %20 ağırlık verilir.

### K174 — Bear/Sideways Rejim Ağırlıkları
Bear piyasada mean-reversion %50, hedge %50. Sideways'ta mean-reversion %50, hedge %20, diğerleri %30.

---

## K163-K166: Fundamental Analysis Filter

### K163 — Sektör Karşılaştırması
- P/E < sektör ortalaması × 1.2
- P/B < sektör ortalaması × 1.3
- EV/EBITDA < sektör ortalaması × 1.2

### K164 — 3 Yıllık Trend
Net kar artışı yıllık ortalama en az %5 olmalı.

### K165 — KAP Özel Durumlar
Son 30 gün içinde sermaye artırımı veya temettü bildirimi varsa yeşil ışık.

### K166 — Temel Analiz Skoru
Skor < 40 olan sinyaller otomatik RED.

---

## K167-K170: Market Microstructure

### K167 — Sentetik L2 Emir Defteri
Backtest'te 5 derinlik seviyeli sentetik order book simüle edilir.

### K168 — Bid-Ask Bounce
Düşük hacimli hisselerde bounce etkisi `bounce = (high-low)/close × 1/log(volume)` formülüyle hesaplanır.

### K169 — Square-Root Law
Piyasa etkisi: `impact = 0.5 × σ × √(order_size/ADV)`

### K170 — VWAP Benchmark
Execution fiyatı VWAP'tan %0.1 kötü ise flag kalkar.

---

## K159-K162: OOS Test Protocol

### K159 — Walk-Forward
6 ay train, 2 ay validation, 2 ay test (rolling).

### K160 — Rejim Bazlı Backtest
Bull/bear/sideways rejimlerinde ayrı Sharpe/Sortino hesaplanır.

### K161 — Sharpe Enflasyon
In-sample Sharpe / OOS Sharpe > 2.0 → overfitting RED.

### K162 — White's Reality Check
Bootstrap p-value < 0.05 → strateji anlamlı predictive güce sahip.

---

## K184-K188: Advanced Trade Analytics

### K184 — Kazanç/Zarar Serisi
Max win streak, max loss streak, beklenen seri uzunluğu raporlanır.

### K185 — Calmar Ratio
CAGR / Max Drawdown > 0.5 hedeflenir.

### K186 — Omega Ratio
İstenen getiri eşiğinin üstündeki kazançlar / altındaki kayıplar.

### K187 — Trade Attribution
Her sinyal tipi (trend, mean-reversion, breakout) için ayrı getiri/mağlubiyet analizi.

### K188 — Otomatik Raporlama
Günlük/haftalık/aylık performans raporu otomatik üretilir.

---

*AnatoliaX Trading System v3.2 — K159-K188*
