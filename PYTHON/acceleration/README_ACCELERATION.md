# GPU/FPGA Acceleration

**Versiyon:** 1.0.0 | **Modul:** `PYTHON/acceleration/`

## Ozet

CUDA, RAPIDS cuDF, ONNX Runtime GPU ve Xilinx Alveo FPGA hizlandirma katmani.

## Bilesenler

- `gpu/` — CUDA baglami, RAPIDS cuDF ozellik hesaplama, CuPy RawKernels, ONNX GPU, gorev zamanlayicisi
- `fpga/` — Xilinx Alveo arayuzu, Verilog sablonlari (feed_parser, order_book, top_level)
- `cpp_shim/` — pybind11 C++ baglantisi (NanosecondClock, ParsedTick, OrderBook)
- `benchmarks/` — Hizlandirma benchmark paketi (3x+ hizlanma hedefi)

## Kural Uyumu

- K95: Gunluk kayip limiti %3 (GPU ile daha hizli risk kontrolu)
- K142-K148: BIST duzenlemeleri
