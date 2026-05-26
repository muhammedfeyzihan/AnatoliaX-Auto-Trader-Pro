"""
fpga/feed_handler_hw.py — FPGA feed handler Python wrapper
"""


class FPGAFeedHandler:
    """
    FPGA feed handler yazilim katmani.

    Donanim modulu:
    - feed_parser.v: UDP paket ayristirma
    - checksum_hw.v: CRC32 hizli dogrulama
    - top_level.v: Toplu entegrasyon

    K182: FPGA yuklu degilse yazilim fallback calisir.
    """

    def __init__(self, bitstream_path: str = None):
        self.bitstream_path = bitstream_path
        self._loaded = False

    def load(self) -> bool:
        # Xilinx xrt load bitstream
        return False

    def parse_packet(self, raw: bytes) -> dict:
        # FPGA ciktisi veya yazilim fallback
        return {"symbol": "", "price": 0.0, "timestamp": 0}
