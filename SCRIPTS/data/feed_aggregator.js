// ============================================================
// feed_aggregator.js — AnatoliaX Veri Birleştirme Motoru (K91-K92)
// TradingView birincil, Bigpara ikincil, biquote yardimci.
// Uyuşmazlik varsa TradingView baz alinir.
// ============================================================

const { SecretManager } = require('../core/secret_manager');
const logger = require('../core/logger');

class FeedAggregator {
    constructor() {
        this.sources = {
            tradingview: { adapter: require('./tradingview_adapter'), weight: 0.99, delay: 0 },
            bigpara: { adapter: require('./bigpara_adapter'), weight: 0.85, delay: 900 },
            biquote: { adapter: require('./biquote_adapter'), weight: 0.90, delay: 0 },
        };
        this.cache = new Map(); // symbol -> { price, source, timestamp }
        this.qualityValidator = require('./quality_validator');
    }

    /**
     * Hisse icin tum kaynaklardan fiyat cek, dogrula, birlestir.
     * @param {string} symbol — BIST sembolu (ornek: THYAO)
     * @returns {Promise<{price:number, source:string, timestamp:number, confidence:number}>}
     */
    async fetch(symbol) {
        logger.info(`[FEED] ${symbol} veri cekiliyor...`);

        const results = [];
        for (const [name, cfg] of Object.entries(this.sources)) {
            try {
                const data = await cfg.adapter.fetch(symbol);
                if (data && data.price) {
                    results.push({
                        source: name,
                        price: parseFloat(data.price),
                        timestamp: data.timestamp || Date.now(),
                        weight: cfg.weight,
                        delay: cfg.delay,
                    });
                }
            } catch (err) {
                logger.warn(`[FEED] ${name} hatasi (${symbol}): ${err.message}`);
            }
        }

        if (results.length === 0) {
            throw new Error(`[FEED] ${symbol} icin HICBIR kaynaktan veri alinamadi (RED)`);
        }

        // Kalite dogrulama
        const validated = this.qualityValidator.validate(symbol, results);
        if (!validated.passed) {
            logger.error(`[FEED] ${symbol} kalite RED: ${validated.reason}`);
            throw new Error(`[FEED] ${symbol} kalite RED: ${validated.reason}`);
        }

        // Birincil kaynak TradingView — eger varsa onu baz al
        const tv = results.find(r => r.source === 'tradingview');
        const selected = tv || results.reduce((best, cur) => (cur.weight > best.weight ? cur : best));

        this.cache.set(symbol, selected);

        logger.info(
            `[FEED] ${symbol} OK | Fiyat: ${selected.price} | Kaynak: ${selected.source} | Guven: ${selected.weight}`
        );

        return {
            price: selected.price,
            source: selected.source,
            timestamp: selected.timestamp,
            confidence: selected.weight,
            alternatives: results.map(r => ({ source: r.source, price: r.price })),
        };
    }

    /** Toplu hisse cekme (BIST 30/50/100) */
    async fetchBatch(symbols) {
        const promises = symbols.map(s => this.fetch(s).catch(err => ({ symbol: s, error: err.message })));
        const results = await Promise.allSettled(promises);
        return results.map(r => (r.status === 'fulfilled' ? r.value : r.reason));
    }

    /** Cache temizleme */
    clearCache() {
        this.cache.clear();
        logger.info('[FEED] Cache temizlendi');
    }
}

module.exports = new FeedAggregator();
