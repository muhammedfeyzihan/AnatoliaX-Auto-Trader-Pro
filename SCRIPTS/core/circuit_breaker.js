// ============================================================
// circuit_breaker.js - Fail-Safe Circuit Breaker (K126)
// Hata orani esigi gecerse devre acilir, fallback calisir.
// Durumlar: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
// ============================================================

const logger = require('./logger');

class CircuitBreaker {
    constructor(name, options = {}) {
        this.name = name;
        this.failureThreshold = options.failureThreshold || 5;
        this.resetTimeoutMs = options.resetTimeoutMs || 30000;
        this.halfOpenMaxCalls = options.halfOpenMaxCalls || 3;
        this.state = 'CLOSED'; // CLOSED | OPEN | HALF_OPEN
        this.failures = 0;
        this.successes = 0;
        this.lastFailureTime = null;
        this.halfOpenCalls = 0;
        this.fallback = options.fallback || null;
        this.onStateChange = options.onStateChange || (() => {});
    }

    async execute(fn, ...args) {
        if (this.state === 'OPEN') {
            if (Date.now() - this.lastFailureTime >= this.resetTimeoutMs) {
                this._transition('HALF_OPEN');
                this.halfOpenCalls = 0;
                this.successes = 0;
            } else {
                logger.warn(`[CB] ${this.name} OPEN - fallback calistiriliyor`);
                return this._fallback(...args);
            }
        }

        if (this.state === 'HALF_OPEN' && this.halfOpenCalls >= this.halfOpenMaxCalls) {
            logger.warn(`[CB] ${this.name} HALF_OPEN limit asildi - fallback`);
            return this._fallback(...args);
        }

        if (this.state === 'HALF_OPEN') this.halfOpenCalls++;

        try {
            const result = await fn(...args);
            this._onSuccess();
            return result;
        } catch (err) {
            this._onFailure();
            return this._fallback(...args);
        }
    }

    _onSuccess() {
        if (this.state === 'HALF_OPEN') {
            this.successes++;
            if (this.successes >= this.halfOpenMaxCalls) {
                this._transition('CLOSED');
                this.failures = 0;
                this.successes = 0;
                this.halfOpenCalls = 0;
            }
        } else {
            this.failures = Math.max(0, this.failures - 1);
        }
    }

    _onFailure() {
        this.failures++;
        this.lastFailureTime = Date.now();
        if (this.failures >= this.failureThreshold) {
            this._transition('OPEN');
        }
    }

    _fallback(...args) {
        if (typeof this.fallback === 'function') {
            try {
                return this.fallback(...args);
            } catch (e) {
                logger.error(`[CB] ${this.name} fallback hatasi: ${e.message}`);
                throw e;
            }
        }
        throw new Error(`[CB] ${this.name} OPEN ve fallback yok`);
    }

    _transition(newState) {
        logger.info(`[CB] ${this.name} ${this.state} -> ${newState}`);
        this.state = newState;
        this.onStateChange(newState, this.name);
    }

    getStatus() {
        return {
            name: this.name,
            state: this.state,
            failures: this.failures,
            lastFailureTime: this.lastFailureTime,
            halfOpenCalls: this.halfOpenCalls,
            successes: this.successes,
        };
    }
}

module.exports = CircuitBreaker;
