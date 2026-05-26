// ============================================================
// quality_validator.js — Veri Kalite ve Tutarlilik Kontrolu (K92)
// ============================================================

const logger = require('../core/logger');

const THRESHOLDS = {
    maxAgeMs: 15 * 60 * 1000, // 15 dakika (Bigpara gecikmeli)
    maxPriceDeviation: 0.05, // %5 fark kabul edilebilir
    minSources: 1, // En az 1 kaynak zorunlu
    preferredSource: 'tradingview',
};

class QualityValidator {
    /**
     * Coklu kaynak sonucunu dogrula.
     * @returns {{passed:boolean, reason?:string}}
     */
    validate(symbol, results) {
        // 1. En az bir kaynak var mi?
        if (results.length < THRESHOLDS.minSources) {
            return { passed: false, reason: 'Yetersiz kaynak (0/1)' };
        }

        // 2. TradingView var mi? (birincil kaynak)
        const tv = results.find(r => r.source === 'tradingview');
        if (!tv) {
            logger.warn(`[QUALITY] ${symbol} TradingView yok! Bigpara/biquote ile devam.`);
        }

        // 3. Fiyat tutarliligi — kaynaklar arasi %5'ten fazla fark var mi?
        const prices = results.map(r => r.price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        const deviation = (maxPrice - minPrice) / minPrice;

        if (deviation > THRESHOLDS.maxPriceDeviation) {
            const reason = `Fiyat uyusmazligi: ${(deviation * 100).toFixed(2)}% (limit %${THRESHOLDS.maxPriceDeviation * 100})`;
            logger.error(`[QUALITY] ${symbol} ${reason}`);
            return { passed: false, reason };
        }

        // 4. Veri yas kontrolu (Bigpara haric)
        const now = Date.now();
        for (const r of results) {
            const age = now - r.timestamp;
            if (r.source !== 'bigpara' && age > THRESHOLDS.maxAgeMs) {
                logger.warn(`[QUALITY] ${symbol} ${r.source} verisi eski (${(age / 60000).toFixed(1)} dk)`);
            }
        }

        logger.info(`[QUALITY] ${symbol} OK | Kaynak: ${results.length} | Sapma: %${(deviation * 100).toFixed(2)}`);
        return { passed: true };
    }
}

module.exports = new QualityValidator();
