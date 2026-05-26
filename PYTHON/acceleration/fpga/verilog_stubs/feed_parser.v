// fpga/verilog_stubs/feed_parser.v — FIX/UDP paket ayrıştırıcı FPGA çekirdek şablonu
//
// Amaç: NIC'ten gelen ham UDP paketleri parse edip Tick struct'a dönüştür
// Hedef: Xilinx Alveo U50 / U200 / U250
// Bellek: HBM (8GB-32GB)
//
// Mimarinin aşamaları:
// 1. RX AXI Stream (512-bit) UDP payload al
// 2. Field extraction: Sembol, Fiyat, Miktar, Zaman damgası
// 3. CRC/Checksum doğrulama
// 4. Çıktı: AXI Stream Tick struct (128-bit)
//
// Performans hedefi: 10M paket/saniye (line rate)
//
// Not: Bu dosya şablondur; tam implementasyon ileride Vivado HLS ile üretilecektir.

module feed_parser (
    input wire aclk,
    input wire aresetn,
    // AXI Stream giriş (UDP payload)
    input wire [511:0] s_axis_tdata,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    input wire s_axis_tlast,
    // AXI Stream çıkış (Parsed Tick)
    output wire [127:0] m_axis_tdata,
    output wire m_axis_tvalid,
    input wire m_axis_tready,
    output wire m_axis_tlast,
    // Kontrol / durum
    output wire [31:0] packet_count,
    output wire [31:0] error_count
);

    // Yer tutucu: AXI Stream passthrough
    assign m_axis_tdata = s_axis_tdata[127:0];
    assign m_axis_tvalid = s_axis_tvalid;
    assign s_axis_tready = m_axis_tready;
    assign m_axis_tlast = s_axis_tlast;
    assign packet_count = 32'd0;
    assign error_count = 32'd0;

endmodule
