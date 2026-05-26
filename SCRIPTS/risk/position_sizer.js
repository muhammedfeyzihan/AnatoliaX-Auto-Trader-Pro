// ============================================================
// position_sizer.js - Kelly Criterion + Pozisyon Boyutu (K128)
// ============================================================

const logger = require('../core/logger');

class PositionSizer {
    constructor(config = {}) {
        this.config = config;
    }

    kelly(winRate, avgWin, avgLoss, minRR) {
        const b = avgWin / avgLoss;
        const f = (winRate * b - (1 - winRate)) / b;
        if (f >= 0.5) return 0.02;
        if (f >= 0.2) return 0.015;
        if (f >= 0) return 0.01;
        return 0;
    }

    fixedFractional(capital, riskPct, entry, stopLoss) {
        const riskAmount = capital * riskPct;
        const riskPerShare = Math.abs(entry - stopLoss);
        if (riskPerShare <= 0) return 0;
        return Math.floor(riskAmount / riskPerShare);
    }

    fixedRatio(capital, delta, equity) {
        const deltaValue = delta || 1000;
        const ratio = Math.floor(equity / deltaValue);
        return Math.max(1, ratio);
    }

    optimalF(capital, returns) {
        if (!returns.length) return 0;
        let bestF = 0;
        let bestGeoMean = -Infinity;
        for (let f = 0.01; f <= 0.5; f += 0.01) {
            const growth = returns.map(r => 1 + f * r);
            const geoMean = Math.pow(growth.reduce((a, b) => a * b, 1), 1 / growth.length);
            if (geoMean > bestGeoMean) {
                bestGeoMean = geoMean;
                bestF = f;
            }
        }
        return bestF;
    }

    size(capital, entry, stopLoss, takeProfit, winRate = 0.5, method = 'kelly') {
        const riskPerShare = Math.abs(entry - stopLoss);
        const rewardPerShare = Math.abs(takeProfit - entry);
        const rr = riskPerShare > 0 ? rewardPerShare / riskPerShare : 0;

        let fraction;
        switch (method) {
            case 'kelly':
                fraction = this.kelly(winRate, rewardPerShare, riskPerShare);
                break;
            case 'fixed_fractional':
                fraction = this.config.fixedRiskPct || 0.01;
                break;
            case 'fixed_ratio':
                return this.fixedRatio(capital, this.config.delta, capital);
            default:
                fraction = 0.01;
        }

        const maxRiskAmount = capital * fraction;
        const qty = Math.floor(maxRiskAmount / riskPerShare);
        const positionValue = qty * entry;
        const riskPct = capital > 0 ? (qty * riskPerShare) / capital : 0;

        logger.info(`[POSITION] ${method} | Qty: ${qty} | Value: ${positionValue.toFixed(2)} | Risk: ${(riskPct*100).toFixed(2)}% | R:R ${rr.toFixed(2)}`);

        return { qty, positionValue, riskAmount: qty * riskPerShare, riskPct, rr, method };
    }
}

module.exports = PositionSizer;
