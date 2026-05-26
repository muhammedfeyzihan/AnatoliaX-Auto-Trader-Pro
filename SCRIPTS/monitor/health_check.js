// ============================================================
// health_check.js - Sistem Saglik Kontrolu (K133)
// Tum modullerin durumunu kontrol eder. Telegram'a alert gonderir.
// ============================================================

const logger = require('../core/logger');
const eventBus = require('../core/event_bus');

class HealthCheck {
    constructor(config = {}) {
        this.checks = new Map();
        this.alertThreshold = config.alertThreshold || 3;
        this.intervalMs = config.checkIntervalMs || 60000;
        this.failures = new Map();
        this.timer = null;
    }

    register(name, checkFn, critical = true) {
        this.checks.set(name, { fn: checkFn, critical });
        this.failures.set(name, 0);
    }

    async run() {
        const results = [];
        for (const [name, { fn, critical }] of this.checks) {
            try {
                const ok = await fn();
                if (ok) {
                    this.failures.set(name, 0);
                    results.push({ name, status: 'OK', critical });
                } else {
                    const f = (this.failures.get(name) || 0) + 1;
                    this.failures.set(name, f);
                    results.push({ name, status: 'FAIL', critical, failures: f });
                    if (f >= this.alertThreshold) {
                        logger.error(`[HEALTH] ${name} ${f} kez basarisiz - ALERT`);
                        eventBus.emit('HEALTH_ALERT', { name, failures: f, critical });
                    }
                }
            } catch (err) {
                const f = (this.failures.get(name) || 0) + 1;
                this.failures.set(name, f);
                results.push({ name, status: 'ERROR', critical, error: err.message, failures: f });
                if (f >= this.alertThreshold) {
                    eventBus.emit('HEALTH_ALERT', { name, failures: f, critical, error: err.message });
                }
            }
        }
        eventBus.emit('HEALTH_CHECK', { results, timestamp: Date.now() });
        return results;
    }

    start() {
        this.timer = setInterval(() => this.run(), this.intervalMs);
        logger.info('[HEALTH] Saglik kontrolu basladi');
    }

    stop() {
        if (this.timer) { clearInterval(this.timer); this.timer = null; }
    }

    getStatus() {
        return {
            checks: Array.from(this.checks.keys()),
            failures: Object.fromEntries(this.failures),
            running: !!this.timer,
        };
    }
}

module.exports = HealthCheck;
