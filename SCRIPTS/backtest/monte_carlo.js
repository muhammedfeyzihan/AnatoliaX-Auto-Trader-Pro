// ============================================================
// monte_carlo.js - Monte Carlo Simulation (K119)
// ============================================================

const logger = require('../core/logger');

class MonteCarloSimulation {
    constructor(config = {}) {
        this.simulations = config.simulations || 10000;
        this.initialCapital = config.initialCapital || 100000;
    }

    run(winRate, avgWin, avgLoss, trades = 100) {
        const results = [];
        for (let i = 0; i < this.simulations; i++) {
            let capital = this.initialCapital;
            for (let t = 0; t < trades; t++) {
                if (Math.random() < winRate) {
                    capital *= (1 + avgWin);
                } else {
                    capital *= (1 - avgLoss);
                }
            }
            results.push(capital);
        }

        results.sort((a, b) => a - b);
        const best = results[results.length - 1];
        const worst = results[0];
        const avg = results.reduce((s, v) => s + v, 0) / results.length;
        const median = results[Math.floor(results.length * 0.5)];
        const p5 = results[Math.floor(results.length * 0.05)];
        const p95 = results[Math.floor(results.length * 0.95)];
        const lossProb = results.filter(v => v < this.initialCapital).length / results.length;
        const maxDD = this._calcMaxDD(results);

        logger.info(`[MONTECARLO] ${this.simulations} sim | CI95: [${p5.toFixed(0)}, ${p95.toFixed(0)}] | Loss prob: ${(lossProb*100).toFixed(1)}%`);

        return {
            simulations: this.simulations,
            best, worst, avg, median,
            confidence95: [p5, p95],
            lossProbability: lossProb,
            maxDrawdown: maxDD,
            positive: p5 > this.initialCapital,
        };
    }

    _calcMaxDD(values) {
        let peak = values[0];
        let maxDD = 0;
        for (const v of values) {
            if (v > peak) peak = v;
            const dd = (peak - v) / peak;
            if (dd > maxDD) maxDD = dd;
        }
        return maxDD;
    }
}

module.exports = MonteCarloSimulation;
