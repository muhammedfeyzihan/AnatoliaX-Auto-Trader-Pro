// ============================================================
// macro_fetcher.js — Makro Veri Cekme Motoru (E-Makro Ajanı)
// TCMB, investing.com, doviz, altin, petrol, VIX
// ============================================================

const logger = require('../core/logger');

const ENDPOINTS = {
    tcmb: {
        faiz: 'https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Main+Menu/Interest+Rates',
        enflasyon: 'https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Enflasyon+Verileri',
    },
    investing: {
        usdtry: 'https://tr.investing.com/currencies/usd-try',
        eurtry: 'https://tr.investing.com/currencies/eur-try',
        gbptry: 'https://tr.investing.com/currencies/gbp-try',
        brent: 'https://tr.investing.com/commodities/brent-oil',
        gold: 'https://tr.investing.com/commodities/gold',
        vix: 'https://tr.investing.com/indices/volatility-s-p-500',
        sp500: 'https://tr.investing.com/indices/us-500',
        bist100: 'https://tr.investing.com/indices/ise-100',
        bistbank: 'https://tr.investing.com/indices/bank',
    },
};

class MacroFetcher {
    constructor() {
        this.cache = new Map();
    }

    /** TCMB politika faizi (son) */
    async fetchTCMBRate() {
        try {
            const resp = await fetch(ENDPOINTS.tcmb.faiz, { timeout: 15000 });
            const text = await resp.text();
            // Basit regex ile son faiz oranini cek (ornek: %50.00)
            const match = text.match(/One Week Repo Rate[\s\S]*?(\d+[\.,]\d+)%?/i) ||
                          text.match(/politika faizi[\s\S]*?(\d+[\.,]\d+)%?/i);
            const rate = match ? parseFloat(match[1].replace(',', '.')) : null;
            logger.info(`[MACRO] TCMB Faiz: %${rate}`);
            return { type: 'TCMB_RATE', value: rate, unit: '%', timestamp: Date.now() };
        } catch (err) {
            logger.error(`[MACRO] TCMB hata: ${err.message}`);
            return null;
        }
    }

    /** TCMB enflasyon (TUFe yillik) */
    async fetchInflation() {
        try {
            const resp = await fetch(ENDPOINTS.tcmb.enflasyon, { timeout: 15000 });
            const text = await resp.text();
            const match = text.match(/TÜFE[\s\S]*?(\d+[\.,]\d+)%?/i) ||
                          text.match(/enflasyon[\s\S]*?(\d+[\.,]\d+)%?/i);
            const rate = match ? parseFloat(match[1].replace(',', '.')) : null;
            logger.info(`[MACRO] TUFe: %${rate}`);
            return { type: 'INFLATION', value: rate, unit: '%', timestamp: Date.now() };
        } catch (err) {
            logger.error(`[MACRO] Enflasyon hata: ${err.message}`);
            return null;
        }
    }

    /** Investing.com sembol fiyati (scraping) */
    async fetchInvestingPrice(url, name) {
        try {
            const resp = await fetch(url, {
                headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)' },
                timeout: 15000,
            });
            const text = await resp.text();
            // data-last-price attribute'u genellikle guncel fiyati icerir
            const match = text.match(/data-last-price="([\d\.,]+)"/) ||
                          text.match(/<span[^>]*id="last_last"[^>]*>([\d\.,]+)</);
            const price = match ? parseFloat(match[1].replace(',', '')) : null;
            logger.info(`[MACRO] ${name}: ${price}`);
            return { type: name, value: price, unit: 'USD/TRY/pts', timestamp: Date.now() };
        } catch (err) {
            logger.error(`[MACRO] ${name} hata: ${err.message}`);
            return null;
        }
    }

    /** Tum makro verileri topla */
    async fetchAll() {
        logger.info('[MACRO] Tum makro veriler cekiliyor...');

        const promises = [
            this.fetchTCMBRate(),
            this.fetchInflation(),
            this.fetchInvestingPrice(ENDPOINTS.investing.usdtry, 'USDTRY'),
            this.fetchInvestingPrice(ENDPOINTS.investing.eurtry, 'EURTRY'),
            this.fetchInvestingPrice(ENDPOINTS.investing.gold, 'GOLD'),
            this.fetchInvestingPrice(ENDPOINTS.investing.brent, 'BRENT'),
            this.fetchInvestingPrice(ENDPOINTS.investing.vix, 'VIX'),
            this.fetchInvestingPrice(ENDPOINTS.investing.sp500, 'SP500'),
            this.fetchInvestingPrice(ENDPOINTS.investing.bist100, 'BIST100'),
        ];

        const results = await Promise.allSettled(promises);
        const data = results
            .filter(r => r.status === 'fulfilled' && r.value)
            .map(r => r.value);

        this.cache.set('latest', { data, timestamp: Date.now() });
        logger.info(`[MACRO] ${data.length}/9 makro verisi alindi.`);
        return data;
    }

    getLatest() {
        return this.cache.get('latest') || null;
    }
}

module.exports = new MacroFetcher();
