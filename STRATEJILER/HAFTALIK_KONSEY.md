# Haftalik Strateji Konseyi (Weekly Strategy Council)

**Versiyon:** 3.2  
**Aktif:** Her Cumartesi  
**Ajanlar:** Sinyal + Risk + Strateji (Telegram rapor)

---

## Amaç

Her hafta sonu, sistem kendini degerlendirir. Gecen hafta ne calisti, ne calismadi? Hangi setup kazandirdi? Hangi zaman diliminde kar ettik? Risk profili nasildi?

Bu verileri birlestirerek yeni hafta icin:
- **Hedef carpani** (1x, 2x, 4x, 8x)
- **Birincil strateji** (trend/mean-reversion/scalping)
- **Zaman dilimi** (M5, M15, H1, D1)
- **Pozisyon olcegi** (tam, %75, yari)

belirleriz.

---

## Konsey Akisi

```
Pazartesi-Cuma  Islem verileri toplanir (SQLite)
Cumartesi       WeeklyCouncil.convene() cagrillir
                |-- Sinyal Ajan raporu
                |-- Risk Ajan raporu
                |-- Strateji Ajan raporu
                |-- 3/3 Onay oylamasi
                |-- Nihai karar (CouncilDecision)
                |-- Telegram raporu
Pazartesi       Yeni strateji aktif olur
```

---

## Matematiksel Model

### Hedef Carpani (Target Multiplier)

```
If Net PnL > 0:   multiplier = min(prev * 2.0, 8.0)
If Net PnL < 0:   multiplier = max(prev * 0.5, 0.25)
If Net PnL = 0:   multiplier = prev
```

**Ornek:**

| Hafta | Net PnL | Onceki Carpani | Yeni Carpani | Aciklama |
|---|---|---|---|---|
| 1 | +500 | 1.0 | 2.0 | Kazandi, x2 |
| 2 | +1200 | 2.0 | 4.0 | Kazandi, x2 |
| 3 | -300 | 4.0 | 2.0 | Zarar, /2 |
| 4 | +800 | 2.0 | 4.0 | Kazandi, x2 |
| 5 | -100 | 4.0 | 2.0 | Zarar, /2 |
| 6 | +50 | 2.0 | 4.0 | Kazandi, x2 |
| 7 | +200 | 4.0 | 8.0 | Kazandi, x2 (cap) |
| 8 | -500 | 8.0 | 4.0 | Zarar, /2 |

### Risk Olcegi (Position Scale)

```
Max DD < %2    → 1.0x (tam pozisyon)
%2 <= DD < %5  → 0.75x
DD >= %5       → 0.5x  (yarim pozisyon)
```

### Strateji Secimi

```
Bull  + Dusuk risk → trend_following + H1/D1
Bear  + Yuksek risk → mean_reversion + hedge + M15/H1
Sideways + Notr → scalping_range + M5/M15
```

---

## Onay Mekanizmasi (3/3)

Tum ajanlar APPROVE vermezse karar RED olur.

**Sinyal Ajan APPROVE kosullari:**
- Win rate >= %40
- En az 1 setup net kazanci pozitif
- En iyi zaman dilimi tespit edilmis

**Risk Ajan APPROVE kosullari:**
- Max drawdown <= %5
- Volatilite annualized < %30
- Ust ustte zarar sayisi < 5

**Strateji Ajan:**
- Daima APPROVE (sadece veri birlestirir)

---

## CLI Kullanimi

```bash
# Haftalik konseyi calistir
python PYTHON/main.py --weekly-council

# Manuel konsey (gecmis veri ile)
python -c "
from PYTHON.agents.weekly_council import WeeklyCouncil
import pandas as pd, numpy as np
council = WeeklyCouncil()
trades = pd.DataFrame({
    'net_pnl': [100, -50, 80, -30, 120],
    'setup': ['breakout', 'breakout', 'trend', 'mean_rev', 'trend'],
    'timeframe': ['M5', 'M5', 'H1', 'M15', 'H1'],
})
equity = pd.Series(100 + np.cumsum(trades['net_pnl']))
d = council.convene('2026-05-12', '2026-05-16', trades, equity)
print(council.to_markdown(d))
"
```

---

## Bagimli Moduller

| Modul | Dosya | Gorev |
|---|---|---|
| WeeklyCouncil | `PYTHON/agents/weekly_council.py` | Ana motor |
| TradeAnalytics | `PYTHON/analytics/trade_analytics.py` | Streak/Calmar/Omega analizi |
| EnsembleOptimizer | `PYTHON/strategy/ensemble_optimizer.py` | Strateji agirliklari |
| BehavioralFinanceGuard | `PYTHON/risk/behavioral_finance.py` | Behavioral metrikler |
| PositionSizer | `PYTHON/risk/position_sizing.py` | Kelly + vol targeting |

---

*AnatoliaX Trading System v3.2*
