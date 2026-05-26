"""
tests/test_fix.py — FIX mesaj birim testleri
"""
import pytest
from broker.protocols.fix_message import FIXMessage


class TestFIXMessage:
    def test_encode_decode_roundtrip(self):
        msg = FIXMessage("D", 1, "SENDER", "TARGET")
        msg.set_field(55, "THYAO")
        msg.set_field(44, "100.50")
        encoded = msg.encode()
        decoded = FIXMessage.decode(encoded)
        assert decoded.msg_type == "D"
        assert decoded.fields[55] == "THYAO"
        assert decoded.fields[44] == "100.50"

    def test_checksum_nonzero(self):
        msg = FIXMessage("A", 1, "A", "B")
        data = msg.encode()
        assert b"10=" in data
