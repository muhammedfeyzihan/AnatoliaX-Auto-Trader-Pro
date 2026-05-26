// ============================================================
// risk_engine.js - Real-Time Risk Engine (K128)
// Her islem oncesi risk hesaplamasi.
// VaR, Kelly, Max Drawdown, Korelasyon, Portfoy riski.
// ============================================================

const logger = require('../core/logger');
const eventBus = require('../core/event_bus');
const StateManager = require('../core/state_manager');

class RiskEngine {
    constructor(config) {
        this.config = config || {};
        this.state = new StateManager('risk');
        this.positions = this.state.get('positions', []);
        this.history = this.state.get('history', []);
        this.maxDailyLoss = this.config.maxDailyLoss || 0.03;
        this.maxPositionPerStock = this.config.maxPositionPerStock || 0.02;
        this.maxOpenPositions = this.config.maxOpenPositions || 5;
        this.minRR = this.config.minRR || 2.0;
        this.maxCorrelation = this.config.maxCorrelation || 0.80;
        this.todayLoss = 0;

        eventBus.on('ORDER_PLACED', (data) => this._onOrderPlaced(data));
        eventBus.on('POSITION_CLOSED', (data) => this._onPositionClosed(data));
    }

    validateOrder(order) {
        const checks = {
            dailyLoss: this._checkDailyLoss(order),
            positionSize: this._checkPositionSize(order),
            maxPositions: this._checkMaxPositions(order),
            rr: this._checkRR(order),
            correlation: this._checkCorrelation(order),
            sector: this._checkSectorLimit(order),
        };
        const passed = Object.values(checks).every(c => c.pass);
        const violations = Object.entries(checks).filter(([, c]) => !c.pass).map(([k]) => k);

        if (!passed) {
            logger.warn(`[RISK] RED: ${violations.join(', ')}`, { order });
            eventBus.emit('RISK_VIOLATION', { order, violations, checks });
        }

        return { passed, checks, violations };
    }

    _checkDailyLoss(order) {
        const projectedLoss = order.qty * (order.price - order.stopLoss);
        const portfolioValue = this._getPortfolioValue();
        const lossPct = portfolioValue > 0 ? projectedLoss / portfolioValue : 0;
        const totalLoss = this.todayLoss + lossPct;
        const pass = totalLoss <= this.maxDailyLoss;
        return { pass, value: totalLoss, limit: this.maxDailyLoss };
    }

    _checkPositionSize(order) {
        const portfolioValue = this._getPortfolioValue();
        const posValue = order.qty * order.price;
        const pct = portfolioValue > 0 ? posValue / portfolioValue : 0;
        return { pass: pct <= this.maxPositionPerStock, value: pct, limit: this.maxPositionPerStock };
    }

    _checkMaxPositions(order) {
        const openCount = this.positions.filter(p => p.status === 'OPEN').length;
        const newCount = openCount + 1;
        return { pass: newCount <= this.maxOpenPositions, value: newCount, limit: this.maxOpenPositions };
    }

    _checkRR(order) {
        if (!order.takeProfit || !order.stopLoss || !order.price) return { pass: false, value: 0, limit: this.minRR };
        const risk = order.price - order.stopLoss;
        const reward = order.takeProfit - order.price;
        const rr = risk > 0 ? reward / risk : 0;
        return { pass: rr >= this.minRR, value: rr, limit: this.minRR };
    }

    _checkCorrelation(order) {
        const sameSector = this.positions.filter(p => p.sector === order.sector);
        const pass = sameSector.length < 2;
        return { pass, value: sameSector.length, limit: 2 };
    }

    _checkSectorLimit(order) {
        const sectorCount = new Set(this.positions.map(p => p.sector)).size;
        return { pass: sectorCount <= 5, value: sectorCount, limit: 5 };
    }

    calculateVaR(returns, confidence = 0.95) {
        const sorted = [...returns].sort((a, b) => a - b);
        const index = Math.floor((1 - confidence) * sorted.length);
        return sorted[index] || 0;
    }

    calculateKelly(winRate, avgWin, avgLoss) {
        const b = avgWin / avgLoss;
        const f = (winRate * b - (1 - winRate)) / b;
        return Math.max(0, Math.min(f, 0.02));
    }

    calculateExpectancy(winRate, avgWin, avgLoss) {
        return (winRate * avgWin) - ((1 - winRate) * avgLoss);
    }

    calculateMaxDrawdown(equityCurve) {
        let peak = equityCurve[0];
        let maxDD = 0;
        for (const val of equityCurve) {
            if (val > peak) peak = val;
            const dd = (peak - val) / peak;
            if (dd > maxDD) maxDD = dd;
        }
        return maxDD;
    }

    calculateSharpe(returns, riskFree = 0.0001) {
        const avg = returns.reduce((a, b) => a + b, 0) / returns.length;
        const variance = returns.reduce((sum, r) => sum + Math.pow(r - avg, 2), 0) / returns.length;
        const std = Math.sqrt(variance);
        return std > 0 ? (avg - riskFree) / std : 0;
    }

    _onOrderPlaced(order) {
        const validation = this.validateOrder(order);
        if (!validation.passed) return;
        this.positions.push({ ...order, status: 'OPEN', openedAt: Date.now() });
        this.state.set('positions', this.positions);
    }

    _onPositionClosed(data) {
        const pos = this.positions.find(p => p.id === data.id);
        if (pos) {
            pos.status = 'CLOSED';
            pos.closedAt = Date.now();
            pos.pnl = data.pnl;
            this.todayLoss += Math.min(0, data.pnl);
            this.history.push({ ...pos });
            this.state.set('history', this.history);
            this.state.set('positions', this.positions);
        }
    }

    _getPortfolioValue() {
        return this.state.get('portfolioValue', 100000);
    }

    getPortfolioRisk() {
        const open = this.positions.filter(p => p.status === 'OPEN');
        const totalRisk = open.reduce((sum, p) => {
            const riskPerShare = p.price - (p.stopLoss || p.price * 0.97);
            return sum + (p.qty * riskPerShare);
        }, 0);
        const portfolioValue = this._getPortfolioValue();
        return portfolioValue > 0 ? totalRisk / portfolioValue : 0;
    }

    getStatus() {
        return {
            dailyLoss: this.todayLoss,
            maxDailyLoss: this.maxDailyLoss,
            openPositions: this.positions.filter(p => p.status === 'OPEN').length,
            maxOpenPositions: this.maxOpenPositions,
            portfolioRisk: this.getPortfolioRisk(),
        };
    }
}

module.exports = RiskEngine;
