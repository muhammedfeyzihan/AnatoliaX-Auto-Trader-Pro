"""
bist/session_hours.py — BIST seans saatleri (09:15-18:00, VIOP 09:15-18:15)
"""
from dataclasses import dataclass
from datetime import time


@dataclass
class Session:
    name: str
    start: time
    end: time


class SessionHours:
    """
    BIST seans saatleri.

    Pay Piyasasi:
    - Sabah: 09:15 - 12:30
    - Ogle: 13:30 - 18:00
    - Tek Fiyat: 09:15 - 09:30 (acilis), 17:55 - 18:00 (kapanis)

    VIOP:
    - Sabah: 09:15 - 12:30
    - Ogle: 13:30 - 18:15
    """

    PAY = [
        Session("sabah", time(9, 15), time(12, 30)),
        Session("ogle", time(13, 30), time(18, 0)),
    ]

    VIOP = [
        Session("sabah", time(9, 15), time(12, 30)),
        Session("ogle", time(13, 30), time(18, 15)),
    ]
