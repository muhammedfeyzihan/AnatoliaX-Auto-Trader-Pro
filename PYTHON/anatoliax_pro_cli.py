"""
anatoliax_pro_cli.py — AnatoliaX Pro unified CLI (main.py'ye dokunulmadan)

Komutlar:
    hft-pro        — HFT Pro modulunu calistir
    broker-trade   — Broker modulunu calistir
    benchmark-gpu  — GPU benchmark calistir
    dev-task       — Ajan gorevi olustur
    dev-status     — Ajan durumunu goster
    dev-review     — Kod incelemesi iste

Kullanim:
    python PYTHON/anatoliax_pro_cli.py hft-pro --config CONFIG/hft_pro.yaml
"""
import argparse
import sys
from pathlib import Path

# Proje kokunu PYTHONPATH'e ekle
sys.path.insert(0, str(Path(__file__).resolve().parent))


def cmd_hft_pro(args):
    from hft_pro.core.clock import HFTClock
    from hft_pro.core.ring_buffer import LockFreeRingBuffer
    print("[HFT Pro] Baslatiliyor...")
    clock = HFTClock()
    rb = LockFreeRingBuffer(capacity=1024, dtype="float64")
    print(f"[HFT Pro] Saat: {clock.now_ns()} ns | Ring buffer: {rb.utilization()}/{rb.capacity}")


def cmd_broker_trade(args):
    from broker.adapters.mock_broker import MockBroker
    from broker.core.broker_interface import Order, OrderSide, OrderType
    from broker.core.order_validator import OrderValidator
    import asyncio
    print("[Broker] Baslatiliyor...")
    broker = MockBroker()
    validator = OrderValidator()
    order = Order(symbol="THYAO", side=OrderSide.BUY, quantity=10, price=100.0, order_type=OrderType.LIMIT)
    errors = validator.validate(order)
    if errors:
        print("[Broker] HATA:", errors)
    else:
        report = asyncio.run(broker.place_order(order))
        print(f"[Broker] Emir durumu: {report.status.name}")


def cmd_benchmark_gpu(args):
    from acceleration.benchmarks.gpu_benchmark import AccelerationBenchmark
    print("[Benchmark] GPU/CPU hizlandirma testleri calistiriliyor...")
    bench = AccelerationBenchmark()
    results = bench.run_all()
    for r in results:
        print(f"  {r.name}: CPU={r.cpu_time_ms:.2f}ms GPU={r.gpu_time_ms:.2f}ms Speedup={r.speedup:.1f}x")


def cmd_dev_task(args):
    from agents.orchestrator import AgentOrchestrator
    orch = AgentOrchestrator()
    plan = orch.decompose(args.description)
    print(f"[Dev] Gorev: {plan.task_id} | Ajan: {plan.assigned_agent} | Adimlar: {plan.steps}")


def cmd_dev_status(args):
    print("[Dev] Ajan durumu: idle")


def cmd_dev_review(args):
    from agents.kimi_bridge import KimiBridge
    kimi = KimiBridge(api_key="")
    result = kimi.review_code(args.file_path)
    print(f"[Dev] Kimi incelemesi: {result}")


def main():
    parser = argparse.ArgumentParser(description="AnatoliaX Pro Unified CLI")
    sub = parser.add_subparsers(dest="command")

    p_hft = sub.add_parser("hft-pro", help="HFT Pro modulunu calistir")
    p_hft.add_argument("--config", default="CONFIG/hft_pro.yaml")

    p_broker = sub.add_parser("broker-trade", help="Broker modulunu calistir")
    p_broker.add_argument("--config", default="CONFIG/broker.yaml")

    p_bench = sub.add_parser("benchmark-gpu", help="GPU benchmark calistir")

    p_task = sub.add_parser("dev-task", help="Ajan gorevi olustur")
    p_task.add_argument("description")

    p_status = sub.add_parser("dev-status", help="Ajan durumunu goster")

    p_review = sub.add_parser("dev-review", help="Kod incelemesi iste")
    p_review.add_argument("file_path")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "hft-pro": cmd_hft_pro,
        "broker-trade": cmd_broker_trade,
        "benchmark-gpu": cmd_benchmark_gpu,
        "dev-task": cmd_dev_task,
        "dev-status": cmd_dev_status,
        "dev-review": cmd_dev_review,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
