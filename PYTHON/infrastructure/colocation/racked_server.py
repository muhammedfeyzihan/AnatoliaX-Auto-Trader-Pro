"""
infrastructure/colocation/racked_server.py — Sunucu/Colocation yonetimi
"""
from dataclasses import dataclass
from typing import List


@dataclass
class ServerNode:
    id: str
    ip: str
    location: str
    latency_us: float
    active: bool = True


class RackedServer:
    """
    Colocation sunucu yonetimi.

    Lokasyonlar:
    - Istanbul: BIST veri merkezi yakinligi
    - Frankfurt: Avrupa borsalari icin
    - New York: NYSE/NASDAQ icin

    K204: Colocation sunucu secimi latency bazli; en dusuk RTT tercih edilir.
    """

    def __init__(self):
        self.nodes: List[ServerNode] = []

    def add(self, node: ServerNode) -> None:
        self.nodes.append(node)

    def best_node(self, market: str = "BIST") -> ServerNode:
        # Istanbul icin en dusuk latency
        candidates = [n for n in self.nodes if n.active and n.location.lower().startswith("istan")]
        return min(candidates, key=lambda n: n.latency_us, default=self.nodes[0])
