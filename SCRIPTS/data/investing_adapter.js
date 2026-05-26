// ============================================================
// investing_adapter.js - Investing.com Scraper/API (K140)
// Investing.com'dan canli veri cekme adapteri.
// WebFetch ile ana sayfa veya hisse sayfasi cekilir.
// K91: TradingView dogrulamasi oncelikli. Investing sadece ikincil.
// ============================================================

const fetch = require('node-fetch');
const logger = require('../core/logger');
const CircuitBreaker = require('../core/circuit_breaker');
const RetryPolicy = require('../core/retry_policy');

class InvestingAdapter {
    constructor(config = {}) {
        this.baseUrl = config.investingBaseUrl || 'https://www.investing.com';
        this.timeout = config.timeout || 10000;
        this.cb = new CircuitBreaker('investing', {
            failureThreshold: 3,
            resetTimeoutMs: 60000,
            fallback: () => null,
        });
        this.retry = new RetryPolicy({ maxAttempts: 3, baseDelayMs: 2000 });
    }

    async fetchEquitiesTurkey() {
        const url = `${this.baseUrl}/equities/turkey`;
        return this.cb.execute(async () => {
            return this.retry.execute(async () => {
                const res = await fetch(url, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html',
                    },
                    timeout: this.timeout,
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const html = await res.text();
                return this._parseEquitiesTable(html);
            });
        });
    }

    async fetchStock(symbol) {
        const url = `${this.baseUrl}/equities/${this._symbolToSlug(symbol)}`;
        return this.cb.execute(async () => {
            return this.retry.execute(async () => {
                const res = await fetch(url, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'text/html',
                    },
                    timeout: this.timeout,
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const html = await res.text();
                return this._parseStockPage(html, symbol);
            });
        });
    }

    _symbolToSlug(symbol) {
        return symbol.toLowerCase().replace(/[^a-z0-9]/g, '-');
    }

    _parseEquitiesTable(html) {
        const stocks = [];
        const regex = /data-symbol="([^"]+)"[^>]*>[\s\S]*?<span[^>]*>([\d,.]+)<\/span>[\s\S]*?<span[^>]*>([\-+\d.,%]+)<\/span>/g;
        let match;
        while ((match = regex.exec(html)) !== null) {
            stocks.push({
                symbol: match[1],
                price: this._parsePrice(match[2]),
                change: this._parsePercent(match[3]),
                source: 'investing.com',
                timestamp: Date.now(),
            });
        }
        logger.info(`[INVESTING] ${stocks.length} hisse cekildi`);
        return stocks;
    }

    _parseStockPage(html, symbol) {
        const priceMatch = html.match(/instrument-price-last[^>]*>([\d,.]+)/);
        const changeMatch = html.match(/instrument-price-change-percent[^>]*>([\-+\d.,%]+)/);
        return {
            symbol,
            price: priceMatch ? this._parsePrice(priceMatch[1]) : null,
            change: changeMatch ? this._parsePercent(changeMatch[1]) : null,
            source: 'investing.com',
            timestamp: Date.now(),
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
        return {
            source: 'investing.com',
            status: this.cb.getStatus().state,
            lastFailure: this.cb.getStatus().lastFailureTime,
        };
    }
}

module.exports = InvestingAdapter;
