"""
fpga/fpga_interface.py — FPGA soyut arayuzu
"""
from abc import ABC, abstractmethod
from typing import Optional


class FPGAInterface(ABC):
    """
    FPGA hizlandirici soyut arayuzu.

    Uygulamalar:
    - XilinxAlveoInterface
    - IntelStratixInterface (yer tutucu)
    """

    @abstractmethod
    def open(self) -> bool:
        """Cihazi ac ve XRT surucusunu baslat."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Cihazi kapat."""
        pass

    @abstractmethod
    def load_bitstream(self, xclbin_path: str) -> bool:
        """XCLBIN bit akisini yukle."""
        pass

    @abstractmethod
    def allocate_buffer(self, size_bytes: int) -> Optional[object]:
        """HBM bellek havuzu ayir."""
        pass

    @abstractmethod
    def run_kernel(self, kernel_name: str, buffers: list, dims: tuple) -> None:
        """Kernel calistir."""
        pass


class XilinxAlveoInterface(FPGAInterface):
    """
    Xilinx Alveo FPGA arayuzu (pyxrt tabanli).

    Cihaz: Alveo U50 / U200 / U250
    HBM: 8GB / 16GB / 32GB
    Kernel: feed_parser, order_book, ema
    """

    def __init__(self, device_index: int = 0):
        self.device_index = device_index
        self._device = None
        self._kernel = None

    def open(self) -> bool:
        try:
            import pyxrt
            self._device = pyxrt.device(self.device_index)
            return True
        except Exception:
            return False

    def close(self) -> None:
        if self._device:
            self._device.close()

    def load_bitstream(self, xclbin_path: str) -> bool:
        # Yer tutucu: gercek XCLBIN yukleme ileride implemente edilecek
        return True

    def allocate_buffer(self, size_bytes: int):
        # Yer tutucu
        return None

    def run_kernel(self, kernel_name: str, buffers: list, dims: tuple) -> None:
        # Yer tutucu
        pass
