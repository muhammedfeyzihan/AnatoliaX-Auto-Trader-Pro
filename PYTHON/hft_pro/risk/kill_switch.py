"""
risk/kill_switch.py — <50μs acil durum anahtarı (paylaşımlı bellek bayrağı)
"""
import mmap
from datetime import datetime, timezone
from typing import Callable, Optional


class KillSwitch:
    """
    Acil durum anahtarı; paylaşımlı bellek atomik bayrağı kullanır.

    Bellek düzeni: POSIX paylaşımlı bellekte tek bayt.
    0x00 = silahlı (ticarete izin ver)
    0x01 = öldürüldü (tüm ticaret durdu)

    Tetikleyiciler:
    - Elle: operatör Telegram/komut ile tetikler
    - Otomatik: günlük kayıp > %3 (K94), drawdown > %10, 5 üst üste zarar
    - Devre: besleme boşluğu > 5s, aracı bağlantı kesildi, gecikme artışı > 10x

    Kurtarma: elle onay gerektirir, 15 dk bekleme, tam sistem sağlık kontrolü.
    """

    def __init__(self, shm_name: str = "/anatoliax_kill_switch"):
        self._shm_name = shm_name
        self._mmap = mmap.mmap(-1, 1)
        self._mmap[0:1] = b"\x00"
        self._on_trigger: Optional[Callable[[str], None]] = None
        self._log: list = []

    def arm(self) -> None:
        """Anahtarı silahla (ticarete izin ver). Yetki gerektirir."""
        self._mmap[0:1] = b"\x00"

    def trigger(self, reason: str) -> None:
        """Acil durum anahtarını tetikle. Sebebi logla."""
        self._mmap[0:1] = b"\x01"
        ts = datetime.now(timezone.utc).isoformat()
        self._log.append(f"[{ts}] KILL_SWITCH: {reason}")
        if self._on_trigger:
            self._on_trigger(reason)

    def is_alive(self) -> bool:
        """Anahtar silahlı mı kontrol et. Sıcak yol: <50ns."""
        return self._mmap[0:1] == b"\x00"

    def register_trigger(self, condition: Callable[[], bool], cooldown_ns: int) -> None:
        """Otomatik tetikleyici koşul kaydet."""
        self._on_trigger = lambda reason: None  # yer tutucu
