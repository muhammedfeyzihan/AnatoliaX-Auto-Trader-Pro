// ============================================================
// backtest_engine.js - Deterministik Backtest Engine
// ============================================================

const logger = require('../core/logger');
const RiskEngine = require('../risk/risk_engine');
const LatencySimulator = require('./latency_simulator');
const SlippageModel = require('./slippage_model');

class BacktestEngine {
    constructor(config = {}) {
        this.config = config;
        this.initialCapital = config.initialCapital || 100000;
        this.commission = config.commission || 0.003;
        this.capital = this.initialCapital;
        this.positions = [];
        this.trades = [];
        this.equityCurve = [this.initialCapital];
        this.latency = new LatencySimulator(config.latency);
        this.slippage = new SlippageModel(config.slippage);
        this.risk = new RiskEngine(config.risk);
    }

    async run(strategy, data) {
        logger.info(`[BACKTEST] Basladi | Veri: ${data.length} bar`);
        for (let i = 0; i < data.length; i++) {
            const bar = data[i];
            const signal = await strategy.generateSignal(bar);
            if (signal.action === 'BUY') {
                await this._openPosition(bar, signal);
            }
            this._updatePositions(bar);
            this.equityCurve.push(this._calculateEquity(bar));
        }
        const report = this._generateReport();
        logger.info(`[BACKTEST] Bitti | Kar: ${report.totalReturn.toFixed(2)}%`);
        return report;
    }

    async _openPosition(bar, signal) {
        const latency = await this.latency.simulate();
        const slip = this.slippage.applyToPrice(bar.price, 100, bar.avgVolume || 1000000, 'BUY');
        const entryPrice = slip.executedPrice;
        const qty = Math.floor(this.capital * 0.02 / entryPrice);
        const cost = qty * entryPrice * (1 + this.commission);
        if (cost > this.capital) return;
        this.positions.push({
            symbol: bar.symbol,
            qty,
            entry: entryPrice,
            sl: signal.sl || entryPrice * 0.97,
            tp: signal.tp || entryPrice * 1.05,
            openedAt: bar.timestamp,
        });
        this.capital -= cost;
    }

    _updatePositions(bar) {
        for (const pos of this.positions) {
            if (bar.price >= pos.tp) this._closePosition(pos, bar, 'TP');
            else if (bar.price <= pos.sl) this._closePosition(pos, bar, 'SL');
        }
    }

    _closePosition(pos, bar, reason) {
        const exitPrice = reason === 'TP' ? pos.tp : pos.sl;
        const slip = this.slippage.applyToPrice(exitPrice, pos.qty, bar.avgVolume || 1000000, 'SELL');
        const revenue = pos.qty * slip.executedPrice * (1 - this.commission);
        const pnl = revenue - (pos.qty * pos.entry);
        this.trades.push({
            symbol: pos.symbol,
            entry: pos.entry,
            exit: slip.executedPrice,
            qty: pos.qty,
            pnl,
            pnlPct: (pnl / (pos.qty * pos.entry)) * 100,
            reason,
            duration: bar.timestamp - pos.openedAt,
        });
        this.capital += revenue;
        this.positions = this.positions.filter(p => p !== pos);
    }

    _calculateEquity(bar) {
        const posValue = this.positions.reduce((sum, p) => sum + p.qty * bar.price, 0);
        return this.capital + posValue;
    }

    _generateReport() {
        const wins = this.trades.filter(t => t.pnl > 0);
        const losses = this.trades.filter(t => t.pnl <= 0);
        const winRate = this.trades.length > 0 ? wins.length / this.trades.length : 0;
        const avgWin = wins.length > 0 ? wins.reduce((s, t) => s + t.pnlPct, 0) / wins.length : 0;
        const avgLoss = losses.length > 0 ? losses.reduce((s, t) => s + Math.abs(t.pnlPct), 0) / losses.length : 0;
        const profitFactor = losses.reduce((s, t) => s + Math.abs(t.pnl), 0) > 0
            ? wins.reduce((s, t) => s + t.pnl, 0) / losses.reduce((s, t) => s + Math.abs(t.pnl), 0)
            : Infinity;
        const maxDD = this.risk.calculateMaxDrawdown(this.equityCurve);
        const totalReturn = ((this.equityCurve[this.equityCurve.length - 1] - this.initialCapital) / this.initialCapital) * 100;

        return {
            totalReturn,
            winRate,
            profitFactor,
            maxDrawdown: maxDD * 100,
            avgWin,
            avgLoss,
            totalTrades: this.trades.length,
            expectancy: (winRate * avgWin) - ((1 - winRate) * avgLoss),
            sharpe: this.risk.calculateSharpe(this.equityCurve.map((v, i) => i > 0 ? (v - this.equityCurve[i-1]) / this.equityCurve[i-1] : 0).slice(1)),
            equityCurve: this.equityCurve,
        };
    }
}

module.exports = BacktestEngine;
