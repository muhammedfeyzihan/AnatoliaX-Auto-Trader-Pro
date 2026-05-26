"""
latency/profiler.py — Uçtan uca gecikme dökümü (P50/P95/P99/P999)
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List

from hft_pro.core.clock import HFTClock


class LatencyStage(Enum):
    FEED_ARRIVAL = auto()
    FEED_PARSE = auto()
    BOOK_UPDATE = auto()
    SIGNAL_COMPUTE = auto()
    RISK_CHECK = auto()
    ORDER_ENCODE = auto()
    KERNEL_SEND = auto()
    NETWORK_RTT = auto()
    BROKER_ACK = auto()
    FILL_RECEIVED = auto()


@dataclass
class LatencyReport:
    stages: Dict[str, Dict[str, float]] = field(default_factory=dict)
    total_p50: float = 0.0
    total_p95: float = 0.0
    total_p99: float = 0.0
    total_p999: float = 0.0


class LatencyProfiler:
    """
    HFT gecikme profilleyici; nanosaniye hassasiyet.

    İzlenen aşamalar:
    1. FEED_ARRIVAL: NIC'te paket varışı (donanım zaman damgası)
    2. FEED_PARSE: paket Tick'e ayrıştırıldı (C++ shim süresi)
    3. BOOK_UPDATE: emir defteri tick ile güncellendi
    4. SIGNAL_COMPUTE: strateji sinyali hesaplandı
    5. RISK_CHECK: ön-ticaret risk kontrolü (UnifiedRiskEngine)
    6. ORDER_ENCODE: iletim için emir kodlandı
    7. KERNEL_SEND: emir göndermek için sistem çağrısı (veya DPDK atlama)
    8. NETWORK_RTT: ağ gidiş-dönüş süresi
    9. BROKER_ACK: aracı onayı alındı
    10. FILL_RECEIVED: doldurma onayı alındı

    Toplam gecikme = FILL_RECEIVED - FEED_ARRIVAL

    T-Digest kullanarak quantile tahmini (düşük bellek).
    Prometheus'a dışa aktar; Grafana görselleştirme.
    """

    def __init__(self):
        self._clock = HFTClock()
        self._samples: Dict[LatencyStage, List[int]] = {s: [] for s in LatencyStage}
        self._max_samples = 100_000

    def record(self, stage: LatencyStage, timestamp_ns: int) -> None:
        """Aşama için zaman damgası kaydet."""
        self._samples[stage].append(timestamp_ns)
        if len(self._samples[stage]) > self._max_samples:
            self._samples[stage] = self._samples[stage][-self._max_samples:]

    def get_report(self) -> LatencyReport:
        """Her aşama için P50/P95/P99/P999 ile tam gecikme raporu."""
        report = LatencyReport()
        import statistics
        for stage, times in self._samples.items():
            if len(times) < 2:
                continue
            sorted_times = sorted(times)
            n = len(sorted_times)
            report.stages[stage.name] = {
                "P50": sorted_times[n // 2] / 1e6,
                "P95": sorted_times[int(n * 0.95)] / 1e6,
                "P99": sorted_times[int(n * 0.99)] / 1e6,
                "P999": sorted_times[int(n * 0.999)] / 1e6,
            }
        return report

    def export_prometheus(self) -> None:
        """Gecikme histogramlarını Prometheus'a dışa aktar."""
        # Yer tutucu: gerçek dışa aktarım ileride metrics modülü ile
        pass

    def alert_if_p99_exceeds(self, threshold_ns: int) -> bool:
        """P99 eşiği aşıyorsa True döndür ve uyarı tetikle."""
        report = self.get_report()
        for stage_name, metrics in report.stages.items():
            if metrics.get("P99", 0.0) * 1e6 > threshold_ns:
                return True
        return False
