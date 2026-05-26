// ============================================================
// strategy.js - Strategy Pattern (K122)
// Farkli trade stratejileri (scalping, swing, position) ayni interface.
// ============================================================

class BaseStrategy {
    constructor(name, config = {}) {
        this.name = name;
        this.config = config;
        if (this.constructor === BaseStrategy) {
            throw new Error('BaseStrategy soyut sinif - dogrudan instantiate edilemez');
        }
    }

    async analyze(stockData) { throw new Error('analyze() implemente edilmeli'); }
    async generateSignal(stockData) { throw new Error('generateSignal() implemente edilmeli'); }
    calculatePositionSize(capital, risk) { throw new Error('calculatePositionSize() implemente edilmeli'); }
    getSL(entry, atr) { throw new Error('getSL() implemente edilmeli'); }
    getTP(entry, sl) { throw new Error('getTP() implemente edilmeli'); }
}

class ScalpingStrategy extends BaseStrategy {
    constructor(config) {
        super('SCALPING', config);
    }

    async analyze(stockData) {
        const { price, ema9, ema21, rsi, volume, vwap, bbUpper, bbLower } = stockData;
        const signals = [];
        if (ema9 > ema21) signals.push({ type: 'ema_cross', strength: 1 });
        if (rsi < 30) signals.push({ type: 'rsi_oversold', strength: 2 });
        if (rsi > 70) signals.push({ type: 'rsi_overbought', strength: -2 });
        if (volume > stockData.avgVolume * 2.5) signals.push({ type: 'volume_spike', strength: 1.5 });
        if (price > vwap) signals.push({ type: 'vwap_bull', strength: 1 });
        const score = signals.reduce((s, x) => s + x.strength, 0);
        return { score, signals, confidence: Math.min(Math.abs(score) / 5, 1) };
    }

    async generateSignal(stockData) {
        const analysis = await this.analyze(stockData);
        if (analysis.score >= 3 && analysis.confidence >= 0.6) {
            return { action: 'BUY', ...analysis, timestamp: Date.now() };
        }
        if (analysis.score <= -3 && analysis.confidence >= 0.6) {
            return { action: 'SELL', ...analysis, timestamp: Date.now() };
        }
        return { action: 'HOLD', ...analysis, timestamp: Date.now() };
    }

    calculatePositionSize(capital, risk) {
        const pct = this.config.positionSize || 0.005;
        return capital * pct;
    }

    getSL(entry, atr) {
        const slPct = this.config.slRange?.[0] || 0.005;
        return entry * (1 - slPct);
    }

    getTP(entry, sl) {
        const risk = entry - sl;
        return entry + (risk * (this.config.minRR || 2));
    }
}

class SwingStrategy extends BaseStrategy {
    constructor(config) {
        super('SWING', config);
    }

    async analyze(stockData) {
        const { price, ema21, ema50, rsi, macd, macdSignal } = stockData;
        const signals = [];
        if (ema21 > ema50) signals.push({ type: 'trend_up', strength: 1 });
        if (rsi > 50 && rsi < 70) signals.push({ type: 'momentum', strength: 1 });
        if (macd > macdSignal) signals.push({ type: 'macd_bull', strength: 1.5 });
        const score = signals.reduce((s, x) => s + x.strength, 0);
        return { score, signals, confidence: Math.min(Math.abs(score) / 4, 1) };
    }

    async generateSignal(stockData) {
        const a = await this.analyze(stockData);
        if (a.score >= 2.5 && a.confidence >= 0.6) return { action: 'BUY', ...a };
        if (a.score <= -2.5 && a.confidence >= 0.6) return { action: 'SELL', ...a };
        return { action: 'HOLD', ...a };
    }

    calculatePositionSize(capital, risk) {
        const kelly = risk.kelly || 0.02;
        return Math.min(capital * kelly, capital * 0.02);
    }

    getSL(entry, atr) {
        return entry - (atr * 1.5);
    }

    getTP(entry, sl) {
        const risk = entry - sl;
        return entry + (risk * 2);
    }
}

class StrategyFactory {
    static create(type, config) {
        switch (type.toUpperCase()) {
            case 'SCALPING': return new ScalpingStrategy(config);
            case 'SWING': return new SwingStrategy(config);
            default: throw new Error(`Bilinmeyen strateji: ${type}`);
        }
    }
}

module.exports = { BaseStrategy, ScalpingStrategy, SwingStrategy, StrategyFactory };
