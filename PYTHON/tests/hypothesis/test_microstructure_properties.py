"""
Property-based tests for execution microstructure.
Invariants: queue_position ∈ [0,1], imbalance ∈ [-1,1], TWAP slices sum to total.
"""
import pytest
from hypothesis import given, strategies as st, settings

from execution.microstructure import (
    ExecutionMicrostructureEngine,
    QueuePositionModel,
    HiddenLiquidityDetector,
    SmartSlicer,
)


class TestMicrostructureProperties:
    @given(
        order_size=st.floats(min_value=1.0, max_value=100000.0),
        book_depth=st.floats(min_value=1.0, max_value=1000000.0),
        arrival_rate=st.floats(min_value=0.1, max_value=1000.0),
    )
    @settings(max_examples=100)
    def test_queue_position_bounded(self, order_size, book_depth, arrival_rate):
        qpm = QueuePositionModel()
        pos = qpm.estimate(order_size, book_depth, arrival_rate)
        assert 0.0 <= pos <= 1.0

    @given(
        bid_vol=st.floats(min_value=0.0, max_value=1000000.0),
        ask_vol=st.floats(min_value=0.0, max_value=1000000.0),
    )
    @settings(max_examples=100)
    def test_imbalance_bounded(self, bid_vol, ask_vol):
        hld = HiddenLiquidityDetector()
        imb = hld.imbalance(bid_vol, ask_vol)
        assert -1.0 <= imb <= 1.0

    @given(
        total_volume=st.floats(min_value=1.0, max_value=100000.0),
        n_slices=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_twap_slices_sum_to_total(self, total_volume, n_slices):
        slicer = SmartSlicer()
        slices = slicer.twap(total_volume, n_slices)
        assert abs(sum(slices) - total_volume) < 1e-6
        assert len(slices) == n_slices
        for s in slices:
            assert s >= 0

    @given(
        weights=st.lists(st.floats(min_value=0.1, max_value=10.0), min_size=1, max_size=50),
        total_volume=st.floats(min_value=1.0, max_value=100000.0),
    )
    @settings(max_examples=100)
    def test_vwap_slices_sum_to_total(self, weights, total_volume):
        slicer = SmartSlicer()
        slices = slicer.vwap(total_volume, weights)
        assert abs(sum(slices) - total_volume) < 1e-6
        assert len(slices) == len(weights)
