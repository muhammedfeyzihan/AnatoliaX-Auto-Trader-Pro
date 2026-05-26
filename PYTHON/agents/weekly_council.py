"""
weekly_council.py — Haftalik Strateji Konseyi (Weekly Strategy Council)
K197-K203: Cumartesi toplanti, ajan birlikteligi, haftalik hedef carpani,
gecmis tecrube birlestirme, garanti en hizli para kazanma yolu.
"""

import json
import math
import statistics
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np


@dataclass
class WeeklyReport:
    """Tek bir haftanin raporu."""
    week_start: str  # ISO date YYYY-MM-DD
    week_end: str
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    best_setup: str = ""
    worst_setup: str = ""
    regime: str = ""  # bull / bear / sideways
    target_multiplier: float = 1.0


@dataclass
class CouncilDecision:
    """Konseyin nihai karari."""
    week_start: str
    week_end: str
    approved: bool = False
    target_multiplier: float = 1.0
    position_scale: float = 1.0
    suggested_timeframes: List[str] = field(default_factory=list)
    primary_strategy: str = ""
    risk_adjustments: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    agent_votes: Dict[str, str] = field(default_factory=dict)


class WeeklyCouncil:
    """
    3 ajan (Sinyal / Risk / Strateji) cumartesi gunu bir araya gelir.
    Gecen haftanin ve onceki haftalarin verilerini analiz edip
    yeni hafta icin optimal stratejiyi belirler.
    """

    # Hedef carpani katlari
    MULTIPLIER_UP = 2.0
    MULTIPLIER_DOWN = 0.5
    MULTIPLIER_CAP = 8.0
    MULTIPLIER_FLOOR = 0.25

    # Risk limitleri
    MAX_DD_PCT = 0.05
    KELLY_FRACTION = 0.25

    def __init__(self, history_weeks: int = 8):
        self.history_weeks = history_weeks
        self._weekly_reports: List[WeeklyReport] = []
        self._last_council_date: Optional[str] = None

    # ── Raporlama (Sinyal Ajan) ────────────────────────────

    def signal_agent_report(self, trades_df: pd.DataFrame) -> Dict:
        """
        Sinyal Ajan: Hangi setup'lar calisti, hangi zaman dilimleri kazandirdi?
        """
        if trades_df.empty:
            return {"best_setup": "", "worst_setup": "", "win_rate": 0.0}

        wins = trades_df[trades_df["net_pnl"] > 0]
        losses = trades_df[trades_df["net_pnl"] <= 0]

        # Setup bazli analiz
        if "setup" in trades_df.columns:
            setup_stats = trades_df.groupby("setup").agg(
                count=("net_pnl", "count"),
                win_rate=("net_pnl", lambda x: (x > 0).mean()),
                total_pnl=("net_pnl", "sum"),
            )
            setup_stats = setup_stats[setup_stats["count"] >= 3]  # en az 3 islem
            if not setup_stats.empty:
                best = setup_stats.sort_values("total_pnl", ascending=False).index[0]
                worst = setup_stats.sort_values("total_pnl").index[0]
            else:
                best = worst = ""
        else:
            best = worst = ""

        # Zaman dilimi bazli analiz
        timeframes = {}
        if "timeframe" in trades_df.columns:
            tf_stats = trades_df.groupby("timeframe")["net_pnl"].sum().sort_values(ascending=False)
            timeframes = tf_stats.to_dict()

        return {
            "best_setup": best,
            "worst_setup": worst,
            "win_rate": len(wins) / len(trades_df) if len(trades_df) > 0 else 0.0,
            "total_trades": len(trades_df),
            "timeframe_pnl": timeframes,
        }

    # ── Risk Ajan Raporu ────────────────────────────────────

    def risk_agent_report(self, equity_series: pd.Series, trades_df: pd.DataFrame) -> Dict:
        """
        Risk Ajan: Drawdown, volatilite, behavioral metrikler.
        """
        if len(equity_series) < 2:
            return {"max_dd": 0.0, "regime": "sideways", "volatility": 0.0}

        returns = equity_series.pct_change().dropna()
        max_dd = self._max_drawdown(equity_series)
        vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.0

        # Rejim tespiti (ADX + SMA proxy)
        regime = self._detect_regime(equity_series)

        # Behavioral
        consecutive_losses = 0
        max_cl = 0
        for pnl in trades_df["net_pnl"] if not trades_df.empty else []:
            if pnl < 0:
                consecutive_losses += 1
                max_cl = max(max_cl, consecutive_losses)
            else:
                consecutive_losses = 0

        return {
            "max_dd": max_dd,
            "regime": regime,
            "volatility": vol,
            "max_consecutive_losses": max_cl,
            "risk_level": "HIGH" if max_dd > 0.08 or vol > 0.30 else "MEDIUM" if max_dd > 0.04 else "LOW",
        }

    def _max_drawdown(self, equity: pd.Series) -> float:
        peak = equity.expanding(min_periods=1).max()
        dd = (peak - equity) / peak
        return dd.max()

    def _detect_regime(self, equity: pd.Series) -> str:
        if len(equity) < 50:
            return "sideways"
        sma50 = equity.rolling(window=50, min_periods=1).mean()
        sma200 = equity.rolling(window=200, min_periods=1).mean()
        current_sma50 = sma50.iloc[-1]
        current_sma200 = sma200.iloc[-1]
        # Basit rejim
        if current_sma50 > current_sma200 * 1.02:
            return "bull"
        elif current_sma50 < current_sma200 * 0.98:
            return "bear"
        return "sideways"

    # ── Strateji Ajan Raporu ───────────────────────────────

    def strategy_agent_report(
        self,
        signal_report: Dict,
        risk_report: Dict,
        previous_reports: List[WeeklyReport],
    ) -> Dict:
        """
        Strateji Ajan: Gecmis verileri birlestirerek hedef carpani ve stratejiyi belirler.
        """
        n_weeks = len(previous_reports)
        if n_weeks == 0:
            return {
                "target_multiplier": 1.0,
                "position_scale": 1.0,
                "primary_strategy": "balanced",
                "suggested_timeframes": ["H1", "D1"],
                "reasoning": "Yeterli gecmis veri yok. Varsayilan strateji.",
                "agent_votes": {"Sinyal": "APPROVE", "Risk": "APPROVE", "Strateji": "APPROVE"},
                "approved": True,
            }

        # Son haftanin performansi
        last = previous_reports[-1]

        # Hedef carpani mantigi:
        # Kazandiysak x2, kayip ettiysek /2 (asagi sinir 0.25)
        # Ust sinir 8.0
        current_mult = last.target_multiplier

        if last.net_pnl > 0:
            new_mult = min(current_mult * self.MULTIPLIER_UP, self.MULTIPLIER_CAP)
            mult_reason = f"Kazanc haftasi ({last.net_pnl:+.2f}). Carpani {current_mult} -> {new_mult}"
        elif last.net_pnl < 0:
            new_mult = max(current_mult * self.MULTIPLIER_DOWN, self.MULTIPLIER_FLOOR)
            mult_reason = f"Zarar haftasi ({last.net_pnl:+.2f}). Carpani {current_mult} -> {new_mult}"
        else:
            new_mult = current_mult
            mult_reason = "Notr hafta. Carpani sabit."

        # Risk bazli pozisyon olcekleme
        if risk_report["max_dd"] > self.MAX_DD_PCT:
            scale = 0.5
            scale_reason = f"Max DD {risk_report['max_dd']*100:.1f}% > {self.MAX_DD_PCT*100:.0f}%, pozisyon yariya indirildi."
        elif risk_report["risk_level"] == "HIGH":
            scale = 0.5
            scale_reason = "Yuksek risk rejimi, pozisyon yariya indirildi."
        elif risk_report["risk_level"] == "MEDIUM":
            scale = 0.75
            scale_reason = "Orta risk, pozisyon %75."
        else:
            scale = 1.0
            scale_reason = "Dusuk risk, tam pozisyon."

        # Strateji secimi
        regime = risk_report["regime"]
        if regime == "bull":
            primary = "trend_following"
            timeframes = ["H1", "D1"]
        elif regime == "bear":
            primary = "mean_reversion_hedge"
            timeframes = ["M15", "H1"]
        else:
            primary = "scalping_range"
            timeframes = ["M5", "M15"]

        # En iyi zaman dilimini sinyal raporundan al
        tf_pnl = signal_report.get("timeframe_pnl", {})
        if tf_pnl:
            best_tf = max(tf_pnl, key=tf_pnl.get)
            if best_tf not in timeframes:
                timeframes.insert(0, best_tf)

        # 3/3 onay kontrolu
        vote_signal = "APPROVE" if signal_report["win_rate"] >= 0.4 else "REJECT"
        vote_risk = "APPROVE" if risk_report["risk_level"] != "HIGH" else "REJECT"
        vote_strategy = "APPROVE"
        all_approve = vote_signal == vote_risk == vote_strategy == "APPROVE"

        reasoning = (
            f"Hafta: {last.week_start} - {last.week_end}. "
            f"Net PnL: {last.net_pnl:+.2f}. "
            f"Rejim: {regime}. "
            f"Best setup: {signal_report.get('best_setup', 'N/A')}. "
            f"{mult_reason} {scale_reason}"
        )

        return {
            "target_multiplier": round(new_mult, 2),
            "position_scale": scale,
            "primary_strategy": primary,
            "suggested_timeframes": timeframes[:3],
            "reasoning": reasoning,
            "agent_votes": {
                "Sinyal": vote_signal,
                "Risk": vote_risk,
                "Strateji": vote_strategy,
            },
            "approved": all_approve,
        }

    # ── Konsey Toplantisi ──────────────────────────────────

    def convene(
        self,
        week_start: str,
        week_end: str,
        trades_df: pd.DataFrame,
        equity_series: pd.Series,
    ) -> CouncilDecision:
        """
        Cumartesi gunu cagirilir. Tum ajanlarin raporlarini birlestirir.
        Once mevcut haftayi arsive ekler, sonra gecmis verilerle strateji belirler.
        """
        signal_r = self.signal_agent_report(trades_df)
        risk_r = self.risk_agent_report(equity_series, trades_df)

        # Mevcut haftayi arsive ekle (eger veri varsa)
        if not trades_df.empty:
            wins = trades_df[trades_df["net_pnl"] > 0]
            losses = trades_df[trades_df["net_pnl"] <= 0]
            report = WeeklyReport(
                week_start=week_start,
                week_end=week_end,
                total_trades=len(trades_df),
                win_count=len(wins),
                loss_count=len(losses),
                gross_profit=wins["net_pnl"].sum() if len(wins) > 0 else 0,
                gross_loss=abs(losses["net_pnl"].sum()) if len(losses) > 0 else 0,
                net_pnl=trades_df["net_pnl"].sum(),
                max_drawdown=risk_r["max_dd"],
                sharpe=0.0,
                best_setup=signal_r.get("best_setup", ""),
                worst_setup=signal_r.get("worst_setup", ""),
                regime=risk_r["regime"],
                target_multiplier=1.0,  # default, strategy_agent_report belirler
            )
            self._weekly_reports.append(report)
            self._weekly_reports = self._weekly_reports[-self.history_weeks:]

        # Gecmis verilerle strateji belirle (mevcut hafta dahil)
        strategy_r = self.strategy_agent_report(signal_r, risk_r, self._weekly_reports)

        # Son eklenen raporun carpani guncelle
        if self._weekly_reports:
            self._weekly_reports[-1].target_multiplier = strategy_r["target_multiplier"]

        self._last_council_date = datetime.now(timezone.utc).isoformat()

        return CouncilDecision(
            week_start=week_start,
            week_end=week_end,
            approved=strategy_r["approved"],
            target_multiplier=strategy_r["target_multiplier"],
            position_scale=strategy_r["position_scale"],
            suggested_timeframes=strategy_r["suggested_timeframes"],
            primary_strategy=strategy_r["primary_strategy"],
            risk_adjustments={
                "max_dd_limit": self.MAX_DD_PCT,
                "kelly_fraction": self.KELLY_FRACTION,
                "position_scale": strategy_r["position_scale"],
            },
            reasoning=strategy_r["reasoning"],
            agent_votes=strategy_r["agent_votes"],
        )

    # ── Cikti Formatlari ───────────────────────────────────

    def to_json(self, decision: CouncilDecision) -> str:
        return json.dumps(asdict(decision), ensure_ascii=False, indent=2)

    def to_markdown(self, decision: CouncilDecision) -> str:
        lines = [
            "# Haftalik Strateji Konseyi Karari",
            f"**Donem:** {decision.week_start} -- {decision.week_end}",
            f"**Onay:** {'EVET (3/3)' if decision.approved else 'HAYIR'}",
            "",
            "## Hedefler",
            f"- **Hedef Carpani:** {decision.target_multiplier}x",
            f"- **Pozisyon Olcegi:** {decision.position_scale}",
            f"- **Birincil Strateji:** {decision.primary_strategy}",
            f"- **Onerilen Zaman Dilimleri:** {', '.join(decision.suggested_timeframes)}",
            "",
            "## Risk Ayarlari",
        ]
        for k, v in decision.risk_adjustments.items():
            lines.append(f"- **{k}:** {v}")
        lines.extend([
            "",
            "## Ajan Oylari",
        ])
        for agent, vote in decision.agent_votes.items():
            lines.append(f"- **{agent}:** {vote}")
        lines.extend([
            "",
            "## Gerekce",
            f"> {decision.reasoning}",
        ])
        return "\n".join(lines)

    # ── Rapor Arsivi ───────────────────────────────────────

    def get_history_summary(self) -> Dict:
        """Onceki haftalarin ozeti."""
        if not self._weekly_reports:
            return {"message": "Gecmis veri yok."}

        total_trades = sum(r.total_trades for r in self._weekly_reports)
        total_wins = sum(r.win_count for r in self._weekly_reports)
        total_pnl = sum(r.net_pnl for r in self._weekly_reports)
        avg_multiplier = statistics.mean(r.target_multiplier for r in self._weekly_reports)

        return {
            "weeks_analyzed": len(self._weekly_reports),
            "total_trades": total_trades,
            "total_win_rate": round(total_wins / total_trades, 4) if total_trades > 0 else 0,
            "total_net_pnl": round(total_pnl, 2),
            "avg_target_multiplier": round(avg_multiplier, 2),
            "best_week": max(self._weekly_reports, key=lambda r: r.net_pnl).week_start,
            "worst_week": min(self._weekly_reports, key=lambda r: r.net_pnl).week_start,
        }
