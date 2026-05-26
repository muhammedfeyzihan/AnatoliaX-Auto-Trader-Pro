// ============================================================
// circuit_breaker.test.js - Unit Test (K139)
// ============================================================

const CircuitBreaker = require('../../core/circuit_breaker');

describe('CircuitBreaker', () => {
    test('CLOSED state allows execution', async () => {
        const cb = new CircuitBreaker('test', { failureThreshold: 3 });
        const result = await cb.execute(async () => 'success');
        expect(result).toBe('success');
        expect(cb.getStatus().state).toBe('CLOSED');
    });

    test('OPEN state after threshold failures', async () => {
        const cb = new CircuitBreaker('test', { failureThreshold: 2 });
        const fail = async () => { throw new Error('fail'); };
        await expect(cb.execute(fail)).rejects.toThrow();
        await expect(cb.execute(fail)).rejects.toThrow();
        expect(cb.getStatus().state).toBe('OPEN');
    });

    test('fallback returns value on OPEN', async () => {
        const cb = new CircuitBreaker('test', {
            failureThreshold: 1,
            fallback: () => 'fallback',
        });
        await expect(cb.execute(async () => { throw new Error('fail'); })).rejects.toThrow();
        const result = await cb.execute(async () => 'should not reach');
        expect(result).toBe('fallback');
    });
});
