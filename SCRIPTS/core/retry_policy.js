// ============================================================
// retry_policy.js - Exponential Backoff Retry (K126)
// Her async islem icin retry mekanizmasi.
// Jitter eklenir (collision onleme).
// ============================================================

const logger = require('./logger');

class RetryPolicy {
    constructor(options = {}) {
        this.maxAttempts = options.maxAttempts || 5;
        this.baseDelayMs = options.baseDelayMs || 1000;
        this.maxDelayMs = options.maxDelayMs || 30000;
        this.multiplier = options.multiplier || 2;
        this.jitter = options.jitter !== false;
        this.retryableErrors = options.retryableErrors || null;
        this.onRetry = options.onRetry || null;
    }

    async execute(fn, ...args) {
        let lastError;
        for (let attempt = 1; attempt <= this.maxAttempts; attempt++) {
            try {
                return await fn(...args);
            } catch (err) {
                lastError = err;
                if (!this._isRetryable(err)) throw err;
                if (attempt === this.maxAttempts) break;
                const delay = this._calculateDelay(attempt);
                logger.warn(`[RETRY] Deneme ${attempt}/${this.maxAttempts} basarisiz. ${delay}ms bekleniyor...`, { error: err.message });
                if (this.onRetry) this.onRetry(attempt, err, delay);
                await this._sleep(delay);
            }
        }
        throw lastError;
    }

    _isRetryable(err) {
        if (!this.retryableErrors) return true;
        return this.retryableErrors.some(code =>
            err.message?.includes(code) || err.code === code || err.name === code
        );
    }

    _calculateDelay(attempt) {
        const exponential = this.baseDelayMs * Math.pow(this.multiplier, attempt - 1);
        const capped = Math.min(exponential, this.maxDelayMs);
        if (!this.jitter) return capped;
        return Math.floor(capped * (0.5 + Math.random() * 0.5));
    }

    _sleep(ms) {
        return new Promise(res => setTimeout(res, ms));
    }
}

module.exports = RetryPolicy;
