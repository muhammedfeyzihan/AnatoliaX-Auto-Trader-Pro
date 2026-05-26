"""
fpga/checksum_hw.py — FPGA checksum dogrulama
"""
import zlib


class FPGAChecksum:
    """
    FPGA checksum dogrulama katmani.

    Donanim modulu:
    - checksum_hw.v: CRC32/Adler32 pipeline

    K184: FPGA checksum yazilim fallback ile ayni sonucu vermeli.
    """

    @staticmethod
    def crc32(data: bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF
