# AnatoliaX Trading System — GitHub Açıklaması

**Versiyon:** 3.2 | **Test:** 657+ test, %80+ coverage | **Lisans:** MIT

---

## TR / Türkçe

### 🏛️ AnatoliaX Nedir?

AnatoliaX, BIST (İstanbul Borsası) ve global piyasalar için geliştirilmiş, **event-driven, çok ajanlı (multi-agent), yapay zeka destekli** profesyonel bir algoritmik trading sistemidir.

**Felsefe:** *"Borsayı yakalamak için çok ajan değil, doğru ajan ve doğru zamanda çalışmak gerekir."*

---

### 🚀 Temel Özellikler

- **3 Ajanlı Konsey:** Sinyal (Teknik + Haber) → Risk (Makro + Limit) → Strateji (3/3 onay)
- **Gold Mining Stratejisi:** Kademeli tier sistemi — MS → S1 → M1 → M5 → M15 → H1 → D1
- **Otomatik Zaman Dilimi Seçimi:** `AdaptiveTierSelector` piyasa koşullarına göre en verimli tier'i otomatik seçer
- **Manuel Çıkış:** Kullanıcı istediği an pozisyonu manuel kapatabilir
- **HFT Modülü:** 1-dakika / 1-saniye tick-level backtest ve latency tracking
- **Nautilus Trader Entegrasyonu:** Event-driven MessageBus, PreTradeRiskEngine, FillModel
- **Paper Trading:** Sanal emir, pozisyon takibi, forward test
- **Manipülasyon Tespiti:** Çoklu zaman dilimi manipülasyon dedektörü
- **Byzantine Consensus:** Güven skoru düşük ajanları otomatik susturma
- **Tam Risk Kontrolü:** Kill Switch, Exposure Limiter, Circuit Breaker, Portfolio Heat

---

### 📊 Gold Mining Tier Sistemi

| Tier | Zaman | Hedef Kar | Tutma | Ajan | Min Sermaye |
|------|-------|-----------|-------|------|-------------|
| MS | 500 ms | %0.01–0.05 | 0.5–3 sn | 1 | 0 TL |
| S1 | 1 saniye | %0.05–0.2 | 3–15 sn | 1 | 1.000 TL |
| M1 | 1 dakika | %0.3–1.0 | 30–120 sn | 2 | 5.000 TL |
| M5 | 5 dakika | %0.8–2.0 | 2–10 dk | 2 | 12.000 TL |
| M15 | 15 dakika | %1.5–5.0 | 5–30 dk | 3 | 25.000 TL |
| H1 | 1 saat | %2.0–6.0 | 1–4 saat | 3 | 50.000 TL |
| D1 | 1 gün | %5.0–15.0 | 1–5 gün | 3 | 100.000 TL |

**Kademeli Aktivasyon:** Sistem MS tier'dan başlar, sermaye ve kazanma oranı arttıkça otomatik olarak üst tier'lara geçer. Zarar zinciri oluşursa otomatik olarak alt tier'a düşer (fallback).

---

### 🛡️ Güvenlik ve Kurallar

- **K91:** TradingView birincil veri kaynağı
- **K92:** "Yalan asla yok" — her fiyat yanında kaynak ve zaman damgası
- **K141:** Piyasa kapalı = işlem yok
- **K143:** Emir validasyonu zorunlu
- `.env`'den API key çekme, kodda asla secret yazma
- SQLite / PostgreSQL / ChromaDB desteği

---

### 🖥️ Kurulum

```bash
# Python bağımlılıkları
cd PYTHON
pip install -r requirements.txt

# Veritabanı
python main.py --init-db

# Docker (opsiyonel)
docker-compose up -d
```

---

### ⚡ Kullanım

```bash
# Sinyal tarama
python main.py --scan THYAO,GARAN,ASELS

# Gold Mining kademeli strateji
python main.py --gold-mining
python main.py --gold-scan THYAO,GARAN --gold-tier M1 --gold-capital 50000

# Backtest
python main.py --backtest data/THYAO.csv --symbol THYAO

# Portföy monitörü
python main.py --monitor

# Testler
cd PYTHON
pytest tests/ -v
```

---

### 🧠 Mimari

```
Veri Kaynakları (Yahoo, TradingView, Bigpara, KAP)
         |
    FeedAggregator
         |
    +----+----+----+
    |    |    |    |
 Sinyal Risk Makro Haber
    |    |    |    |
    +----+----+----+
         |
    Strateji Ajan (3/3 onay + Byzantine Consensus)
         |
    +----+----+
    |         |
 Paper     Canli Emir
 Trading   (Broker API)
    |
 SQLite / PostgreSQL
```

---

### 📁 Proje Yapısı

```
AnatoliaX-Trading-System/
├── PYTHON/                # Python backtest, analitik, risk motoru
│   ├── main.py           # CLI orchestrator
│   ├── strategy/         # Stratejiler (Gold Mining, HFT, vb.)
│   ├── backtest/         # Vektörize + event-driven backtest
│   ├── paper_trading/    # Paper broker + signal engine
│   ├── hft/              # Tick-level HFT modülü
│   ├── data/             # Fetcher, catalog, instrument provider
│   ├── risk/             # Position, Account, PreTradeRiskEngine
│   ├── execution/        # UnifiedExecutionEngine, order types
│   ├── agents/           # Orchestrator, Q-learning memory
│   ├── analytics/        # Volume anomaly, BB+volume combo
│   ├── memory/           # ChromaDB embedding
│   ├── telegram/         # Reporter bot
│   ├── observability/    # JSON logging, Prometheus metrics
│   ├── common/           # MessageBus, events, validators
│   └── tests/            # 657+ pytest
├── SCRIPTS/              # Node.js motor (opsiyonel)
├── KURALLAR/             # K1-K141 kurallar ve Gold Mining kuralları
├── AJANLAR/              # Ajan kuralları
├── CONFIG/               # Yapılandırma
├── README.md
├── LICENSE
├── .gitignore
├── Dockerfile
└── docker-compose.yml
```

---

### 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/xyz`)
3. Testleri çalıştırın (`pytest tests/`)
4. Pull Request açın

---

### ⚠️ Sorumluluk Reddi

Bu sistem **eğitim ve araştırma** amaçlıdır.
- Gerçek para ile kullanmadan önce paper trade yapın.
- Finansal tavsiye değildir.
- Tüm risk kullanıcıya aittir.

---

## EN / English

**AnatoliaX** is an event-driven, multi-agent AI trading system for BIST (Istanbul Stock Exchange) and global markets.

- **3-Agent Council:** Signal → Risk → Strategy (3/3 consensus)
- **Gold Mining Strategy:** Progressive tier system (MS → S1 → M1 → M5 → M15 → H1 → D1)
- **Adaptive Tier Selector:** Auto-selects best timeframe based on market conditions
- **Manual Exit:** User can close positions at any time
- **HFT Module:** Tick-level backtest and latency tracking
- **Full Risk Controls:** Kill Switch, Exposure Limiter, Circuit Breaker
- **Manipulation Detection:** Multi-timeframe scanner
- **Byzantine Consensus:** Auto-mutes low-trust agents

**Version:** 3.2 | **Tests:** 657+ | **License:** MIT

---

*AnatoliaX Trading System — Sadakat. Güven. Kusursuzluk.*
