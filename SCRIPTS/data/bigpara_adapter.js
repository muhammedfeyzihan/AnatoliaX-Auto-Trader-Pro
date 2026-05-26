// ============================================================
// bigpara_adapter.js - Bigpara Adapter (K91-K92)
// Mevcut cache_manager.js temizlenerek OOP class yapisi.
// Primary source DEGIL, secondary (15dk gecikmeli).
// ============================================================

const fetch = require('node-fetch');
const logger = require('../core/logger');
const CircuitBreaker = require('../core/circuit_breaker');
const RetryPolicy = require('../core/retry_policy');

const CACHE_DIR = require('path').join(__dirname, '..', '..', 'cache');
const CACHE_TTL = 15 * 60 * 1000;

class BigparaAdapter {
    constructor(config = {}) {
        this.baseUrl = config.bigparaBaseUrl || 'https://bigpara.hurriyet.com.tr';
        this.timeout = config.timeout || 10000;
        this.cb = new CircuitBreaker('bigpara', {
            failureThreshold: 3,
            resetTimeoutMs: 60000,
            fallback: () => null,
        });
        this.retry = new RetryPolicy({ maxAttempts: 3, baseDelayMs: 2000 });
    }

    async fetchMostActive() {
        const url = `${this.baseUrl}/borsa/en-cok-islem-gorenler/`;
        return this.cb.execute(async () => this.retry.execute(async () => {
            const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: this.timeout });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const html = await res.text();
            return this._parseTable(html);
        }));
    }

    async fetchStock(symbol) {
        const url = `${this.baseUrl}/borsa/hisse-senetleri/${symbol.toLowerCase()}-${symbol.toLowerCase()}/`;
        return this.cb.execute(async () => this.retry.execute(async () => {
            const res = await fetch(url, { headers: { 'User-Agent': 'Mozilla/5.0' }, timeout: this.timeout });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const html = await res.text();
            return this._parseStockPage(html, symbol);
        }));
    }

    _parseTable(html) {
        const stocks = [];
        const rowRe = /<tr[^>]*>[\s\S]*?<td[^>]*>([A-Z0-9]+)<\/td>[\s\S]*?<td[^>]*>([\d,.]+)<\/td>[\s\S]*?<td[^>]*>([\-+\d.,%]+)<\/td>[\s\S]*?<td[^>]*>([\d.]+)<\/td>/g;
        let m;
        while ((m = rowRe.exec(html)) !== null) {
            stocks.push({
                symbol: m[1],
                price: this._parsePrice(m[2]),
                change: this._parsePercent(m[3]),
                volume: parseInt(m[4].replace(/\./g, ''), 10),
                source: 'bigpara',
                timestamp: Date.now(),
                delay: '15dk',
            });
        }
        logger.info(`[BIGPARA] ${stocks.length} hisse cekildi`);
        return stocks;
    }

    _parseStockPage(html, symbol) {
        const priceMatch = html.match(/lastPrice[^>]*>([\d,.]+)/);
        const changeMatch = html.match(/dailyChange[^>]*>([\-+\d.,%]+)/);
        return {
            symbol,
            price: priceMatch ? this._parsePrice(priceMatch[1]) : null,
            change: changeMatch ? this._parsePercent(changeMatch[1]) : null,
            source: 'bigpara',
            timestamp: Date.now(),
            delay: '15dk',
            verified: false,
            note: 'TradingView dogrulamasi gerekli (K91)',
        };
    }

    _parsePrice(s) {
        return parseFloat(s.replace(/\./g, '').replace(',', '.'));
    }

    _parsePercent(s) {
        return parseFloat(s.replace('%', '').replace(',', '.'));
    }

    getHealth() {
        return { source: 'bigpara', status: this.cb.getStatus().state };
    }
}

module.exports = BigparaAdapter;
