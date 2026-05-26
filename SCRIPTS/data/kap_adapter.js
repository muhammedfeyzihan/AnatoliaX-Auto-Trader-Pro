// ============================================================
// kap_adapter.js — KAP.gov.tr Bildirim Cekme ve Isleme
// ============================================================

const logger = require('../core/logger');

const KAP_API = 'https://www.kap.org.tr/tr/api/bildirimOzeti';

class KAPAdapter {
    constructor() {
        this.cache = new Map();
    }

    /**
     * Son N gunluk KAP bildirimlerini cek.
     * @param {number} days — Varsayilan 1 gun
     * @returns {Promise<Array<{ticker:string, date:string, title:string, type:string, url:string}>>}
     */
    async fetchAnnouncements(days = 1) {
        try {
            logger.info(`[KAP] Son ${days} gunluk bildirimler cekiliyor...`);

            // KAP API'si icin ornek istek (gercek endpoint'e gore guncellenmeli)
            const resp = await fetch(`${KAP_API}?gun=${days}`, {
                headers: {
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                },
                timeout: 15000,
            });

            if (!resp.ok) {
                throw new Error(`HTTP ${resp.status}`);
            }

            const data = await resp.json();
            const announcements = this.parseAnnouncements(data);

            logger.info(`[KAP] ${announcements.length} bildirim alindi.`);
            return announcements;
        } catch (err) {
            logger.error(`[KAP] Hata: ${err.message}`);
            return [];
        }
    }

    parseAnnouncements(raw) {
        if (!Array.isArray(raw)) return [];
        return raw.map(item => ({
            ticker: item.ticker || item.code || item.sirket || 'UNKNOWN',
            date: item.disclosureDate || item.tarih || new Date().toISOString(),
            title: item.title || item.baslik || 'Bilinmeyen Bildirim',
            type: this.classifyType(item.title || item.baslik || ''),
            url: item.disclosureIndex || item.link || '',
        }));
    }

    /** Bildirim basligina gore tip siniflandirma */
    classifyType(title) {
        const lower = title.toLowerCase();
        if (lower.includes('temettü') || lower.includes('kar payı')) return 'TEMETTU';
        if (lower.includes('sermaye') || lower.includes('bedelsiz') || lower.includes('bedelli')) return 'SERMAYE';
        if (lower.includes('yönetim kurulu') || lower.includes('genel kurul')) return 'YONETIM';
        if (lower.includes('finansal tablo') || lower.includes('bilanço')) return 'FINANSAL';
        if (lower.includes('esas sözleşme') || lower.includes('tadil')) return 'SOZLESME';
        if (lower.includes('ilişkili taraf') || lower.includes('bagli ortaklik')) return 'ILISKILI';
        return 'DIGER';
    }

    /** Belirli bir hissenin bildirimlerini cek */
    async fetchByTicker(ticker, days = 7) {
        const all = await this.fetchAnnouncements(days);
        return all.filter(a => a.ticker === ticker.toUpperCase());
    }

    /** KAP bildirimi ile fiyat hareketi korelasyonu (temel veri) */
    async fetchForCorrelation(days = 30) {
        const announcements = await this.fetchAnnouncements(days);
        return announcements;
    }
}

module.exports = new KAPAdapter();
