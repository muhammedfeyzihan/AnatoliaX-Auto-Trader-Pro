// ============================================================
// tradingview_adapter.js - TradingView Adapter (K91)
// Birincil veri kaynagi. Her zaman dogrulama onceligi.
// ============================================================

const fetch = require('node-fetch');
const logger = require('../core/logger');
const CircuitBreaker = require('../core/circuit_breaker');
const RetryPolicy = require('../core/retry_policy');

class TradingViewAdapter {
    constructor(config = {}) {
        this.baseUrl = config.tradingViewBaseUrl || 'https://tr.tradingview.com';
        this.timeout = config.timeout || 15000;
        this.cb = new CircuitBreaker('tradingview', {
            failureThreshold: 3,
            resetTimeoutMs: 60000,
            fallback: () => null,
        });
        this.retry = new RetryPolicy({ maxAttempts: 3, baseDelayMs: 2000 });
    }

    async fetchQuote(symbol) {
        const url = `${this.baseUrl}/symbols/BIST-${symbol}/`;
        return this.cb.execute(async () => {
            return this.retry.execute(async () => {
                const res = await fetch(url, {
                    headers: {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'text/html,application/xhtml+xml',
                    },
                    timeout: this.timeout,
                });
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                const html = await res.text();
                return this._parseQuote(html, symbol);
            });
        });
    }

    async fetchIndex(indexSymbol = 'XU100') {
        return this.fetchQuote(indexSymbol);
    }

    _parseQuote(html, symbol) {
        const priceMatch = html.match(/[\"']last[\"']\s*:\s*([\d.]+)/i) ||
                          html.match(/lastPrice[^>]*>([\d,.]+)/i) ||
                          html.match(/[<\s]([\d,.]+)\s*TRY/i);
        const changeMatch = html.match(/[\"']change[\"']\s*:\s*([\-+\d.]+)/i) ||
                            html.match(/change[^>]*>([\-+\d.,%]+)/i);
        const volumeMatch = html.match(/[\"']volume[\"']\s*:\s*([\d.]+)/i);

        const price = priceMatch ? this._parsePrice(priceMatch[1]) : null;
        const change = changeMatch ? this._parsePercent(changeMatch[1]) : null;
        const volume = volumeMatch ? parseFloat(volumeMatch[1]) : null;

        if (!price) {
            logger.warn(`[TRADINGVIEW] ${symbol} fiyat cekilemedi`);
            return null;
        }

        return {
            symbol,
            price,
            change,
            volume,
            source: 'tradingview',
            timestamp: Date.now(),
            verified: true,
            note: 'Birincil kaynak (K91)',
        };
    }

    _parsePrice(s) {
        return parseFloat(s.replace(/\./g, '').replace(',', '.'));
    }

    _parsePercent(s) {
        return parseFloat(s.replace('%', '').replace(',', '.'));
    }

    getHealth() {
        return { source: 'tradingview', status: this.cb.getStatus().state };
    }
}

module.exports = TradingViewAdapter;
