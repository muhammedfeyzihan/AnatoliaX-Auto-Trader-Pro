// ============================================================
// portfolio_risk.js - Portfolio Risk Analysis (K128)
// ============================================================

class PortfolioRisk {
    constructor(config = {}) {
        this.maxSectorExposure = config.maxSectorExposure || 0.30;
        this.maxSingleStock = config.maxSingleStock || 0.10;
    }

    calculate(positions, prices) {
        const totalValue = positions.reduce((sum, p) => sum + p.qty * (prices[p.symbol] || p.entry), 0);
        const sectorExposure = {};
        const stockExposure = {};

        for (const pos of positions) {
            const value = pos.qty * (prices[pos.symbol] || pos.entry);
            const pct = totalValue > 0 ? value / totalValue : 0;
            stockExposure[pos.symbol] = pct;
            sectorExposure[pos.sector] = (sectorExposure[pos.sector] || 0) + pct;
        }

        const alerts = [];
        for (const [sym, pct] of Object.entries(stockExposure)) {
            if (pct > this.maxSingleStock) alerts.push({ type: 'STOCK_LIMIT', symbol: sym, pct });
        }
        for (const [sec, pct] of Object.entries(sectorExposure)) {
            if (pct > this.maxSectorExposure) alerts.push({ type: 'SECTOR_LIMIT', sector: sec, pct });
        }

        return { totalValue, sectorExposure, stockExposure, alerts, safe: alerts.length === 0 };
    }
}

module.exports = PortfolioRisk;
