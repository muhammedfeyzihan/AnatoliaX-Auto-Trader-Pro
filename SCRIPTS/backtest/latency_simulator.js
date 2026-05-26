// ============================================================
// latency_simulator.js - Gercekci Latency Simulasyonu (K134)
// Normal dagilimli rastgele gecikme uretir.
// ============================================================

class LatencySimulator {
    constructor(config = {}) {
        this.mean = config.meanMs || 150;
        this.stdDev = config.stdDevMs || 50;
        this.min = config.minMs || 50;
        this.max = config.maxMs || 500;
    }

    sample() {
        let u = 0, v = 0;
        while (u === 0) u = Math.random();
        while (v === 0) v = Math.random();
        const z = Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
        let latency = this.mean + this.stdDev * z;
        latency = Math.max(this.min, Math.min(this.max, latency));
        return Math.round(latency);
    }

    async simulate() {
        const delay = this.sample();
        await new Promise(r => setTimeout(r, delay));
        return delay;
    }

    distribution(samples = 1000) {
        const values = Array.from({ length: samples }, () => this.sample());
        values.sort((a, b) => a - b);
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const p50 = values[Math.floor(values.length * 0.5)];
        const p95 = values[Math.floor(values.length * 0.95)];
        const p99 = values[Math.floor(values.length * 0.99)];
        return { avg: Math.round(avg), p50, p95, p99, min: values[0], max: values[values.length - 1] };
    }
}

module.exports = LatencySimulator;
