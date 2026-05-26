// ============================================================
// telegram_reporter.js - Telegram Rapor Formatlari (K133)
// ============================================================

const fetch = require('node-fetch');
const logger = require('../core/logger');
const secretManager = require('../core/secret_manager');

class TelegramReporter {
    constructor(config = {}) {
        this.botToken = config.botToken || secretManager.getSafe('TELEGRAM_BOT_TOKEN', '');
        this.chatId = config.chatId || secretManager.getSafe('TELEGRAM_CHAT_ID', '');
        this.enabled = !!this.botToken && !!this.chatId;
    }

    async send(text) {
        if (!this.enabled) {
            logger.warn('[TELEGRAM] Bot token veya chatId eksik');
            return null;
        }
        try {
            const encoded = encodeURIComponent(text);
            const url = `https://api.telegram.org/bot${this.botToken}/sendMessage?chat_id=${this.chatId}&text=${encoded}`;
            const res = await fetch(url, { method: 'GET', timeout: 30000 });
            const json = await res.json();
            if (!json.ok) throw new Error(json.description);
            logger.debug('[TELEGRAM] Mesaj gonderildi');
            return json;
        } catch (err) {
            logger.error(`[TELEGRAM] Gonderim hatasi: ${err.message}`);
            return null;
        }
    }

    async sendReport(type, data) {
        let text = '';
        switch (type) {
            case 'MORNING':
                text = this._morningReport(data); break;
            case 'SCALPING':
                text = this._scalpingReport(data); break;
            case 'CLOSING':
                text = this._closingReport(data); break;
            case 'HEALTH':
                text = this._healthReport(data); break;
            default:
                text = JSON.stringify(data, null, 2);
        }
        return this.send(text);
    }

    _morningReport(data) {
        const stocks = data.stocks || [];
        const lines = stocks.map(s => `${s.symbol} | ${s.price.toFixed(2)} | ${s.change >= 0 ? '+' : ''}${s.change.toFixed(2)}%`).join('\n');
        return `🏛️ SABAH RAPORU\nBIST 100: ${data.index || 'N/A'}\n\n📈 Hisseler:\n${lines}\n\n📋 ${data.decision || 'Beklemede'}`;
    }

    _scalpingReport(data) {
        return `⚡ SCALPING RAPORU\nIslem: ${data.trades || 0}\nKar: ${data.profit || 0}%\nWin Rate: ${data.winRate || 0}%`;
    }

    _closingReport(data) {
        return `🕐 KAPANIS RAPORU\nBIST 100: ${data.index || 'N/A'}\nAcik Pozisyon: ${data.openPositions || 0}\nGunluk K/Z: ${data.dailyPnL || 0}%`;
    }

    _healthReport(data) {
        const results = data.results || [];
        const lines = results.map(r => `${r.name}: ${r.status}`).join('\n');
        return `💊 SAGLIK RAPORU\n${lines}`;
    }
}

module.exports = TelegramReporter;
