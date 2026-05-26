"""
protocols/fix_session.py — FIX oturum yonetimi (durum makinesi + sira kurtarma)
"""
import asyncio
from enum import Enum, auto
from typing import Callable, Optional

from broker.protocols.fix_message import FIXMessage


class SessionState(Enum):
    DISCONNECTED = auto()
    CONNECTING = auto()
    LOGON_SENT = auto()
    LOGON_CONFIRMED = auto()
    ACTIVE = auto()
    RECOVERING = auto()
    DISCONNECTING = auto()


class FIXSession:
    """
    FIX 4.2/4.4 oturum yoneticisi.

    Durum makinesi:
    DISCONNECTED -> CONNECTING -> LOGON_SENT -> LOGON_CONFIRMED -> ACTIVE
    Hata -> RECOVERING -> ACTIVE
    Kapatma -> DISCONNECTING -> DISCONNECTED

    Sira kurtarma:
    - Beklenen sira != alinan sira: ResendRequest gonder
    - 3 dakika icinde yoklama alinmazsa: TestRequest gonder, sonra Logout

    Kalp atisi:
    - HeartbeatInterval = 30s (varsayilan)
    """

    def __init__(self, sender: str, target: str, heartbeat_sec: int = 30):
        self.sender = sender
        self.target = target
        self.heartbeat_sec = heartbeat_sec
        self.state = SessionState.DISCONNECTED
        self._seq_num = 1
        self._expected_seq = 1
        self._on_message: Optional[Callable[[FIXMessage], None]] = None
        self._transport = None

    async def connect(self, host: str, port: int) -> bool:
        self.state = SessionState.CONNECTING
        # Yer tutucu: gercek TCP baglantisi ileride implemente edilecek
        self.state = SessionState.LOGON_SENT
        logon = FIXMessage("A", self._seq_num, self.sender, self.target)
        logon.set_field(98, "0")
        logon.set_field(108, str(self.heartbeat_sec))
        await self._send(logon.encode())
        self._seq_num += 1
        self.state = SessionState.ACTIVE
        asyncio.create_task(self._heartbeat_loop())
        return True

    async def disconnect(self) -> None:
        self.state = SessionState.DISCONNECTING
        logout = FIXMessage("5", self._seq_num, self.sender, self.target)
        await self._send(logout.encode())
        self.state = SessionState.DISCONNECTED

    async def send(self, msg: FIXMessage) -> None:
        msg.seq_num = self._seq_num
        await self._send(msg.encode())
        self._seq_num += 1

    def register_message_handler(self, handler: Callable[[FIXMessage], None]) -> None:
        self._on_message = handler

    async def _send(self, data: bytes) -> None:
        # Yer tutucu: gercek TCP iletimi ileride implemente edilecek
        pass

    async def _heartbeat_loop(self) -> None:
        while self.state == SessionState.ACTIVE:
            await asyncio.sleep(self.heartbeat_sec)
            hb = FIXMessage("0", self._seq_num, self.sender, self.target)
            await self._send(hb.encode())
            self._seq_num += 1
