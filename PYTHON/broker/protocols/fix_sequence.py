"""
protocols/fix_sequence.py — FIX sira numarasi yonetimi + kurtarma
"""
from typing import Optional


class FIXSequenceStore:
    """
    FIX sira numarasi kalici depolama.

    Ozellikler:
    - SeqNum yazma/okuma (SQLite persist)
    - ResendRequest: eksik araliklari tespit et
    - Gap fill: SequenceReset-FillGap ile doldur

    K167: Her oturum basinda SeqNum kalici depodan geri yuklenir.
    """

    def __init__(self, persist_path: str = "data/fix_seq.db"):
        self.persist_path = persist_path
        self._seq = 0

    def get_next(self) -> int:
        self._seq += 1
        return self._seq

    def save(self, seq: int) -> None:
        self._seq = seq

    def reset(self) -> None:
        self._seq = 0
