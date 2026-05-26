// ============================================================
// factory.js - Factory Pattern (K122)
// Broker, adapter, strateji nesnelerinin uretimi.
// ============================================================

const logger = require('../logger');
const { StrategyFactory } = require('./strategy');
const CircuitBreaker = require('../circuit_breaker');
const RetryPolicy = require('../retry_policy');

class BrokerFactory {
    static create(type, config) {
        switch (type.toLowerCase()) {
            case 'mock': return new MockBroker(config);
            case 'abstract': return new AbstractBroker(config);
            default:
                logger.warn(`[FACTORY] Bilinmeyen broker: ${type}, abstract kullaniliyor`);
                return new AbstractBroker(config);
        }
    }
}

class AbstractBroker {
    constructor(config) {
        this.name = config.name || 'AbstractBroker';
        this.config = config;
        this.cb = new CircuitBreaker(`${this.name}-cb`, {
            failureThreshold: 3,
            resetTimeoutMs: 15000,
            fallback: () => ({ status: 'FALLBACK', message: 'Broker devre disi' }),
        });
        this.retry = new RetryPolicy({ maxAttempts: 3, baseDelayMs: 1000 });
    }

    async connect() { throw new Error('connect() implemente edilmeli'); }
    async disconnect() { throw new Error('disconnect() implemente edilmeli'); }
    async placeOrder(order) { throw new Error('placeOrder() implemente edilmeli'); }
    async cancelOrder(orderId) { throw new Error('cancelOrder() implemente edilmeli'); }
    async getPositions() { throw new Error('getPositions() implemente edilmeli'); }
    async getBalance() { throw new Error('getBalance() implemente edilmeli'); }
    async getQuote(symbol) { throw new Error('getQuote() implemente edilmeli'); }
}

class MockBroker extends AbstractBroker {
    constructor(config) {
        super({ ...config, name: 'MockBroker' });
        this.orders = [];
        this.positions = [];
        this.balance = config.balance || 100000;
    }

    async connect() { logger.info('[MOCK BROKER] Baglandi'); return true; }
    async disconnect() { logger.info('[MOCK BROKER] Kapatildi'); return true; }

    async placeOrder(order) {
        return this.cb.execute(async () => {
            const id = `MOCK-${Date.now()}`;
            this.orders.push({ id, ...order, status: 'FILLED', fillTime: Date.now() });
            if (order.side === 'BUY') this.positions.push({ id, symbol: order.symbol, qty: order.qty, entry: order.price });
            return { id, status: 'FILLED', price: order.price };
        });
    }

    async getPositions() { return this.positions; }
    async getBalance() { return this.balance; }
    async getQuote(symbol) {
        return { symbol, bid: 100, ask: 100.5, last: 100.25, volume: 1000000, time: Date.now() };
    }
}

class AdapterFactory {
    static create(type, config) {
        switch (type.toLowerCase()) {
            case 'bigpara': return new (require('../../data/bigpara_adapter'))(config);
            case 'investing': return new (require('../../data/investing_adapter'))(config);
            case 'tradingview': return new (require('../../data/tradingview_adapter'))(config);
            case 'biquote': return new (require('../../data/biquote_adapter'))(config);
            default: throw new Error(`Bilinmeyen adapter: ${type}`);
        }
    }
}

module.exports = { BrokerFactory, AbstractBroker, MockBroker, AdapterFactory, StrategyFactory };
