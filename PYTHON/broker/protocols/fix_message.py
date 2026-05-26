"""
protocols/fix_message.py — FIX mesaj insa/ayristirici + checksum
"""
from typing import Dict, List


class FIXMessage:
    """
    FIX 4.2/4.4 mesaj insa edici ve ayristirici.

    Yapilandirma:
    - BeginString (8), MsgType (35), MsgSeqNum (34), SenderCompID (49), TargetCompID (56)
    - Checksum: MOD 256 toplam, 3 haneli

    Akis:
    1. Yapilandirma mesaji olustur
    2. Checksum hesapla
    3. Dize olarak ilet
    4. Gelen mesaji sozluk olarak ayristir
    """

    def __init__(self, msg_type: str, seq_num: int, sender: str, target: str, version: str = "FIX.4.4"):
        self.msg_type = msg_type
        self.seq_num = seq_num
        self.sender = sender
        self.target = target
        self.version = version
        self.fields: Dict[int, str] = {}

    def set_field(self, tag: int, value: str) -> None:
        self.fields[tag] = value

    def encode(self) -> bytes:
        parts = [f"8={self.version}\x01", f"9=0000\x01", f"35={self.msg_type}\x01"]
        parts.append(f"34={self.seq_num}\x01")
        parts.append(f"49={self.sender}\x01")
        parts.append(f"56={self.target}\x01")
        for tag, value in sorted(self.fields.items()):
            parts.append(f"{tag}={value}\x01")
        body = "".join(parts[2:])
        body_len = len(body.encode("ascii"))
        parts[1] = f"9={body_len}\x01"
        msg = "".join(parts)
        chk = self._checksum(msg)
        msg += f"10={chk:03d}\x01"
        return msg.encode("ascii")

    @staticmethod
    def decode(data: bytes) -> "FIXMessage":
        raw = data.decode("ascii").replace("\x01", "|").rstrip("|")
        pairs = {}
        for item in raw.split("|"):
            if "=" in item:
                k, v = item.split("=", 1)
                pairs[int(k)] = v
        msg = FIXMessage(
            msg_type=pairs.get(35, ""),
            seq_num=int(pairs.get(34, 0)),
            sender=pairs.get(49, ""),
            target=pairs.get(56, ""),
            version=pairs.get(8, "FIX.4.4"),
        )
        msg.fields = {k: v for k, v in pairs.items() if k not in (8, 9, 35, 34, 49, 56, 10)}
        return msg

    @staticmethod
    def _checksum(msg_without_10: str) -> int:
        total = sum(msg_without_10.encode("ascii"))
        return total % 256
