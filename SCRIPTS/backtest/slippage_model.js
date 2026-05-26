// ============================================================
// slippage_model.js - Liquidity/Slippage Model (K135)
// Hacme bagli slippage: Dusuk hacim = yuksek slippage.
// ============================================================

class SlippageModel {
    constructor(config = {}) {
        this.baseSlippage = config.baseSlippage || 0.001;
        this.volumeThreshold = config.volumeThreshold || 1000000;
        this.maxSlippage = config.maxSlippage || 0.01;
    }

    calculate(orderQty, avgDailyVolume, spread = 0.002) {
        const participation = avgDailyVolume > 0 ? orderQty / avgDailyVolume : 1;
        const impact = this.baseSlippage * Math.pow(participation * 10, 0.5);
        const spreadCost = spread * 0.5;
        const totalSlippage = Math.min(impact + spreadCost, this.maxSlippage);
        return {
            slippage: totalSlippage,
            impactCost: impact,
            spreadCost,
            adjustedPrice: totalSlippage,
            note: participation > 0.1 ? 'YUKSEK_SLIPPAGE: Hacim dusuk' : '',
        };
    }

    applyToPrice(price, orderQty, avgDailyVolume, side = 'BUY') {
        const slip = this.calculate(orderQty, avgDailyVolume);
        const multiplier = side === 'BUY' ? 1 + slip.slippage : 1 - slip.slippage;
        return {
            originalPrice: price,
            executedPrice: price * multiplier,
            slippage: slip.slippage,
            cost: price * slip.slippage * orderQty,
        };
    }
}

module.exports = SlippageModel;
