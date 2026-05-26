"""
main.py — Python Orchestrator
Node.js ana motor ile birlikte calisan Python backtest, analitik ve risk modulu.
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime

# Modul yollarini ekle
sys.path.insert(0, os.path.dirname(__file__))

from backtest import engine as bt_engine, indicators, signals, slippage, commission
from analytics import volume_anomaly, bb_volume_combo, error_analyzer, agent_scoring
from memory import chroma_store, embedder, query
from risk import database, portfolio_monitor, metrics as risk_metrics, dashboard
from data.instrument_provider import BIST_UNIVERSE
from data.feed_aggregator import FeedAggregator


def init_db():
    """Veritabanini baslatir."""
    database.init_db()
    print("[PYTHON] Veritabani baslatildi.")


def run_backtest(csv_path: str, symbol: str = "THYAO", vectorized: bool = False, regime: str | None = None):
    """CSV dosyasi uzerinde backtest calistirir.
    v3.3+: Regime-adaptive backtest destegi (K95).
    """
    from strategy.parameter_registry import get_registry

    reg = get_registry()
    cfg = reg.get_signal_config(regime=regime or "sideways", symbol=symbol)
    risk_cfg = reg.get_risk_config(regime=regime or "sideways")

    df = pd.read_csv(csv_path, parse_dates=["timestamp"], index_col="timestamp")
    df = indicators.apply_all(df)
    df = signals.combined_signal(df, config=cfg)

    if vectorized:
        from optimization.vectorized_backtest import VectorizedBacktestEngine
        eng = VectorizedBacktestEngine(
            df,
            slippage_model=slippage.SlippageModel(),
            commission_model=commission.CommissionModel(),
            initial_capital=100_000,
            position_size_pct=risk_cfg.position_size_pct,
        )
    else:
        eng = bt_engine.BacktestEngine(
            df,
            slippage_model=slippage.SlippageModel(),
            commission_model=commission.CommissionModel(),
            initial_capital=100_000,
            position_size_pct=risk_cfg.position_size_pct,
            signal_config=cfg,
        )
    result = eng.run()

    print(f"\n[BACKTEST] {symbol} | Regime: {regime or 'sideways'} | Config: adaptive (K95)")
    print(f"  Baslangic Sermayesi: 100,000 TL")
    print(f"  Bitis Sermayesi: {result['final_capital']:.2f} TL")
    print(f"  Toplam Getiri: %{result['total_return']*100:.2f}")
    print(f"  Islem Sayisi: {len(result['trades'])}")
    print(f"  Pozisyon Buyuklugu: %{risk_cfg.position_size_pct*100:.2f}")

    # Metrikler
    m = risk_metrics.calculate_portfolio_metrics(result["trades"], result["equity"]["equity"])
    print("\n" + dashboard.cli_table(m))

    return result


def run_analytics(csv_path: str):
    """Analitik modullerini calistirir."""
    df = pd.read_csv(csv_path, parse_dates=["timestamp"], index_col="timestamp")

    # Hacim anomalisi
    df = volume_anomaly.detect_volume_anomaly(df)
    anomalies = volume_anomaly.summarize_anomalies(df)
    if not anomalies.empty:
        print(f"\n[HACIM] {len(anomalies)} anomali tespit edildi.")
        print(anomalies.head())

    # BB + Hacim kombinasyonu
    df = bb_volume_combo.detect_bb_volume_combo(df)
    combo = bb_volume_combo.summarize_signals(df)
    if not combo.empty:
        print(f"\n[BB+HACIM] {len(combo)} kombinasyon sinyali tespit edildi.")
        print(combo.head())


def run_monitor():
    """Portfoy monitörünü baslatir."""
    monitor = portfolio_monitor.PortfolioMonitor()
    summary = monitor.get_portfolio_summary()
    print("\n[PORTFOY] Ozet:")
    for k, v in summary.items():
        print(f"  {k}: {v}")


def run_chroma_demo():
    """ChromaDB demo sorgusu calistirir."""
    print("\n[CHROMADB] Demo analiz kaydi...")
    client = chroma_store.get_client()
    collection = chroma_store.get_or_create_collection(client)

    text = embedder.build_analysis_text(
        symbol="THYAO", date="2026-05-18", price=103.0,
        ema9=102.5, ema21=100.0, rsi=62.0, macd_hist=0.5,
        bb_width=0.04, volume_z=2.8, regime="BULL", decision="AL"
    )
    emb = embedder.embed(text)
    chroma_store.add_analysis(collection, "demo_1", "THYAO", text, emb)

    results = query.find_similar_decisions(
        symbol="THYAO", date="2026-05-18", price=103.0,
        ema9=102.5, ema21=100.0, rsi=62.0, macd_hist=0.5,
        bb_width=0.04, volume_z=2.8, regime="BULL", decision="AL"
    )
    print(f"[CHROMADB] {len(results)} benzer analiz bulundu.")


def run_error_demo():
    """Hata analizi demo."""
    analyzer = error_analyzer.ErrorAnalyzer()
    analyzer.log_error(
        symbol="THYAO", agent="B", expected="YUKSEL", actual="DUS",
        market_regime="BEAR", pnl_impact=-1500, root_cause_category="makro",
        description="Makro veri beklentisi yanlis. USD/TRY ani sicrama.",
        missed_signals=["USD/TRY > 38", "VIX > 30"],
    )
    print("\n[HATA] Demo hata kaydi olusturuldu.")
    print(analyzer.analyze_patterns())


def run_scan(symbols: list[str]):
    """Canli sinyal taramasi calistir."""
    from paper_trading.signal_engine import SignalEngine
    engine = SignalEngine(paper_trading=False)  # Sadece sinyal kaydet, emir verme
    results = engine.run_scan(symbols)
    executed = [r for r in results if r.get("executed")]
    print(f"\n[TARAMA] {len(symbols)} sembol tarandi. {len(executed)} sinyal bulundu.")
    return results


def run_parallel_scan(symbols: list[str], workers: int = 8):
    """Paralel sinyal taramasi calistir."""
    from optimization.parallel_scanner import ParallelScanner
    scanner = ParallelScanner(max_workers=workers)
    results, stats = scanner.run_scan_with_progress(symbols)
    print(f"\n[TARAMA PARALEL] {stats['scanned']}/{stats['total']} sembol | {stats['signals']} sinyal | {stats['errors']} hata")
    for r in results:
        print(f"  {r['symbol']} | Skor: {r['score']:.0f} | R:R: {r['r_r']:.2f}")
    return results


def run_hft_backtest(csv_path: str, strategy: str = "m1_momentum", interval: int = 60):
    """HFT tick-level backtest calistir."""
    import pandas as pd
    from hft.backtest.hft_backtest import HFTBacktestEngine
    from hft.config import HFTConfig

    tick_df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    if "price" not in tick_df.columns:
        print("[HFT] CSV 'price' kolonu icermeli.")
        return None

    engine = HFTBacktestEngine(
        tick_df=tick_df,
        strategy=strategy,
        interval_seconds=interval,
        initial_capital=100_000.0,
    )
    result = engine.run()

    print(f"\n[HFT BACKTEST] {strategy} | {len(tick_df)} tick")
    print(f"  Baslangic: 100,000 TL")
    print(f"  Bitis: {result['final_capital']:.2f} TL")
    print(f"  Getiri: %{result['total_return']*100:.2f}")
    print(f"  Islem: {len(result['trades'])}")
    print(f"  Latency: {result['latency_stats']}")
    print(f"  Orders: {result['order_stats']}")
    return result


def run_manipulation_scan(symbols: list[str]):
    """Çoklu zaman diliminde manipülasyon taramasi."""
    from manipulation.multi_tf_detector import MultiTFManipDetector
    from data.feed_aggregator import FeedAggregator
    detector = MultiTFManipDetector()
    feed = FeedAggregator()
    results = []
    for sym in symbols:
        bars = {}
        for interval, period in [("15m", "5d"), ("1h", "15d"), ("1d", "3mo")]:
            try:
                df = feed.fetch(sym, interval=interval, period=period)
                if df is not None and len(df) >= 30:
                    bars[interval] = df
            except Exception:
                continue
        if not bars:
            print(f"[MANIP] {sym} yeterli veri yok.")
            continue
        res = detector.scan(sym, bars=bars)
        status = "MANIP" if res.is_manipulated else "TEMIZ"
        print(f"[MANIP] {sym} | {status} | Skor: {res.threat_score:.0f} | {res.reason}")
        results.append(res)
    return results


def run_agent_trust():
    """Agent trust skorlarini goster."""
    from manipulation.agent_trust_scorer import AgentTrustScorer
    scorer = AgentTrustScorer()
    scores = scorer.get_all_scores()
    print("\n[TRUST] Agent Trust Skorlari:")
    for aid, data in scores.items():
        print(f"  {aid}: {data['trust_score']:.1f} (success={data['win_rate']:.2f}, threats={data['threat_count']})")
    top = scorer.get_top_agents(n=5)
    if top:
        print("\n  Top 5:")
        for t in top:
            print(f"    {t['agent_id']}: {t['trust_score']:.1f}")
    return scores


def run_hft_live(symbols: list[str], strategy: str = "m1_momentum"):
    """HFT canli sinyal uretimi (simulated feed ile demo)."""
    import pandas as pd
    from hft.config import HFTConfig
    from hft.tick_aggregator import TickAggregator
    from hft.signal_generator import generate_signal_from_df
    from hft.risk_filter import RiskFilter
    from hft.position_manager import HFTPositionManager
    from hft.order_manager import HFTOrderManager
    from hft.latency_tracker import LatencyTracker
    from hft.broker_feed import SimulatedBrokerFeed
    from risk.account import Account

    config = HFTConfig(timeframe="1m", symbols=symbols)
    account = Account(initial_cash=100_000.0, max_position_value_pct=1.0)
    pos_mgr = HFTPositionManager(account)
    order_mgr = HFTOrderManager()
    risk = RiskFilter()
    latency = LatencyTracker()
    aggregator = TickAggregator(interval_seconds=60)

    # Simulated feed: fetch last bars from FeedAggregator
    feed = FeedAggregator()
    bars_dict = {}
    for sym in symbols:
        try:
            df = feed.fetch(sym, interval="1m", period="1d")
            if df is not None and len(df) >= 30:
                bars_dict[sym] = df
        except Exception as e:
            print(f"[HFT] {sym} veri hatasi: {e}")

    if not bars_dict:
        print("[HFT] Yeterli veri yok.")
        return []

    signals_found = []
    for sym, df in bars_dict.items():
        sig = generate_signal_from_df(df, strategy=strategy)
        if sig and sig.get("signal", 0) != 0:
            signals_found.append({"symbol": sym, "signal": sig})
            print(f"[HFT] {sym} | signal={sig['signal']} | entry={sig.get('entry', 0):.2f}")

    print(f"\n[HFT LIVE] {len(symbols)} sembol | {len(signals_found)} sinyal")
    return signals_found


def run_gold_mining(symbols: list[str], tier: str | None = None, capital: float = 100_000.0):
    """Gold Mining kademeli stratejisini calistir."""
    from strategy.gold_mining.orchestrator import GoldMiningOrchestrator, GoldMiningState
    from data.feed_aggregator import FeedAggregator

    state = GoldMiningState(current_tier_name=tier or "MS")
    engine = GoldMiningOrchestrator(initial_capital=capital, state=state)
    feed = FeedAggregator()

    def provider(sym, interval):
        try:
            return feed.fetch(sym, interval=interval, period="1d")
        except Exception:
            return None

    print(f"\n[GOLD MINING] Baslangic: {capital:,.0f} TL | Tier: {engine.state.current_tier_name}")
    results = engine.run_scan(symbols, provider)

    executed = [r for r in results if r.get("executed")]
    print(f"[GOLD MINING] {len(symbols)} sembol | {len(executed)} islem acildi")
    for r in executed:
        sig = r.get("signal", {})
        print(f"  {r['symbol']} | {sig.get('side','')} @ {sig.get('entry',0):.2f} | Tier: {r['tier']} | Agents: {r['agents_active']}")

    print(f"[GOLD MINING] Durum: {engine.state.to_dict()}")
    return results


def main():
    parser = argparse.ArgumentParser(description="AnatoliaX Python Modulu")
    parser.add_argument("--parallel-scan", type=str, metavar="SYMBOLS", help="Paralel sinyal taramasi (virgulle ayrilmis semboller)")
    parser.add_argument("--workers", type=int, default=8, help="Paralel worker sayisi (varsayilan: 8)")
    parser.add_argument("--vectorized-backtest", action="store_true", help="Hizli vektorize backtest motorunu kullan")

    parser.add_argument("--init-db", action="store_true", help="Veritabanini baslat")
    parser.add_argument("--backtest", type=str, metavar="CSV", help="Backtest calistir")
    parser.add_argument("--symbol", type=str, default="THYAO", help="Hisse sembolu")
    parser.add_argument("--regime", type=str, default=None, choices=["bull", "bear", "sideways", "volatile", "low_vol"], help="Backtest regime (K95 adaptive)")
    parser.add_argument("--analytics", type=str, metavar="CSV", help="Analitik calistir")
    parser.add_argument("--monitor", action="store_true", help="Portfoy monitörü")
    parser.add_argument("--chroma-demo", action="store_true", help="ChromaDB demo")
    parser.add_argument("--error-demo", action="store_true", help="Hata analizi demo")
    parser.add_argument("--all-demos", action="store_true", help="Tum demolar")
    parser.add_argument("--scan-all", action="store_true", help="BIST universe tum sembolleri tara")
    parser.add_argument("--scan", type=str, metavar="SYMBOLS", help="Virgulle ayrilmis sembol listesi (ornek: THYAO,GARAN,ASELS)")
    parser.add_argument("--hft-backtest", type=str, metavar="CSV", help="HFT tick-level backtest calistir")
    parser.add_argument("--hft-strategy", type=str, default="m1_momentum", choices=["m1_momentum", "s1_micro_scalp"], help="HFT stratejisi")
    parser.add_argument("--hft-interval", type=int, default=60, help="HFT bar araligi (saniye)")
    parser.add_argument("--hft-live", type=str, metavar="SYMBOLS", help="HFT canli sinyal (virgulle ayrilmis semboller)")
    parser.add_argument("--add-user", type=str, metavar="NAME", help="Yeni kullanici ekle (sifre sorulur)")
    parser.add_argument("--list-users", action="store_true", help="Kullanici listesini goster")

    parser.add_argument("--manipulation-scan", type=str, metavar="SYMBOLS", help="Manipülasyon taramasi (virgulle ayrilmis semboller)")
    parser.add_argument("--agent-trust", action="store_true", help="Agent trust skorlarini goster")

    # K243-K244: Manipülasyon fallback ve dinamik rotasyon
    parser.add_argument("--fallback-scan", type=str, metavar="SYMBOLS", help="Manipülasyon tespiti sonrasi otomatik fallback ile tarama")
    parser.add_argument("--auto-rotate-scan", type=str, metavar="SYMBOLS", help="Dinamik sembol rotasyonu ile tarama")
    parser.add_argument("--enable-crypto-fallback", action="store_true", help="Manipülasyon sonrasi kripto piyasasina gecis aktif")
    parser.add_argument("--enable-forex-fallback", action="store_true", help="Manipülasyon sonrasi forex piyasasina gecis aktif")

    parser.add_argument("--gold-mining", action="store_true", help="Gold Mining kademeli stratejisini calistir")
    parser.add_argument("--gold-tier", type=str, default=None, choices=["MS", "S1", "M1", "M5", "M15", "H1", "D1"], help="Gold Mining baslangic tier'i (varsayilan: MS)")
    parser.add_argument("--gold-capital", type=float, default=100_000.0, help="Gold Mining baslangic sermayesi")
    parser.add_argument("--gold-scan", type=str, metavar="SYMBOLS", help="Gold Mining sembol listesi (virgulle ayrilmis)")

    # K246-K248: Zaman bazli trading kontrolu
    parser.add_argument("--time-check", action="store_true", help="Aktif zaman penceresi ve trading durumunu goster")
    parser.add_argument("--time-summary", action="store_true", help="Zaman bazli trading ozetini goster")

    # v3.3 Integration orchestrator (Nautilus + Hummingbot + OpenClaw + Hermes)
    parser.add_argument("--integration-health", action="store_true", help="Entegrasyon saglik kontrolu (Nautilus/Hummingbot/OpenClaw/Hermes)")
    parser.add_argument("--adapter-status", action="store_true", help="Tum adapter durumlarini goster")
    parser.add_argument("--replay-validate", type=str, metavar="CSV", help="Deterministic replay validasyonu (tick CSV)")
    parser.add_argument("--replay-tolerance", type=float, default=1e-9, help="Replay validasyon toleransi")
    parser.add_argument("--integration-execute", type=str, metavar="JSON", help="Sinyal JSON'i ile entegrasyonlu emir calistir")

    # Omega Protocol (Master Strategy)
    parser.add_argument("--omega-protocol", type=str, metavar="CSV", help="Omega Protocol master stratejisi calistir (CSV dosyasi)")
    parser.add_argument("--omega-campaign", type=str, metavar="SYMBOLS", help="Omega 20-gunluk kampanya (virgulle ayrilmis semboller)")
    parser.add_argument("--omega-capital", type=float, default=1_000.0, help="Omega baslangic sermayesi (varsayilan: 1000)")

    # Tiered Growth Protocol (Daily return targets)
    parser.add_argument("--tiered-protocol", type=str, metavar="CSV", help="Tiered Growth Protocol calistir (CSV dosyasi)")
    parser.add_argument("--tiered-tier", type=str, default="PCT_5",
                        choices=["PCT_1", "PCT_3", "PCT_5", "PCT_8", "PCT_10", "PCT_13", "PCT_15", "PCT_18", "PCT_20", "PCT_100"],
                        help="Gunluk getiri hedefi (varsayilan: PCT_5)")
    parser.add_argument("--tiered-capital", type=float, default=10_000.0, help="Tiered baslangic sermayesi (varsayilan: 10000)")
    parser.add_argument("--tiered-scan", type=str, metavar="SYMBOLS", help="Tiered ile coklu sembol tarama")
    parser.add_argument("--tiered-table", action="store_true", help="Tum tierlerin karsilastirma tablosunu goster")

    # v3.5 Enhancement CLI arguments
    parser.add_argument("--microstructure", type=str, metavar="SYMBOL", help="Mikro yapi analizi (Phase 1)")
    parser.add_argument("--order-book", type=str, metavar="SYMBOL", help="L2/L3 Order book reconstruction (Phase 1)")
    parser.add_argument("--cognitive-memory", action="store_true", help="Bilissel bellek demo (Phase 5)")
    parser.add_argument("--event-sourcing", action="store_true", help="Event sourcing demo (Phase 2)")
    parser.add_argument("--portfolio-intelligence", action="store_true", help="Portfoy istihbarati (Phase 3)")
    parser.add_argument("--formal-verify", action="store_true", help="Formal verification kontrolu (Phase 2)")
    parser.add_argument("--tick-simulator", action="store_true", help="Tick-level market simulator demo (Phase 1)")
    parser.add_argument("--shadow-exec", action="store_true", help="Shadow execution environment demo (Phase 1)")
    parser.add_argument("--liquidity-collapse", action="store_true", help="Liquidity collapse detection demo (Phase 1)")
    parser.add_argument("--toxic-flow", action="store_true", help="Toxic flow detection demo (Phase 1)")
    parser.add_argument("--factor-exposure", action="store_true", help="Factor exposure engine demo (Phase 3)")
    parser.add_argument("--dynamic-hedge", action="store_true", help="Dynamic hedging engine demo (Phase 3)")
    parser.add_argument("--regime-predict", action="store_true", help="Regime transition prediction demo (Phase 4)")
    parser.add_argument("--alpha-decay", action="store_true", help="Alpha decay detection demo (Phase 4)")
    parser.add_argument("--strategy-genome", action="store_true", help="Strategy genome system demo (Phase 4)")
    parser.add_argument("--research-agent", action="store_true", help="Autonomous research agent demo (Phase 4)")
    parser.add_argument("--adversarial-sim", action="store_true", help="Adversarial market simulation demo (Phase 4)")
    parser.add_argument("--macro-ontology", action="store_true", help="Macro ontology engine demo (Phase 4)")
    parser.add_argument("--fpga-shim", action="store_true", help="FPGA shim latency assessment (Phase 5)")
    parser.add_argument("--options-surface", action="store_true", help="Options volatility surface demo (Phase 5)")
    parser.add_argument("--arbitrage-brain", action="store_true", help="Cross-exchange arbitrage brain demo (Phase 5)")
    parser.add_argument("--rl-execution", action="store_true", help="RL execution policy demo (Phase 5)")
    parser.add_argument("--gpu-pipeline", action="store_true", help="GPU pipeline benchmark (Phase 5)")
    parser.add_argument("--colocation", action="store_true", help="Co-location intelligence demo (Phase 5)")
    parser.add_argument("--mlops-governance", action="store_true", help="MLOps governance demo (Phase 5)")
    parser.add_argument("--compliance-engine", action="store_true", help="Compliance regulatory engine demo (Phase 5)")
    parser.add_argument("--cluster-orchestration", action="store_true", help="Cluster orchestration demo (Phase 5)")

    args = parser.parse_args()

    if args.add_user:
        from auth.rbac import RBACManager
        from auth.demo_user import add_user_cli
        import getpass
        rbac = RBACManager()
        role = input("Rol (trader/viewer/admin): ").strip() or "trader"
        pw = getpass.getpass("Sifre: ")
        ok = add_user_cli(rbac, args.add_user, role, pw)
        print("[AUTH] Kullanici eklendi." if ok else "[AUTH] Kullanici zaten var.")

    if args.list_users:
        from auth.rbac import RBACManager
        rbac = RBACManager()
        print("Kullanicilar:", rbac.list_users())

    if args.init_db:
        init_db()

    if args.parallel_scan:
        symbols = [s.strip().upper() for s in args.parallel_scan.split(",")]
        run_parallel_scan(symbols, workers=args.workers)

    if args.backtest:
        run_backtest(args.backtest, args.symbol, vectorized=args.vectorized_backtest, regime=args.regime)

    if args.analytics:
        run_analytics(args.analytics)

    if args.monitor:
        run_monitor()

    if args.chroma_demo:
        run_chroma_demo()

    if args.error_demo:
        run_error_demo()

    if args.all_demos:
        init_db()
        run_monitor()
        run_chroma_demo()
        run_error_demo()
        print("\n[PYTHON] Tum demolar tamamlandi.")

    if args.scan_all:
        run_scan(BIST_UNIVERSE)

    if args.scan:
        symbols = [s.strip().upper() for s in args.scan.split(",")]
        run_scan(symbols)

    if args.hft_backtest:
        run_hft_backtest(args.hft_backtest, strategy=args.hft_strategy, interval=args.hft_interval)

    if args.hft_live:
        symbols = [s.strip().upper() for s in args.hft_live.split(",")]
        run_hft_live(symbols, strategy=args.hft_strategy)

    if args.manipulation_scan:
        symbols = [s.strip().upper() for s in args.manipulation_scan.split(",")]
        run_manipulation_scan(symbols)

    # K243-K244: Fallback ve dinamik rotasyon
    if args.fallback_scan:
        symbols = [s.strip().upper() for s in args.fallback_scan.split(",")]
        from paper_trading.signal_engine import SignalEngine
        engine = SignalEngine(
            enable_fallback=True,
            enable_crypto=args.enable_crypto_fallback,
            enable_forex=args.enable_forex_fallback,
        )
        results = engine.run_scan_with_fallback(symbols)
        executed = [r for r in results if r.get("executed")]
        print(f"\n[FALLBACK TARAMA] {len(symbols)} sembol | {len(executed)} islem | Blacklist: {list(engine.get_fallback_blacklist().keys())}")

    if args.auto_rotate_scan:
        symbols = [s.strip().upper() for s in args.auto_rotate_scan.split(",")]
        from paper_trading.signal_engine import SignalEngine
        from data.instrument_provider import BIST_UNIVERSE
        engine = SignalEngine(
            enable_fallback=True,
            enable_auto_rotate=True,
            bist_universe=BIST_UNIVERSE,
        )
        results = engine.run_dynamic_rotation_scan(symbols)
        executed = [r for r in results if r.get("executed")]
        hist = engine.get_rotation_history()
        print(f"\n[ROTASYON TARAMA] {len(symbols)} sembol | {len(executed)} islem | {len(hist)} rotasyon")
        for h in hist:
            print(f"  {h['from']} -> {h['to']} | {h['reason']}")

    if args.agent_trust:
        run_agent_trust()

    # K246-K248: Zaman bazli trading kontrolu
    if args.time_check:
        from common.time_rules import TimeBasedTradingManager
        tm = TimeBasedTradingManager()
        suggestion = tm.suggest_optimal_trading_time()
        print("\n[ZAMAN KONTROLU]")
        print(f"  Aktif Pencere: {suggestion['current_window']}")
        print(f"  Trading: {'ACIK' if suggestion['can_trade_now'] else 'KAPALI'}")
        print(f"  Risk Carpani: {suggestion.get('risk_multiplier', 0.0)}")
        print(f"  Max Pozisyon: {suggestion.get('max_positions', 0)}")
        print(f"  Neden: {suggestion['reason']}")
        if suggestion.get('next_window'):
            print(f"  Sonraki Pencere: {suggestion['next_window']} ({suggestion['minutes_until']} dk)")
        alerts = tm.check_and_alert()
        if alerts:
            print(f"  Uyarilar: {len(alerts)}")
            for a in alerts:
                print(f"    [{a.level.value.upper()}] {a.message}")

    if args.time_summary:
        from common.time_rules import TimeBasedTradingManager
        tm = TimeBasedTradingManager()
        summary = tm.get_summary()
        print("\n[ZAMAN OZETI]")
        for k, v in summary.items():
            if k == "optimal_trading_suggestion":
                print(f"  {k}:")
                for sk, sv in v.items():
                    print(f"    {sk}: {sv}")
            else:
                print(f"  {k}: {v}")

    if args.gold_mining or args.gold_scan:
        symbols = [s.strip().upper() for s in args.gold_scan.split(",")] if args.gold_scan else BIST_UNIVERSE
        run_gold_mining(symbols, tier=args.gold_tier, capital=args.gold_capital)

    # v3.3 Integration orchestrator
    if args.integration_health or args.adapter_status:
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        health = orch.initialize()
        print("\n[INTEGRATION] Saglik Durumu:")
        for subsystem, data in health.items():
            if subsystem == "ok":
                continue
            print(f"  {subsystem.upper()}: {data}")

    if args.replay_validate:
        import json
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        tick_df = pd.read_csv(args.replay_validate, parse_dates=["timestamp"])
        ticks = tick_df.to_dict("records")
        result = orch.replay_validate(ticks, expected_state={"cash": 100_000.0}, tolerance=args.replay_tolerance)
        print("\n[REPLAY] Validasyon Sonucu:")
        print(f"  Valid: {result['valid']}")
        print(f"  Checksum: {result['checksum']}")
        print(f"  Ticks: {result['ticks_processed']}")
        if result.get("mismatches"):
            print(f"  Mismatches: {result['mismatches']}")

    if args.integration_execute:
        import json
        from adapters.integration_orchestrator import IntegrationOrchestrator
        orch = IntegrationOrchestrator()
        orch.initialize()
        signal = json.loads(args.integration_execute)
        res = orch.execute_signal(signal)
        print("\n[INTEGRATION] Emir Sonucu:")
        print(f"  OK: {res.ok}")
        print(f"  Order ID: {res.order_id}")
        print(f"  Provider: {res.provider}")
        print(f"  Error: {res.error}")

    if args.omega_protocol:
        import pandas as pd
        from adapters.integration_orchestrator import IntegrationOrchestrator
        from strategy.protocol_strategies.omega_protocol import OmegaProtocol
        df = pd.read_csv(args.omega_protocol, parse_dates=["timestamp"], index_col="timestamp")
        orch = IntegrationOrchestrator()
        orch.initialize()
        proto = OmegaProtocol(initial_capital=args.omega_capital)
        signal = proto.evaluate(df, symbol=args.symbol)
        print("\n[OMEGA PROTOCOL] Degerlendirme:")
        if signal:
            print(f"  Sinyal: {signal.side} {signal.symbol}")
            print(f"  Entry: {signal.entry_price:.2f} | SL: {signal.stop_loss:.2f} | TP: {signal.take_profit:.2f}")
            print(f"  Size: {signal.size:.2f} | Kelly: {signal.kelly_fraction:.2%} | R:R: {signal.rr:.2f}")
            print(f"  Confidence: {signal.confidence:.0f}% | Regime: {signal.regime}")
            print(f"  Capital: {proto.current_capital:,.2f} | Target: {proto.params['target_capital']:,.0f}")
            # Auto-execute through orchestrator
            exec_res = orch.run_omega_protocol(
                df=df.to_dict(), symbol=args.symbol,
                p_win=0.55, avg_win=2.0, avg_loss=1.0,
            )
            print(f"  Execution OK: {exec_res['ok']} | Provider: {exec_res['execution']['provider']}")
        else:
            print("  Sinyel yok (BLOK)")
            print(f"  Capital: {proto.current_capital:,.2f} | Drawdown: {proto._drawdown:.2f}%")

    if args.omega_campaign:
        symbols = [s.strip().upper() for s in args.omega_campaign.split(",")]
        from adapters.integration_orchestrator import IntegrationOrchestrator
        from data.feed_aggregator import FeedAggregator
        feed = FeedAggregator()
        orch = IntegrationOrchestrator()
        orch.initialize()
        report = orch.run_omega_campaign(
            symbols=symbols,
            bars_provider=lambda sym: feed.fetch(sym, interval="15m", period="5d"),
            higher_tf_provider=lambda sym: feed.fetch(sym, interval="1h", period="15d"),
        )
        print("\n[OMEGA CAMPAIGN] Sonuc:")
        print(f"  Baslangic: {report['initial_capital']:,.0f} TL")
        print(f"  Bitis: {report['final_capital']:,.2f} TL")
        print(f"  Hedef: {report['target_capital']:,.0f} TL")
        print(f"  Gun: {report['days_elapsed']} / {report['total_trades']} islem")
        print(f"  Return: {report['return_multiple']:.1f}x | Max DD: {report['max_drawdown_pct']:.1f}%")
        for d in report.get("daily_log", [])[-5:]:
            print(f"    Day {d['day']}: {d['capital']:,.0f} TL | PnL: {d['day_pnl']:,.0f} | Trades: {d['trades']}")

    if args.tiered_table:
        from strategy.protocol_strategies.tiered_growth_protocol import TieredGrowthProtocol
        proto = TieredGrowthProtocol(initial_capital=args.tiered_capital)
        df = proto.get_tier_comparison_table(capital=args.tiered_capital)
        print("\n[TIERED] Gunluk Getiri Hedefi — Aylik Karsilastirma Tablosu")
        print(df.to_string(index=False))

    if args.tiered_protocol:
        import pandas as pd
        from adapters.integration_orchestrator import IntegrationOrchestrator
        df = pd.read_csv(args.tiered_protocol, parse_dates=["timestamp"], index_col="timestamp")
        orch = IntegrationOrchestrator()
        orch.initialize()
        res = orch.run_tiered_protocol(
            df=df.to_dict(), symbol=args.symbol, tier=args.tiered_tier,
        )
        print(f"\n[TIERED PROTOCOL] Tier: {args.tiered_tier}")
        print(f"  OK: {res['ok']} | Symbol: {res.get('symbol', args.symbol)}")
        proj = res.get("projection", {})
        if proj:
            print(f"  Aylik Hedef: %{proj.get('total_return_pct', 0):.1f}")
            print(f"  Beklenen Sermaye: {proj.get('final_capital', 0):,.0f} TL")
            print(f"  Kazanma Orani Gerekli: {proj.get('win_rate_needed', 0):.0%}")
            print(f"  Max DD: {proj.get('max_expected_dd_pct', 0):.1f}%")
            print(f"  Risk of Ruin: {proj.get('risk_of_ruin', 0):.4f}")

    if args.tiered_scan:
        symbols = [s.strip().upper() for s in args.tiered_scan.split(",")]
        from adapters.integration_orchestrator import IntegrationOrchestrator
        from data.feed_aggregator import FeedAggregator
        feed = FeedAggregator()
        orch = IntegrationOrchestrator()
        orch.initialize()
        results = orch.run_tiered_scan(
            symbols=symbols, tier=args.tiered_tier,
            bars_provider=lambda sym: feed.fetch(sym, interval="15m", period="5d"),
        )
        print(f"\n[TIERED SCAN] {len(symbols)} sembol | {len(results)} sinyal | Tier: {args.tiered_tier}")
        for r in results[:5]:
            sig = r.get("signal", {})
            print(f"  {r['symbol']} | {sig.get('side', '')} @ {sig.get('entry_price', 0):.2f} | Conf: {sig.get('confidence', 0):.0f}%")

    # v3.5 Enhancement: Microstructure analysis
    if args.microstructure:
        from execution.microstructure import ExecutionMicrostructureEngine, MicrostructureState
        eng = ExecutionMicrostructureEngine()
        state = MicrostructureState(
            symbol=args.microstructure,
            bid_vol=1_000_000,
            ask_vol=800_000,
            book_depth=500_000,
            arrival_rate=50.0,
            midprice=105.0,
            spread=0.5,
            vpin=0.65,
        )
        analysis = eng.analyze_state(state)
        print(f"\n[MICROSTRUCTURE] {args.microstructure}")
        for k, v in analysis.items():
            print(f"  {k}: {v}")

    # v3.5 Enhancement: Order book reconstruction
    if args.order_book:
        from execution.order_book import OrderBookReconstructor, OrderBookEvent
        ob = OrderBookReconstructor(symbol=args.order_book)
        # Demo events
        now = datetime.now(timezone.utc)
        for i in range(5):
            ob.apply_event(OrderBookEvent(
                timestamp=now + timedelta(seconds=i),
                symbol=args.order_book,
                side="bid",
                price=100.0 + i * 0.1,
                size=1000.0 + i * 100,
                event_type="add",
                order_id=f"demo_{i}",
            ))
        print(f"\n[ORDER BOOK] {args.order_book}")
        print(f"  Best Bid: {ob.get_best_bid().price if ob.get_best_bid() else 'N/A'}")
        print(f"  Best Ask: {ob.get_best_ask().price if ob.get_best_ask() else 'N/A'}")
        print(f"  Spread: {ob.get_spread():.4f}")
        print(f"  Depth: {ob.get_book_depth():.0f}")

    # v3.5 Enhancement: Cognitive memory demo
    if args.cognitive_memory:
        from agents.cognitive_memory import CognitiveMemoryLayer, EpisodicMemory
        mem = CognitiveMemoryLayer()
        mem.add_episode(EpisodicMemory(
            context="BULL regime, EMA crossover",
            action="BUY THYAO @ 103.0",
            outcome="+2.5%",
            emotion="euphoria",
            symbol="THYAO",
            pnl=2500.0,
        ))
        episodes = mem.retrieve_episodes("BULL")
        print(f"\n[COGNITIVE MEMORY] Episodes: {len(episodes)}")
        for ep in episodes:
            print(f"  {ep.symbol} | {ep.action} -> {ep.outcome} | {ep.emotion}")

    # v3.5 Enhancement: Event sourcing demo
    if args.event_sourcing:
        from common.event_sourcing import EventBus, EventStore, Event, EventType
        store = EventStore()
        bus = EventBus(event_store=store)
        bus.publish(Event(
            event_type=EventType.SIGNAL,
            payload={"symbol": "THYAO", "side": "buy", "score": 85},
            correlation_id="demo-corr-1",
        ))
        events = store.get_events(event_type=EventType.SIGNAL)
        print(f"\n[EVENT SOURCING] Events: {len(events)}")
        for e in events:
            print(f"  {e.event_type.value} | {e.payload}")

    # v3.5 Enhancement: Portfolio intelligence
    if args.portfolio_intelligence:
        from risk.unified_risk_engine import PortfolioIntelligenceMixin
        intel = PortfolioIntelligenceMixin(symbols=["THYAO", "GARAN", "ASELS"])
        intel.update_metric("THYAO", sharpe=1.2, calmar=0.8, pnl=5000, sigma=0.15)
        intel.update_metric("GARAN", sharpe=0.9, calmar=0.6, pnl=3000, sigma=0.12)
        intel.update_metric("ASELS", sharpe=1.5, calmar=1.1, pnl=8000, sigma=0.20)
        weights = intel.allocate_weights()
        print(f"\n[PORTFOLIO INTELLIGENCE] Weights:")
        for sym, w in weights.items():
            print(f"  {sym}: {w:.2%}")

    # v3.5 Enhancement: Formal verification
    if args.formal_verify:
        from risk.unified_risk_engine import FormalVerificationMixin
        verifier = FormalVerificationMixin()
        result = verifier.verify_all(
            drawdown=0.04,
            position_size=8,
            daily_loss=0.02,
        )
        print(f"\n[FORMAL VERIFICATION] All OK: {result['all_ok']}")
        for k, v in result.items():
            if k != "all_ok":
                print(f"  {k}: {v}")

    if args.tick_simulator:
        from backtest.tick_simulator import TickLevelMarketSimulator, TickSimulatorConfig
        sim = TickLevelMarketSimulator(TickSimulatorConfig())
        result = sim.simulate_fill(arrival_price=100.0, order_size=5000, queue_depth=20000, volatility=0.02, spread=0.5)
        print(f"\n[TICK SIMULATOR] Fill: {result}")

    if args.shadow_exec:
        from execution.shadow_execution import ShadowExecutionEnvironment
        env = ShadowExecutionEnvironment()
        env.create_shadow("order_1", "THYAO", "buy", 1000, 105.0)
        env.record_live_fill("order_1", 105.2, 50.0)
        alert = env.record_shadow_fill("order_1", 105.3, 80.0, 0.5)
        print(f"\n[SHADOW EXEC] {alert}")

    if args.liquidity_collapse:
        from execution.liquidity_collapse import LiquidityCollapseDetector, LiquidityCollapseConfig
        det = LiquidityCollapseDetector(LiquidityCollapseConfig())
        for _ in range(30):
            det.ingest(imbalance=0.8, spread=0.5 + _*0.01, volume=1_000_000 - _*1000, vpin=0.65)
        pred = det.predict()
        print(f"\n[LIQUIDITY COLLAPSE] {pred}")

    if args.toxic_flow:
        from execution.toxic_flow import ToxicFlowDetector, ToxicFlowConfig
        det = ToxicFlowDetector(ToxicFlowConfig())
        result = det.is_toxic(
            execution_price=100.5, midprice_5min_after=99.8, midprice_1min_after=100.1,
            midprice_at_fill=100.4, price_change=-0.5, size=5000, spread=0.5, adv=1_000_000
        )
        print(f"\n[TOXIC FLOW] {result}")

    if args.factor_exposure:
        from risk.factor_exposure import FactorExposureEngine
        eng = FactorExposureEngine()
        for i in range(60):
            eng.ingest(portfolio_return=0.001 * (i % 5), factor_returns={
                "market_beta": 0.002, "sector_momentum": 0.001, "volatility_factor": -0.0005,
                "momentum_factor": 0.0015, "macro_rates": 0.0001, "macro_fx": -0.0002, "macro_commodities": 0.0003,
            })
        report = eng.get_exposure_report()
        print(f"\n[FACTOR EXPOSURE] Betas: {report.betas}")

    if args.dynamic_hedge:
        from risk.dynamic_hedging import DynamicHedgingEngine
        eng = DynamicHedgingEngine()
        rec = eng.delta_hedge(portfolio_delta=1000, future_delta=50, future_symbol="XU030_FUT", midprice=105.0, spread=0.5)
        print(f"\n[DYNAMIC HEDGE] {rec}")

    if args.regime_predict:
        from agents.regime_predictor import RegimePredictor
        rp = RegimePredictor()
        for i in range(100):
            rp.ingest(regime="bull", features={"volatility_clustering": 0.1, "correlation_breakdown": 0.2, "volume_anomaly": 0.3, "options_skew": -0.1, "credit_spread": 0.05})
        probs = rp.predict_next("bull")
        print(f"\n[REGIME PREDICT] {probs}")

    if args.alpha_decay:
        from agents.alpha_decay import AlphaDecayDetector
        det = AlphaDecayDetector()
        for i in range(25):
            det.ingest_trade(pnl=100 if i % 3 == 0 else -150)
        result = det.check_decay()
        print(f"\n[ALPHA DECAY] {result}")

    if args.strategy_genome:
        from agents.strategy_genome import StrategyGenomeSystem, StrategyGenome
        sg_sys = StrategyGenomeSystem()
        g = sg_sys.create_genome("genome_1", parameters={"ema_fast": 9, "ema_slow": 21})
        child = sg_sys.mutate("genome_1")
        sg_sys.score_genome(child.genome_id, sharpe=1.2, calmar=0.9, max_dd=0.08, regime="bull", paper_trades=150)
        print(f"\n[STRATEGY GENOME] Top: {sg_sys.get_top_genomes(3)}")

    if args.research_agent:
        from agents.research_agents import AutonomousResearchAgent
        agent = AutonomousResearchAgent()
        data = [100 + i + (5 if i == 50 else 0) for i in range(100)]
        result = agent.pipeline(data, "THYAO", "volume", [0.01, -0.02, 0.015, -0.01, 0.02])
        print(f"\n[RESEARCH AGENT] Validated: {result.validated if result else 'N/A'}")

    if args.adversarial_sim:
        from agents.adversarial_simulation import AdversarialSimulation
        sim = AdversarialSimulation()
        def dummy_strategy(state):
            return {"action": "buy", "size": 100}
        result = sim.train(dummy_strategy, episodes=10)
        print(f"\n[ADVERSARIAL SIM] Ready for live: {result['ready_for_live']}")

    if args.macro_ontology:
        from agents.macro_ontology import MacroOntologyEngine
        ont = MacroOntologyEngine()
        ont.add_edge("Fed_rate_hike", "USD_strengthens", 0.8, 1.0)
        ont.add_edge("USD_strengthens", "EM_stress", 0.6, 3.0)
        ont.add_edge("EM_stress", "BIST_outflows", 0.5, 5.0)
        impact = ont.infer_impact("Fed_rate_hike", "BIST_outflows")
        print(f"\n[MACRO ONTOLOGY] Impact probability: {impact:.2%}")

    if args.fpga_shim:
        from infrastructure.fpga_shim import FpgaDriver
        drv = FpgaDriver()
        print(f"\n[FPGA SHIM] {drv.get_latency_assessment()}")

    if args.options_surface:
        from risk.options_vol_surface import OptionsVolatilitySurface, OptionStrike
        surf = OptionsVolatilitySurface(spot=100.0)
        for k in range(90, 111, 5):
            surf.add_strike(OptionStrike(strike=k, expiry_days=30, iv=0.2, open_interest=1000, volume=500, delta=0.5, gamma=0.05, theta=-0.01, vega=0.1))
        print(f"\n[OPTIONS SURFACE] Gamma exposure: {surf.gamma_exposure():.2f}")

    if args.arbitrage_brain:
        from execution.arbitrage_brain import CrossExchangeArbitrageBrain
        brain = CrossExchangeArbitrageBrain()
        brain.update_rtt("binance", 45.0)
        brain.update_rtt("bist", 12.0)
        print(f"\n[ARBITRAGE BRAIN] Best region: {brain.best_region('bist')}")

    if args.rl_execution:
        from execution.rl_execution import RLExecutionPolicy
        policy = RLExecutionPolicy()
        action = policy.select_action([0.6, 0.3, 0.1, -0.2, 0.75, 50.0])
        print(f"\n[RL EXECUTION] Action: {action}")

    if args.gpu_pipeline:
        from optimization.gpu_pipeline import GpuPipeline
        pipe = GpuPipeline(use_gpu=False)
        bench = pipe.benchmark(["THYAO", "GARAN"], {"THYAO": [100.0]*100, "GARAN": [50.0]*100})
        print(f"\n[GPU PIPELINE] {bench}")

    if args.colocation:
        from infrastructure.colocation import ColocationIntelligence
        ci = ColocationIntelligence()
        ci.measure_rtt("binance", "tokyo", 45.0)
        print(f"\n[COLOCATION] Best region for binance: {ci.best_region('binance')}")

    if args.mlops_governance:
        from infrastructure.mlops_governance import MLOpsGovernance, ModelVersion
        gov = MLOpsGovernance()
        gov.register(ModelVersion("model_1", "v1.0", sharpe=1.2, paper_trades=150, shadow_divergence=0.03, approved=True))
        print(f"\n[MLOPS GOVERNANCE] Approval: {gov.approval_status('v1.0')}")

    if args.compliance_engine:
        from compliance.regulatory_engine import ComplianceRegulatoryEngine
        comp = ComplianceRegulatoryEngine()
        comp.log_order_event("order_1", "NEW", {"symbol": "THYAO", "side": "buy", "size": 1000})
        state = comp.reconstruct_state(int(1e18))
        print(f"\n[COMPLIANCE] Events reconstructed: {len(state)}")

    if args.cluster_orchestration:
        from infrastructure.cluster_orchestration import ClusterOrchestrator, StrategyDeployment
        orch = ClusterOrchestrator()
        dep = StrategyDeployment(name="strategy-a", replicas=3, cpu_limit="2", memory_limit="4Gi", strategy_version="v1.0")
        orch.deploy(dep)
        print(f"\n[CLUSTER ORCH] Status: {orch.rolling_update_status()}")

    if len(sys.argv) == 1:
        parser.print_help()


if __name__ == "__main__":
    main()
