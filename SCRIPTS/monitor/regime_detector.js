// ============================================================
// regime_detector.js - Piyasa Rejimi Tespiti (K136)
// State machine tabanli. BULL/BEAR/SIDEWAYS/VOLATILE/CRASH.
// ============================================================

const { MarketRegimeDetector } = require('../core/patterns/state_machine');
const logger = require('../core/logger');
const eventBus = require('../core/event_bus');

class RegimeDetector {
    constructor(config = {}) {
        this.detector = new MarketRegimeDetector();
        this.lookback = config.lookback || 20;
        this.volatilityThreshold = config.volatilityThreshold || 0.025;
        this.trendThreshold = config.trendThreshold || 0.02;
    }

    feed(prices, volumes) {
        if (prices.length < this.lookback) return this.detector.getState();

        const returns = [];
        for (let i = 1; i < prices.length; i++) {
            returns.push((prices[i] - prices[i-1]) / prices[i-1]);
        }

        const avgReturn = returns.reduce((a, b) => a + b, 0) / returns.length;
        const variance = returns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) / returns.length;
        const volatility = Math.sqrt(variance);
        const trend = avgReturn * 100;
        const vix = volatility * 100;

        const advancers = returns.filter(r => r > 0).length;
        const breadth = returns.length > 0 ? advancers / returns.length : 0.5;
        const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;
        const volumeSpike = avgVolume > 0 ? volumes[volumes.length - 1] / avgVolume : 1;

        const newState = this.detector.detect(vix, trend, breadth, volumeSpike);

        if (newState !== this.detector.getState()) {
            eventBus.emit('REGIME_CHANGE', {
                from: this.detector.sm.history[this.detector.sm.history.length - 2]?.to || 'UNKNOWN',
                to: newState,
                vix, trend, breadth, volumeSpike,
            });
            logger.info(`[REGIME] ${newState} | vix=${vix.toFixed(2)} trend=${trend.toFixed(2)}%`);
        }

        return newState;
    }

    getState() { return this.detector.getState(); }
    getHistory() { return this.detector.getHistory(); }
}

module.exports = RegimeDetector;
