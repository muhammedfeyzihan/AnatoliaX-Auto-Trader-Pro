// fpga/verilog_stubs/top_level.v — FPGA top-level entegrasyon şablonu
//
// Amaç: feed_parser + order_book + ema_update kernel'lerini tek XCLBIN'de birleştir
// Hedef: Xilinx Alveo U50
//
// Akış:
// 1. UDP payload → feed_parser → Tick
// 2. Tick → order_book → Güncellenmiş defter
// 3. Fiyat → ema_update → EMA değeri
// 4. Hepsi HBM üzerinden host'a bildirilir
//
// Not: Bu dosya şablondur; tam implementasyon ileride Vivado ile üretilecektir.

module top_level (
    input wire aclk,
    input wire aresetn,
    // QSFP+ 100G Ethernet AXI Stream (yer tutucu)
    input wire [511:0] qsfp_rx_tdata,
    input wire qsfp_rx_tvalid,
    output wire qsfp_rx_tready,
    // Host DMA AXI Stream çıkışı
    output wire [511:0] host_tx_tdata,
    output wire host_tx_tvalid,
    input wire host_tx_tready,
    // Kontrol kaydediciler (host üzerinden)
    input wire [31:0] ctrl_reg,
    output wire [31:0] status_reg
);

    wire [127:0] tick_data;
    wire tick_valid;
    wire tick_ready;

    feed_parser fp_inst (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_axis_tdata(qsfp_rx_tdata),
        .s_axis_tvalid(qsfp_rx_tvalid),
        .s_axis_tready(qsfp_rx_tready),
        .s_axis_tlast(1'b0),
        .m_axis_tdata(tick_data),
        .m_axis_tvalid(tick_valid),
        .m_axis_tready(tick_ready),
        .m_axis_tlast(),
        .packet_count(),
        .error_count()
    );

    order_book ob_inst (
        .aclk(aclk),
        .aresetn(aresetn),
        .s_axis_tdata(tick_data),
        .s_axis_tvalid(tick_valid),
        .s_axis_tready(tick_ready),
        .m_axis_tdata(host_tx_tdata[255:0]),
        .m_axis_tvalid(host_tx_tvalid),
        .m_axis_tready(host_tx_tready),
        .m_axi_araddr(),
        .m_axi_arvalid(),
        .m_axi_arready(1'b1),
        .m_axi_rdata(512'd0),
        .m_axi_rvalid(1'b0),
        .m_axi_rready()
    );

    assign status_reg = 32'hDEAD_BEEF;

endmodule
