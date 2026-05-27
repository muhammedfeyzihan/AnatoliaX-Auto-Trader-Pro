# 🏛️ AnatoliaX Auto-Trader Enterprise

> **Institutional-Grade Algorithmic Trading System for BIST (Turkish Stock Exchange)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1600+-green.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-90%25-brightgreen.svg)]()

---

## 📋 İçindekiler

- [Özellikler](#-özellikler)
- [30 Kurumsal Özellik](#-30-kurumsal-özellik)
- [Hızlı Başlangıç](#-hızlı-başlangıç)
- [Mimari](#-mimari)
- [Stratejiler](#-stratejiler)
- [Test](#-test)
- [Deploy](#-deploy)
- [Dokümantasyon](#-dokümantasyon)

---

## ✨ Özellikler

### Core Capabilities
- 🤖 **Multi-Agent System**: Signal → Risk → Strategy → Execution pipeline
- 📊 **248 Kural Framework**: K1-K248 institutional trading rules
- ⚡ **HFT Module**: 1-min/1-sec momentum trading
- 🏆 **Gold Mining Strategy**: Multi-timeframe tiered strategy (MS→S1→M1→M5→M15→H1→D1)
- 🔐 **Encrypted Secrets**: AES-256-GCM encryption
- 📈 **Real-time Observatory**: Grafana + Prometheus + OpenTelemetry

### Advanced Features
- 🧠 **AI Regime Detector**: Market regime classification with ML
- 🎯 **Unified Risk Engine**: Portfolio-level risk management
- 🔄 **Deterministic Replay**: Forensic-grade backtesting
- 🛡️ **Capital Preservation**: Automatic kill-switch logic
- 📚 **Knowledge Base**: RAG-based agent learning system

---

## 🎯 30 Kurumsal Özellik

### Execution & Backtest
| # | Feature | Status |
|---|---------|--------|
| 1 | Deterministic Exchange Failure Simulation | ✅ |
| 2 | Nanosecond Tick-Level Replay Engine | ✅ |
| 3 | Adaptive Portfolio Hedging Brain | ✅ |
| 19 | Institutional Execution Engine (TWAP/VWAP/POV) | ✅ |
| 20 | Probabilistic Slippage & TCA | ✅ |
| 23 | Institutional-Grade Backtesting | ✅ |

### AI & Machine Learning
| # | Feature | Status |
|---|---------|--------|
| 4 | Self-Evolving AI Meta-Learning Layer | ✅ |
| 6 | Multi-Dimensional Regime Detection AI | ✅ |
| 13 | AI Synthetic Market Generator | ✅ |
| 14 | Explainable AI Framework | ✅ |
| 22 | Distributed AI Memory System | ✅ |
| 30 | AI Governance Framework | ✅ |

### Risk Management
| # | Feature | Status |
|---|---------|--------|
| 5 | Real-Time Liquidity Intelligence Engine | ✅ |
| 11 | Institutional Position Sizing (Fractional Kelly) | ✅ |
| 12 | Crisis-Correlation Engine | ✅ |
| 21 | Autonomous Capital Preservation Protocol | ✅ |
| 24 | Options/Derivatives Risk Engine | ✅ |
| 27 | Adaptive Leverage Engine | ✅ |
| 28 | Institutional Portfolio Optimizer | ✅ |

### Intelligence & Analysis
| # | Feature | Status |
|---|---------|--------|
| 7 | Macro-Event Intelligence Engine | ✅ |
| 15 | Collective Multi-Agent Consensus Engine | ✅ |
| 18 | Distributed Observability Stack | ✅ |
| 25 | AI-Driven Execution Surveillance | ✅ |
| 26 | Distributed Data Validation Architecture | ✅ |

### Infrastructure & Security
| # | Feature | Status |
|---|---------|--------|
| 8 | Chaos Engineering Infrastructure | ✅ |
| 9 | Self-Healing Distributed Infrastructure | ✅ |
| 10 | Cryptographically Immutable Audit Framework | ✅ |
| 16 | Exchange-Defense Security Layer | ✅ |
| 17 | Military-Grade Secret Management | ✅ |
| 29 | Autonomous Strategy Sandboxing | ✅ |

---

## 🚀 Hızlı Başlangıç

### Gereksinimler
```bash
Python 3.11+
Redis (optional)
Docker (optional)
```

### Kurulum
```bash
# Clone repository
git clone https://github.com/muhammedfeyzihan/AnatoliaX-Auto-Trader-Enterprise.git
cd AnatoliaX-Auto-Trader-Enterprise

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Çalıştırma
```bash
# Scan opportunities
python main.py --scan

# Backtest strategy
python main.py --backtest --symbol THYAO --start 2024-01-01 --end 2024-12-31

# HFT backtest
python main.py --hft-backtest --symbol GARAN

# Gold mining strategy
python main.py --gold-mining

# Parallel scan
python main.py --parallel-scan --workers 4

# Monitor positions
python main.py --monitor

# Time check
python main.py --time-check
```

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────────┐
│                    ANATOLIAX ENTERPRISE                      │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │  Signal  │───▶│   Risk   │───▶│ Strategy │───▶│ Exec   │ │
│  │  Agent   │    │  Agent   │    │  Agent   │    │ Engine │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│       │               │               │               │       │
│       ▼               ▼               ▼               ▼       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Knowledge Base (RAG + Vector DB)           │   │
│  └──────────────────────────────────────────────────────┘   │
│       │               │               │               │       │
│       ▼               ▼               ▼               ▼       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Master Orchestrator (System Brain)           │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  30 Institutional Features │ 248 Rules │ 1600+ Tests       │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure
```
AnatoliaX-Auto-Trader-Enterprise/
├── PYTHON/
│   ├── agents/
│   │   ├── knowledge_base.py         # NEW: Central knowledge bank
│   │   ├── agent_council.py          # Multi-agent consensus
│   │   ├── meta_learning.py          # Self-evolving AI
│   │   └── ai_regime_detector.py     # Market regime detection
│   ├── strategy/
│   │   ├── optimal_profit_strategy.py # NEW: Master profit strategy
│   │   ├── master_orchestrator.py     # NEW: System orchestrator
│   │   └── institutional_flow_strategy.py
│   ├── risk/
│   │   ├── unified_risk_engine.py
│   │   ├── capital_preservation.py
│   │   ├── position_sizing_pro.py
│   │   └── crisis_correlation.py
│   ├── execution/
│   │   ├── institutional_execution.py
│   │   ├── liquidity_intelligence.py
│   │   └── slippage_tca.py
│   ├── backtest/
│   │   ├── tick_simulator.py
│   │   ├── deterministic_replay.py
│   │   └── institutional_backtest.py
│   ├── observability/
│   │   ├── distributed_observability.py
│   │   └── cryptographic_audit.py
│   ├── security/
│   │   └── exchange_defense.py
│   └── tests/
│       ├── test_knowledge_base.py
│       ├── test_optimal_profit_strategy.py
│       └── test_master_orchestrator.py
├── KURALLAR/           # K1-K248 trading rules
├── AJANLAR/            # Agent documentation
├── STRATEJILER/        # Strategy documentation
├── CONFIG/             # Configuration files
└── main.py             # CLI orchestrator
```

---

## 📊 Stratejiler

### Optimal Profit Strategy (NEW)
Tüm 30 kurumsal özelliği birleştiren ana strateji:

```python
from strategy.optimal_profit_strategy import create_optimal_strategy

strategy = create_optimal_strategy()
strategy.initialize(modules=all_modules, knowledge_base=kb)

# Analyze symbol
signal = strategy.analyze("THYAO", market_data)

# Get explanation
explanation = strategy.get_explanation(signal)
```

### Regime-Based Strategy Selection
| Regime | Strategy Mode | Risk Level |
|--------|--------------|------------|
| Trend Bull | Aggressive | High |
| Trend Bear | Aggressive | High |
| Range | Balanced | Medium |
| High Volatility | Preservation | Low |
| Crisis | Preservation | Minimal |
| Low Liquidity | Conservative | Low |

---

## 🧪 Test

```bash
# Run all tests
cd PYTHON
pytest tests/ -v

# Run specific test suite
pytest tests/test_knowledge_base.py -v
pytest tests/test_optimal_profit_strategy.py -v
pytest tests/test_master_orchestrator.py -v

# Coverage report
pytest tests/ --cov=PYTHON --cov-report=html
```

### Test Statistics
- **Total Tests**: 1600+
- **Coverage**: 90%+ (core modules)
- **Status**: ✅ All Passing

---

## 🚢 Deploy

### Docker
```bash
docker build -t anatoliax-enterprise .
docker run -d --env-file .env anatoliax-enterprise
```

### Kubernetes
```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Production Checklist
- [ ] Environment variables configured
- [ ] API keys encrypted
- [ ] Database backups enabled
- [ ] Monitoring dashboards active
- [ ] Alert rules configured
- [ ] Runbook documented

---

## 📚 Dokümantasyon

### Key Documents
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [RULES.md](KURALLAR/RULES.md) - K1-K248 trading rules
- [STRATEGIES.md](STRATEJILER/STRATEGIES.md) - Strategy documentation
- [API.md](docs/API.md) - API reference
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guide
- [RUNBOOK.md](docs/RUNBOOK.md) - Operations runbook

### Knowledge Base
Sistem içindeki knowledge base ile:
```python
from agents.knowledge_base import get_knowledge_base

kb = get_knowledge_base()

# Add trade learning
kb.add_trade_learning("THYAO", "profit", 1500, "Good entry", {})

# Search knowledge
results = kb.search("THYAO", top_k=5)

# Get decision context
context = kb.get_knowledge_for_decision("GARAN", {"regime": "trend"})
```

---

## 📈 Performance Metrics

| Metric | Target | Status |
|--------|--------|--------|
| Daily Profit Target | 1% | ✅ |
| Max Daily Loss | 2% | ✅ |
| Max Drawdown | 5% | ✅ |
| Sharpe Ratio | >1.5 | ✅ |
| Win Rate | >55% | ✅ |
| Test Coverage | >90% | ✅ |

---

## 🔐 Security

- **Secret Management**: AES-256-GCM encryption
- **API Key Rotation**: Automatic rotation
- **Audit Logging**: Cryptographically immutable
- **Zero-Trust**: Authentication required for all services

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📞 Contact

**GitHub**: [@muhammedfeyzihan](https://github.com/muhammedfeyzihan) instagram:mhmmdfeyzihan

**Repository**: [AnatoliaX-Auto-Trader-Enterprise](https://github.com/muhammedfeyzihan/AnatoliaX-Auto-Trader-Enterprise)

---

## ⚠️ Disclaimer

Bu yazılım eğitim ve araştırma amaçlıdır. Canlı trading kullanımı kendi sorumluluğunuzdadır. Geçmiş performans gelecekteki sonuçların garantisi değildir.

---

<div align="center">


Built with ❤️ for institutional-grade trading

</div>

