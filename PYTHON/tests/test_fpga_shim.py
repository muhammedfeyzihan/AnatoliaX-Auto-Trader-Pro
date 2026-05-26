import pytest
from infrastructure.fpga_shim import PythonFpgaShim, FpgaDriver


def test_python_fpga_shim_parse_feed():
    shim = PythonFpgaShim()
    result = shim.parse_feed(b"raw_data")
    assert result["symbol"] == "THYAO"
    assert "price" in result


def test_python_fpga_shim_encode_order():
    shim = PythonFpgaShim()
    encoded = shim.encode_order({"symbol": "THYAO", "price": 100})
    assert isinstance(encoded, bytes)


def test_python_fpga_shim_checksum():
    shim = PythonFpgaShim()
    cs = shim.checksum(b"abc")
    assert 0 <= cs <= 255


def test_fpga_driver_latency_assessment():
    driver = FpgaDriver()
    assessment = driver.get_latency_assessment()
    assert "python_hot_path_us" in assessment
    assert "fpga_target_ns" in assessment


def test_fpga_driver_registers():
    driver = FpgaDriver()
    driver.write_register(0x100, 42)
    assert driver.read_register(0x100) == 0  # stub returns 0
