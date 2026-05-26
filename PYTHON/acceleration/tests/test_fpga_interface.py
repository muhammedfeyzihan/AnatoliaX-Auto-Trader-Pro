"""
tests/test_fpga_interface.py — FPGA interface testleri
"""
import unittest
from PYTHON.acceleration.fpga.fpga_interface import FPGAInterface


class TestFPGAInterface(unittest.TestCase):
    def test_init(self):
        fpga = FPGAInterface()
        self.assertIsNotNone(fpga)

    def test_not_available(self):
        fpga = FPGAInterface()
        self.assertFalse(fpga.is_available())


if __name__ == "__main__":
    unittest.main()
