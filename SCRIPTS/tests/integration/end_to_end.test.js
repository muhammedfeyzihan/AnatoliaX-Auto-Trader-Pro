// ============================================================
// end_to_end.test.js - Integration Test (K139)
// ============================================================

const eventBus = require('../../core/event_bus');
const RiskEngine = require('../../risk/risk_engine');
const { StrategyFactory } = require('../../core/patterns/strategy');

describe('End-to-End Flow', () => {
    test('signal -> risk check -> decision', async () => {
        const strategy = StrategyFactory.create('SCALPING', { positionSize: 0.005, minRR: 2 });
        const stockData = {
            price: 150, ema9: 152, ema21: 148, rsi: 65,
            volume: 5000000, avgVolume: 1000000, vwap: 149,
        };
        const signal = await strategy.generateSignal(stockData);
        expect(['BUY', 'SELL', 'HOLD']).toContain(signal.action);

        const risk = new RiskEngine({ maxPositionPerStock: 0.02, minRR: 2 });
        if (signal.action === 'BUY') {
            const order = {
                symbol: 'THYAO', qty: 100, price: 150,
                stopLoss: 145, takeProfit: 160, sector: 'havacilik',
            };
            const validation = risk.validateOrder(order);
            expect(validation.checks.rr.pass).toBe(true);
        }
    });

    test('event bus delivers message', () => {
        return new Promise((resolve) => {
            eventBus.on('TEST_EVENT', (data) => {
                expect(data.msg).toBe('hello');
                resolve();
            });
            eventBus.emit('TEST_EVENT', { msg: 'hello' });
        });
    });
});
