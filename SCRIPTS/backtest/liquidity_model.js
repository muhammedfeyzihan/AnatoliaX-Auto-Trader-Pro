// ============================================================
// liquidity_model.js - Derinlik/Liquidity Model (K135)
// ============================================================

class LiquidityModel {
    constructor(config = {}) {
        this.minDepth = config.minDepth || 100000;
        this.depthFactor = config.depthFactor || 0.01;
    }

    estimateDepth(avgVolume, bidAskSpread) {
        const depth = avgVolume * this.depthFactor / (bidAskSpread * 100);
        return { depth, adequate: depth >= this.minDepth, spread: bidAskSpread };
    }

    canFill(orderValue, avgVolume, bidAskSpread) {
        const { depth, adequate } = this.estimateDepth(avgVolume, bidAskSpread);
        return adequate && orderValue <= depth * 0.1;
    }
}

module.exports = LiquidityModel;
