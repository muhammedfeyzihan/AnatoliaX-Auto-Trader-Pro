"""
test_replay_engine.py — Tests for DeterministicReplayEngine (K229)
"""
import pytest
import csv
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backtest.replay_engine import DeterministicReplayEngine, Tick


class TestDeterministicReplayEngine:
    def test_load_and_step(self):
        path = "test_ticks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price", "size"])
            writer.writeheader()
            for i in range(5):
                writer.writerow({"timestamp": f"2026-05-22T10:00:0{i}", "price": 100 + i, "size": 10})

        engine = DeterministicReplayEngine(seed=42)
        engine.load_csv(path, timestamp_col="timestamp", price_col="price")
        assert len(engine._ticks) == 5

        tick = engine.step()
        assert tick.price == 100

        os.remove(path)

    def test_run(self):
        path = "test_ticks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price", "size"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"timestamp": f"2026-05-22T10:00:{i:02d}", "price": 100 + i, "size": 10})

        engine = DeterministicReplayEngine(seed=42)
        engine.load_csv(path, timestamp_col="timestamp", price_col="price")
        count = engine.run(max_ticks=3)
        assert count == 3
        assert engine.get_progress()["current"] == 3

        os.remove(path)

    def test_handler(self):
        path = "test_ticks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price"])
            writer.writeheader()
            for i in range(3):
                writer.writerow({"timestamp": f"2026-05-22T10:00:0{i}", "price": 100 + i})

        engine = DeterministicReplayEngine(seed=42)
        engine.load_csv(path, timestamp_col="timestamp", price_col="price")
        received = []
        engine.add_handler(lambda t: received.append(t.price))
        engine.run()
        assert len(received) == 3
        assert received[0] == 100

        os.remove(path)

    def test_reset(self):
        path = "test_ticks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price"])
            writer.writeheader()
            writer.writerow({"timestamp": "2026-05-22T10:00:00", "price": 100})

        engine = DeterministicReplayEngine(seed=42)
        engine.load_csv(path, timestamp_col="timestamp", price_col="price")
        engine.step()
        engine.reset()
        assert engine.get_progress()["current"] == 0

        os.remove(path)

    def test_slice(self):
        path = "test_ticks.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["timestamp", "price"])
            writer.writeheader()
            for i in range(10):
                writer.writerow({"timestamp": f"2026-05-22T10:00:{i:02d}", "price": 100 + i})

        engine = DeterministicReplayEngine(seed=42)
        engine.load_csv(path, timestamp_col="timestamp", price_col="price")
        sliced = engine.slice(2, 5)
        assert len(sliced) == 3
        assert sliced[0].price == 102

        os.remove(path)

    def test_load_df(self):
        import pandas as pd
        df = pd.DataFrame({
            "close": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "volume": [1000, 2000, 3000],
        })
        engine = DeterministicReplayEngine(seed=42)
        engine.load_df(df, symbol="THYAO")
        assert len(engine._ticks) == 3
        assert engine._ticks[0].symbol == "THYAO"
