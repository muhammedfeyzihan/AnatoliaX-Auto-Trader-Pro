import pytest
from execution.fix_gateway import FixGateway, FixVersion


def test_checksum():
    gw = FixGateway()
    assert gw._checksum(b"ABC") == sum(b"ABC") % 256


def test_send_message_increments_seq():
    gw = FixGateway()
    msg = gw.send_message("D", {"55": "THYAO", "54": "1", "38": "100"})
    assert gw.state.seqnum_out == 1
    assert b"34=1" in msg


def test_message_checksum_validation():
    gw = FixGateway()
    body = b"35=D\x0155=THYAO\x01"
    chksum = gw._checksum(body)
    raw = f"8=FIX.4.4\x019={len(body)}\x01{body.decode()}10={chksum:03d}\x01".encode()
    assert gw.on_message(raw) is True
