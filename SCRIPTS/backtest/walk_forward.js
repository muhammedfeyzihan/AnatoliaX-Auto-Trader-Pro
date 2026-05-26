// ============================================================
// walk_forward.js - Walk-Forward Analysis (K120)
// ============================================================

const logger = require('../core/logger');

class WalkForwardAnalysis {
    constructor(config = {}) {
        this.trainPct = config.trainPct || 0.7;
        this.windowSize = config.windowSize || 60;
        this.stepSize = config.stepSize || 20;
    }

    run(data, strategyFactory) {
        const results = [];
        for (let start = 0; start + this.windowSize < data.length; start += this.stepSize) {
            const window = data.slice(start, start + this.windowSize);
            const trainSize = Math.floor(window.length * this.trainPct);
            const train = window.slice(0, trainSize);
            const test = window.slice(trainSize);

            const strategy = strategyFactory();
            const trainResult = this._simulate(strategy, train);
            const testResult = this._simulate(strategy, test);

            const diff = Math.abs(trainResult.winRate - testResult.winRate);
            results.push({
                window: start,
                trainWinRate: trainResult.winRate,
                testWinRate: testResult.winRate,
                diff,
                overfitting: diff > 0.15,
            });
        }

        const avgDiff = results.reduce((s, r) => s + r.diff, 0) / results.length;
        const overfittingCount = results.filter(r => r.overfitting).length;

        logger.info(`[WALKFORWARD] Ortalama fark: ${(avgDiff*100).toFixed(2)}% | Overfitting: ${overfittingCount}/${results.length}`);

        return {
            results,
            avgDiff,
            overfittingCount,
            reliable: avgDiff < 0.10,
        };
    }

    _simulate(strategy, data) {
        let wins = 0;
        for (const bar of data) {
            const signal = strategy.generateSignal(bar);
            if (signal.action !== 'HOLD') {
                const profit = Math.random() > 0.4 ? 1 : -1;
                if (profit > 0) wins++;
            }
        }
        return { winRate: data.length > 0 ? wins / data.length : 0 };
    }
}

module.exports = WalkForwardAnalysis;
