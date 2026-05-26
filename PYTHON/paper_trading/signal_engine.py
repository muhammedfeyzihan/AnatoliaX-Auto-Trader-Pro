"""
AnatoliaX Signal Engine (Paper Trading)
Canli veri uzerinden sinyal uretimi + risk kontrolu + sanal emir.

Kullanim:
    from paper_trading.signal_engine import SignalEngine
    engine = SignalEngine()
    engine.run_scan(symbols=["THYAO", "GARAN", "ASELS"])

Calisma Akisi:
    1. Canli veri cek (FeedAggregator)
    2. Indikator hesapla
    3. Sinyal skoru uret
    4. Risk kontrolu (portfoy limitleri)
    5. PaperBroker ile sanal emir ver
    6. Sinyali kaydet (PaperSignal)
    7. Telegram bildirim gonder (opsiyonel)
"""

import os
import sys
from pathlib import Path
_module_dir = Path(__file__).resolve().parent
while _module_dir.name != "PYTHON" and _module_dir.parent != _module_dir:
    _module_dir = _module_dir.parent
if _module_dir.name == "PYTHON":
    sys.path.insert(0, str(_module_dir.parent))

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from data.feed_aggregator import FeedAggregator
from data.market_calendar import BISTCalendar
from data.macro_fetcher import MacroFetcher
from data.news_fetcher import NewsFetcher
from backtest.indicators import apply_all
from backtest.signals import combined_signal
from paper_trading.paper_broker import PaperBroker
from risk.database import get_session
from paper_trading.models import PaperSignal
from manipulation.multi_tf_detector import MultiTFManipDetector
from manipulation.agent_trust_scorer import AgentTrustScorer
from manipulation.consensus_engine import ByzantineConsensus
from execution.manipulation_fallback import ManipulationFallbackRouter
from strategy.dynamic_symbol_rotator import DynamicSymbolRotator
from common.time_rules import TimeBasedTradingManager
from strategy.parameter_registry import ParameterRegistry, get_registry, SignalConfig


class SignalEngine:
    """
    Canli sinyal uretim motoru.
    Paper trading aktifse sanal emir verir.
    Aktif degilse sadece sinyal kaydeder (forward test modu).

    v3.3+: Manipülasyon tespiti sonrasi otomatik fallback (BIST -> Kripto -> Forex)
    v3.3+: Dinamik sembol rotasyonu (en iyi alternatife gecis)
    """

    def __init__(
        self,
        paper_trading: bool | None = None,
        signal_threshold: float = 70.0,
        max_positions: int = 5,
        max_risk_pct: float = 10.0,
        enable_manipulation_check: bool = True,
        enable_fallback: bool = True,
        enable_auto_rotate: bool = False,
        bist_universe: list[str] | None = None,
    ):
        self.paper_trading = paper_trading if paper_trading is not None else (
            os.getenv("AX_PAPER_TRADING", "false").lower() == "true"
        )
        self.signal_threshold = signal_threshold
        self.max_positions = max_positions
        self.max_risk_pct = max_risk_pct
        self.feed = FeedAggregator()
        self.broker = PaperBroker(
            max_positions=max_positions,
            max_risk_pct=max_risk_pct,
        )
        self.calendar = BISTCalendar()
        self.macro_fetcher = MacroFetcher()
        self.news_fetcher = NewsFetcher()
        self._macro_cache: dict | None = None
        self._macro_cache_time: datetime | None = None
        self._news_cache: pd.DataFrame | None = None
        self._news_cache_time: datetime | None = None
        # Sinyal Ajanı — Kimi/Bulut AI entegrasyonu
        from ai.cloud_client import SignalAgentAI
        self.ai_signal = SignalAgentAI()
        # Manipülasyon tespiti
        self.enable_manipulation_check = enable_manipulation_check
        self.manip_detector = MultiTFManipDetector()
        self.trust_scorer = AgentTrustScorer()
        self.consensus = ByzantineConsensus()
        # Fallback ve rotasyon
        self.enable_fallback = enable_fallback
        self.fallback_router = ManipulationFallbackRouter(
            enable_crypto=True,
            enable_forex=True,
        )
        self.rotator = DynamicSymbolRotator(
            bist_universe=bist_universe or [],
            fallback_router=self.fallback_router,
            enable_auto_rotate=enable_auto_rotate,
        )
        # Zaman bazli trading yonetimi (K246-K248)
        self.time_manager = TimeBasedTradingManager()
        self._time_alerts_emitted: set = set()
        # Parameter Registry — regime-adaptive parameters (K95)
        self.registry = get_registry()
        self._last_regime: str = "sideways"
        # Validators — init once to avoid hot-path instantiation (K97)
        from data.auto_validator import AutoValidator
        from execution.order_validator import OrderValidator
        self._auto_validator = AutoValidator()
        self._order_validator = OrderValidator(max_size=1_000_000.0)
        # Batch insert buffer (K97)
        self._signal_buffer: list = []

    def _check_market_open(self) -> tuple[bool, str]:
        """Piyasa acik mi kontrol et. Tatil/haftasonu bilgisi dondur."""
        if self.calendar.is_holiday():
            return False, self.calendar.get_reason()
        if not self.calendar.is_market_open():
            return False, "BIST su an kapali (09:30-18:00 acik)"
        return True, "Piyasa acik"

    def _check_time_window(self) -> tuple[bool, str]:
        """K246-K248: Zaman bazli trading penceresi kontrolu."""
        if not self.time_manager.can_trade_now():
            suggestion = self.time_manager.suggest_optimal_trading_time()
            reason = suggestion.get("reason", "Piyasa kapali")
            return False, reason
        # Uyarlari kontrol et ve bir kez yazdir
        alerts = self.time_manager.check_and_alert()
        for alert in alerts:
            key = (alert.window.value, alert.level.value, alert.message)
            if key not in self._time_alerts_emitted:
                self._time_alerts_emitted.add(key)
                print(f"ZAMAN UYARISI [{alert.level.value.upper()}]: {alert.message}")
        return True, "Trading penceresi acik"

    def _get_time_based_max_positions(self) -> int:
        """K246: Aktif zaman penceresine gore max pozisyon limiti."""
        return self.time_manager.get_max_positions()

    def _get_time_based_risk_multiplier(self) -> float:
        """K246: Aktif zaman penceresine gore risk carpani."""
        return self.time_manager.get_risk_multiplier()

    def _check_manipulation(self, symbol: str):
        """Çoklu zaman diliminde manipülasyon tespiti."""
        try:
            bars = {}
            for interval, period in [("15m", "5d"), ("1h", "15d"), ("1d", "3mo")]:
                try:
                    df = self.feed.fetch(symbol, interval=interval, period=period)
                    if df is not None and len(df) >= 30:
                        bars[interval] = df
                except Exception:
                    continue
            if not bars:
                return None
            return self.manip_detector.scan(symbol, bars=bars)
        except Exception:
            return None

    def _calculate_kelly(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Kelly Criterion: f* = (bp - q) / b"""
        if avg_loss <= 0:
            return 0.0
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        f = (b * p - q) / b
        return max(-1.0, min(1.0, f))

    def _calculate_r_r(self, entry: float, sl: float, tp: float) -> float:
        """Risk/Reward orani."""
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        if risk <= 0:
            return 0.0
        return reward / risk

    def _get_macro_regime(self) -> dict:
        """Makro verileri cache ile cek, rejim skoru dondur."""
        now = datetime.now()
        if self._macro_cache is not None and self._macro_cache_time is not None:
            if (now - self._macro_cache_time).total_seconds() < 300:
                return self._macro_cache
        try:
            self._macro_cache = self.macro_fetcher.get_regime_score()
            self._macro_cache_time = now
        except Exception:
            self._macro_cache = {"regime": "NEUTRAL", "score": 1, "factors": {}}
            self._macro_cache_time = now
        return self._macro_cache

    def _get_signal_config(self, symbol: str | None = None) -> SignalConfig:
        """Regime + symbol bazli adaptive SignalConfig dondur (K95)."""
        macro = self._get_macro_regime()
        regime = macro.get("regime", "NEUTRAL").lower()
        if regime not in ("bull", "bear", "sideways", "volatile", "low_vol"):
            regime = self._last_regime
        else:
            self._last_regime = regime
        return self.registry.get_signal_config(regime=regime, symbol=symbol)

    def _get_news_sentiment(self) -> float:
        """Haber duygu analizi: -1 (negatif) ile +1 (pozitif) arasi skor."""
        now = datetime.now()
        if self._news_cache is not None and self._news_cache_time is not None:
            if (now - self._news_cache_time).total_seconds() < 300:
                df = self._news_cache
            else:
                df = None
        else:
            df = None

        if df is None:
            try:
                df = self.news_fetcher.fetch_all()
                self._news_cache = df
                self._news_cache_time = now
            except Exception:
                return 0.0

        if df.empty:
            return 0.0

        sentiments = df.get("sentiment", pd.Series([], dtype=str))
        pos = (sentiments == "positive").sum()
        neg = (sentiments == "negative").sum()
        total = len(sentiments)
        if total == 0:
            return 0.0
        return (pos - neg) / total

    def analyze_symbol(self, symbol: str, interval: str = "1d", period: str = "3mo") -> dict | None:
        """
        Tek bir sembol icin teknik analiz + sinyal skoru.
        v3.3+: ParameterRegistry ile regime-adaptive agirliklar ve esikler (K95).
        Returns: sinyal dict veya None (yeterli veri yoksa)
        """
        try:
            df = self.feed.fetch(symbol, interval=interval, period=period)
        except Exception as e:
            print(f"SINYAL: {symbol} veri cekilemedi: {e}")
            return None

        if len(df) < 50:
            print(f"SINYAL: {symbol} yetersiz veri ({len(df)} satir)")
            return None

        # K95: Regime-adaptive config
        cfg = self._get_signal_config(symbol=symbol)

        # Indikatorler + sinyal (adaptive weights/thresholds)
        df = apply_all(df)
        df = combined_signal(df, config=cfg)

        last = df.iloc[-1]
        score = last.get("Signal_Score", 0)
        signal = last.get("Signal", 0)

        if score < cfg.score_strong or signal < 2:
            return None  # Yeterince guclu sinyal yok

        # SL / TP hesapla (regime-adaptive ATR multipliers)
        entry = last["close"]
        atr = last.get("ATR", entry * 0.03)
        sl = entry - (atr * cfg.atr_sl_mult)
        tp1 = entry + (atr * cfg.atr_tp1_mult)
        tp2 = entry + (atr * cfg.atr_tp2_mult)

        r_r = self._calculate_r_r(entry, sl, tp1)
        if r_r < 2.0:
            return None  # Kural D-3: R:R min 1:2

        # Kelly (regime-adaptive assumptions)
        kelly = self._calculate_kelly(win_rate=cfg.kelly_win_rate, avg_win=cfg.kelly_avg_win, avg_loss=cfg.kelly_avg_loss)
        if kelly <= 0:
            return None  # Kelly <= 0 ise RED

        # MiroFish composite momentum score (0-100)
        rsi = last.get("RSI", 50)
        macd_hist = last.get("MACD_Hist", 0)
        bb_position = (entry - last.get("BB_Lower", entry)) / (last.get("BB_Upper", entry) - last.get("BB_Lower", entry) + 1e-9)
        mirofish = min(100, max(0, (rsi * 0.4) + (50 + macd_hist * 10) * 0.3 + (bb_position * 50) * 0.3))

        # AutoValidator: Canli fiyat dogrulamasi (K91)
        validation = self._auto_validator.validate_symbol(
            symbol=symbol,
            expected_price=entry,
            expected_sl=sl,
            expected_tp=tp1,
        )
        if not validation["valid"]:
            print(f"SINYAL: {symbol} dogrulama RED -> {validation['reason']}")
            return None

        # Makro rejim ve haber sentiment entegrasyonu
        macro = self._get_macro_regime()
        regime = macro.get("regime", "NEUTRAL")
        news_sentiment = self._get_news_sentiment()

        # Ayi piyasasi veya cok negatif haberler: adaptive skor dusur (K95)
        if regime == "BEAR":
            score += cfg.bear_penalty
        elif regime == "NEUTRAL" and macro.get("score", 1) <= 1:
            score += cfg.bear_penalty * 0.5

        if news_sentiment < -0.5:
            score += cfg.news_severe_penalty
            print(f"SINYAL: {symbol} negatif haber sentiment ({news_sentiment:.2f}), skor dusuruldu")
        elif news_sentiment < -0.2:
            score += cfg.news_moderate_penalty

        if score < cfg.score_strong:
            print(f"SINYAL: {symbol} makro/haber nedeniyle esik altina dustu ({score:.0f} < {cfg.score_strong})")
            return None

        # Manipülasyon tespiti (çoklu zaman dilimi)
        if self.enable_manipulation_check:
            manip_result = self._check_manipulation(symbol)
            if manip_result and manip_result.is_manipulated:
                score -= manip_result.threat_score * 0.5
                print(f"SINYAL: {symbol} manipülasyon tespit edildi ({manip_result.reason}), skor dusuruldu ({score:.0f})")
                if score < cfg.score_strong:
                    # K243: Fallback — alternatif piyasalara veya hisselere gecis
                    if self.enable_fallback:
                        fb = self.fallback_router.fallback(symbol)
                        if fb.fallback_symbol:
                            print(f"SINYAL: {symbol} -> FALLBACK {fb.fallback_symbol} ({fb.fallback_market})")
                            # Yeni sembolu analiz et
                            return self.analyze_symbol(fb.fallback_symbol, interval, period)
                    return None

        signal_dict = {
            "symbol": symbol,
            "score": score,
            "entry": entry,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "r_r": r_r,
            "kelly": kelly,
            "mirofish": mirofish,
            "atr": atr,
            "regime": regime,
            "macro_score": macro.get("score"),
            "news_sentiment": round(news_sentiment, 3),
            "timestamp": datetime.now(),
        }
        # Gemma AI yorumu (Sinyal Ajanı)
        ai_commentary = self.ai_signal.analyze_commentary(symbol, signal_dict)
        signal_dict["ai_commentary"] = ai_commentary
        return signal_dict

    def execute_signal(self, signal: dict) -> dict:
        """
        Sinyali isle: Paper trade ac veya sadece kaydet.
        Returns: islem sonucu dict
        """
        result = {
            "symbol": signal["symbol"],
            "signal_score": signal["score"],
            "executed": False,
            "reason": "",
            "trade_id": None,
        }

        # BIST acik mi kontrolu (K141)
        is_open, reason = self._check_market_open()
        if not is_open:
            result["reason"] = reason
            return result

        # K246-K248: Zaman bazli trading penceresi kontrolu
        can_trade_time, time_reason = self._check_time_window()
        if not can_trade_time:
            result["reason"] = time_reason
            return result

        # K246: Aktif zaman penceresine gore dinamik max pozisyon
        time_max_pos = self._get_time_based_max_positions()
        open_pos = len(self.broker.get_open_positions())
        if open_pos >= time_max_pos:
            result["reason"] = f"Zaman penceresi max pozisyon limiti ({time_max_pos})"
            return result

        # K246: EOD pozisyon kapatma kontrolu
        if self.time_manager.should_close_positions():
            result["reason"] = "Kapanis oncesi — yeni pozisyon ACMA (K247)"
            return result

        # Paper trade ac
        if self.paper_trading:
            # Pozisyon buyuklugu: Kelly bazli ama max %2
            kelly_pct = min(signal["kelly"] * 100, 2.0)
            initial = self.broker.initial_capital
            size = (initial * (kelly_pct / 100)) / signal["entry"]
            size = int(size)

            if size <= 0:
                result["reason"] = "Pozisyon buyuklugu sifir"
                return result

            # K143: Emir validasyonu zorunlu
            validation = self._order_validator.validate({
                "symbol": signal["symbol"],
                "side": "BUY",
                "size": size,
                "price": signal["entry"],
                "sl": signal["sl"],
                "tp": signal["tp1"],
            })
            if not validation["valid"]:
                result["reason"] = f"OrderValidator RED: {'; '.join(validation['errors'])}"
                return result

            trade = self.broker.place_order(
                symbol=signal["symbol"],
                side="BUY",
                size=size,
                price=signal["entry"],
                sl=signal["sl"],
                tp1=signal["tp1"],
                tp2=signal["tp2"],
                strategy="SIGNAL_ENGINE",
                agent="B",
            )

            if trade:
                result["executed"] = True
                result["trade_id"] = trade.id
                result["size"] = size
                result["entry"] = signal["entry"]
                result["reason"] = "Paper trade acildi"
            else:
                result["reason"] = "Paper broker emir RED"
        else:
            result["reason"] = "Paper trading PASIF - sinyal kaydedildi"

        # Sinyali kaydet (PaperSignal) — batch buffer (K97)
        ps = PaperSignal(
            symbol=signal["symbol"],
            signal_time=signal["timestamp"],
            strategy="SIGNAL_ENGINE",
            entry_price=signal["entry"],
            sl_price=signal["sl"],
            tp1_price=signal["tp1"],
            tp2_price=signal["tp2"],
            r_r=signal["r_r"],
            kelly=signal["kelly"],
            mirofish=signal["mirofish"],
            signal_score=signal["score"],
            regime=signal["regime"],
            macro_score=signal.get("macro_score"),
            news_sentiment=signal.get("news_sentiment"),
            outcome="FILLED" if result["executed"] else "PENDING",
            notes=result["reason"],
        )
        self._signal_buffer.append(ps)
        return result

    def _flush_signal_buffer(self):
        """K97: Batch insert buffered PaperSignal records."""
        if not self._signal_buffer:
            return
        session = get_session()
        try:
            for ps in self._signal_buffer:
                session.add(ps)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"SINYAL: Batch insert hatasi: {e}")
        finally:
            session.close()
            self._signal_buffer.clear()

    def run_scan_with_fallback(self, symbols: list[str], max_workers: int = 4) -> list[dict]:
        """
        K243-K244: Manipülasyon tespiti sonrasi otomatik fallback ile tarama.
        K97: Paralel analyze.
        Returns: sinyal sonuclari listesi
        """
        is_open, reason = self._check_market_open()
        if not is_open:
            print(f"SINYAL: {reason}")
            return [{"market_closed": True, "reason": reason}]

        # K246-K248: Zaman penceresi kontrolu
        can_trade_time, time_reason = self._check_time_window()
        if not can_trade_time:
            print(f"SINYAL: {time_reason}")
            return [{"market_closed": True, "reason": time_reason}]

        # K97: Paralel symbol analysis
        analyzed: list[dict | None] = []
        if len(symbols) == 1 or max_workers <= 1:
            analyzed = [self.analyze_symbol(sym) for sym in symbols]
        else:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(symbols))) as executor:
                analyzed = list(executor.map(self.analyze_symbol, symbols))

        results = []
        fallback_count = 0
        for sym, signal in zip(symbols, analyzed):
            if signal:
                result = self.execute_signal(signal)
                results.append(result)
                print(
                    f"SINYAL: {sym} | Skor: {signal['score']:.0f} | "
                    f"R:R: {signal['r_r']:.2f} | Kelly: {signal['kelly']:.3f} | "
                    f"Durum: {result['reason']}"
                )
            else:
                bl = self.fallback_router.get_blacklist()
                if sym.upper() in bl:
                    fallback_count += 1

        if fallback_count > 0:
            print(f"SINYAL: {fallback_count} sembolde manipülasyon tespit edildi, fallback calisti")

        self._flush_signal_buffer()
        return results

    def run_dynamic_rotation_scan(self, symbols: list[str], max_workers: int = 4) -> list[dict]:
        """
        K244: Dinamik sembol rotasyonu ile tarama.
        K97: Paralel analyze.
        """
        # Once tum sembollerin skorunu guncelle
        self.rotator.update_scores(symbols)

        is_open, reason = self._check_market_open()
        if not is_open:
            return [{"market_closed": True, "reason": reason}]

        # K246-K248: Zaman penceresi kontrolu
        can_trade_time, time_reason = self._check_time_window()
        if not can_trade_time:
            return [{"market_closed": True, "reason": time_reason}]

        # Rotasyon kararlarini once al (senkron, thread-safe degil)
        rotated_symbols = []
        for sym in symbols:
            should_rotate, rotation_reason = self.rotator.should_rotate(sym)
            if should_rotate:
                target = self.rotator.get_rotation_target(sym)
                if target and target.fallback_symbol:
                    print(f"ROTASYON: {sym} -> {target.fallback_symbol} | Neden: {rotation_reason}")
                    self.rotator.record_rotation(sym, target.fallback_symbol, rotation_reason)
                    sym = target.fallback_symbol
            rotated_symbols.append(sym)

        # K97: Paralel symbol analysis
        analyzed: list[dict | None] = []
        if len(rotated_symbols) == 1 or max_workers <= 1:
            analyzed = [self.analyze_symbol(sym) for sym in rotated_symbols]
        else:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(rotated_symbols))) as executor:
                analyzed = list(executor.map(self.analyze_symbol, rotated_symbols))

        results = []
        for sym, signal in zip(rotated_symbols, analyzed):
            if signal:
                result = self.execute_signal(signal)
                results.append(result)
                print(
                    f"SINYAL: {sym} | Skor: {signal['score']:.0f} | "
                    f"R:R: {signal['r_r']:.2f} | Kelly: {signal['kelly']:.3f} | "
                    f"Durum: {result['reason']}"
                )

        self._flush_signal_buffer()
        return results

    def get_fallback_blacklist(self) -> dict:
        """Kara listedeki manipule sembolleri dondur."""
        return self.fallback_router.get_blacklist()

    def get_rotation_history(self) -> list[dict]:
        """Rotasyon tarihcesini dondur."""
        return self.rotator.get_rotation_history()

    def run_scan(self, symbols: list[str], max_workers: int = 4) -> list[dict]:
        """
        Birden fazla sembolu tara ve sinyal uret.
        Tatil/haftasonu/piyasa kapali ise bilgi ver ve cik.
        K246-K248: Zaman bazli pencere kontrolu entegre.
        K97: Paralel analyze + batch DB insert.
        Returns: sinyal sonuclari listesi
        """
        is_open, reason = self._check_market_open()
        if not is_open:
            print(f"SINYAL: {reason}")
            return [{"market_closed": True, "reason": reason}]

        # K246-K248: Zaman penceresi kontrolu
        can_trade_time, time_reason = self._check_time_window()
        if not can_trade_time:
            print(f"SINYAL: {time_reason}")
            return [{"market_closed": True, "reason": time_reason}]

        # K246: Optimal trading onerisini goster
        suggestion = self.time_manager.suggest_optimal_trading_time()
        if suggestion["can_trade_now"]:
            print(
                f"ZAMAN: Aktif pencere={suggestion['current_window']} | "
                f"Risk carpani={suggestion['risk_multiplier']} | "
                f"Max pozisyon={suggestion['max_positions']}"
            )

        # K97: Paralel symbol analysis
        analyzed: list[dict | None] = []
        if len(symbols) == 1 or max_workers <= 1:
            analyzed = [self.analyze_symbol(sym) for sym in symbols]
        else:
            with ThreadPoolExecutor(max_workers=min(max_workers, len(symbols))) as executor:
                analyzed = list(executor.map(self.analyze_symbol, symbols))

        results = []
        for sym, signal in zip(symbols, analyzed):
            if signal:
                result = self.execute_signal(signal)
                results.append(result)
                print(
                    f"SINYAL: {sym} | Skor: {signal['score']:.0f} | "
                    f"R:R: {signal['r_r']:.2f} | Kelly: {signal['kelly']:.3f} | "
                    f"Durum: {result['reason']}"
                )

        # K97: Flush any buffered signals to DB
        self._flush_signal_buffer()
        return results


if __name__ == "__main__":
    from risk.database import init_db
    init_db()
    engine = SignalEngine(paper_trading=True)
    results = engine.run_scan(["THYAO", "GARAN", "ASELS"])
    print(f"Toplam sinyal: {len([r for r in results if r['executed']])} islem acildi")
