// ============================================================
// risk_engine.test.js - Unit Test (K139)
// ============================================================

const RiskEngine = require('../../risk/risk_engine');

describe('RiskEngine', () => {
    let engine;

    beforeEach(() => {
        engine = new RiskEngine({
            maxDailyLoss: 0.03,
            maxPositionPerStock: 0.02,
            maxOpenPositions: 5,
            minRR: 2.0,
        });
    });

    test('valid order passes all checks', () => {
        const order = {
            symbol: 'THYAO',
            qty: 100,
            price: 150,
            stopLoss: 145,
            takeProfit: 160,
            sector: 'havacilik',
        };
        const result = engine.validateOrder(order);
        expect(result.passed).toBe(true);
        expect(result.violations).toHaveLength(0);
    });

    test('R:R < 2.0 is rejected', () => {
        const order = {
            symbol: 'THYAO',
            qty: 100,
            price: 150,
            stopLoss: 148,
            takeProfit: 152,
            sector: 'havacilik',
        };
        const result = engine.validateOrder(order);
        expect(result.passed).toBe(false);
        expect(result.violations).toContain('rr');
    });

    test('Kelly calculation', () => {
        const f = engine.calculateKelly(0.6, 4, 2);
        expect(f).toBeGreaterThan(0);
        expect(f).toBeLessThanOrEqual(0.02);
    });

    test('Sharpe ratio', () => {
        const returns = [0.01, 0.02, -0.01, 0.015, 0.005];
        const sharpe = engine.calculateSharpe(returns);
        expect(sharpe).not.toBeNaN();
    });
});
