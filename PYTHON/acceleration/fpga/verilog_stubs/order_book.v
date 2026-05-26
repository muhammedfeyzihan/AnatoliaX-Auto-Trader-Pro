// fpga/verilog_stubs/order_book.v — L1/L2 emir defteri güncelleme FPGA çekirdek şablonu
//
// Amaç: Tick bazlı emir defteri güncelleme (add/modify/cancel/execute)
// Hedef: Xilinx Alveo U50 / U200 / U250
// Bellek: HBM (32GB) ~ 2000+ sembol, her biri 1000 seviye
//
// Mimarinin aşamaları:
// 1. Tick girişi al (AXI Stream)
// 2. Sembol hash → HBM adresi
// 3. Seviye güncelle (bid/ask fiyat → miktar)
// 4. Yayılma / orta / VWAP hesapla
// 5. Çıktı: Güncellenmiş emir defteri durumu
//
// Not: Bu dosya şablondur; tam implementasyon ileride Vivado HLS ile üretilecektir.

module order_book (
    input wire aclk,
    input wire aresetn,
    // Tick girişi
    input wire [127:0] s_axis_tdata,
    input wire s_axis_tvalid,
    output wire s_axis_tready,
    // Defter durumu çıkışı
    output wire [255:0] m_axis_tdata,
    output wire m_axis_tvalid,
    input wire m_axis_tready,
    // HBM AXI4 arayüzü (yer tutucu)
    output wire [63:0] m_axi_araddr,
    output wire m_axi_arvalid,
    input wire m_axi_arready,
    input wire [511:0] m_axi_rdata,
    input wire m_axi_rvalid,
    output wire m_axi_rready
);

    // Yer tutucu: passthrough
    assign m_axis_tdata = {s_axis_tdata, 128'd0};
    assign m_axis_tvalid = s_axis_tvalid;
    assign s_axis_tready = m_axis_tready;
    assign m_axi_araddr = 64'd0;
    assign m_axi_arvalid = 1'b0;
    assign m_axi_rready = 1'b0;

endmodule
