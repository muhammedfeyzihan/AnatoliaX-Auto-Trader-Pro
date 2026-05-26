// ============================================================
// config.js - Merkezi Konfigurasyon Yonetimi (K124)
// Tum ayarlar buradan okunur. Hardcode YASAK.
// Siralama: .env > config.json > default
// ============================================================

const fs = require('fs');
const path = require('path');

const CONFIG_PATH = process.env.ANATOLIAX_CONFIG || path.join(__dirname, '..', '..', 'config.json');
const ENV_PREFIX = 'AX_';

const DEFAULTS = {
    market: {
        exchange: 'BIST',
        timezone: 'Europe/Istanbul',
        openHour: 9,
        openMinute: 30,
        closeHour: 18,
        closeMinute: 0,
    },
    risk: {
        maxPositionPerStock: 0.02,
        maxDailyLoss: 0.03,
        maxOpenPositions: 5,
        maxSectorPositions: 2,
        minRR: 2.0,
        minWinRate: 0.55,
        maxCorrelation: 0.80,
        varConfidence: 0.95,
    },
    scalping: {
        enabled: true,
        maxSimultaneous: 3,
        maxDailyTrades: 10,
        positionSize: 0.005,
        slRange: [0.005, 0.015],
        tpLevels: [0.01, 0.02, 0.03],
        maxHoldingMinutes: 15,
        dailyRiskCap: 0.02,
        commission: 0.003,
    },
    data: {
        primarySource: 'tradingview',
        secondarySource: 'bigpara',
        tertiarySource: 'investing',
        tickSource: 'biquote',
        cacheTtlMs: 15 * 60 * 1000,
        staleThresholdMs: 24 * 60 * 60 * 1000,
    },
    telegram: {
        enabled: true,
        chatId: process.env.TELEGRAM_CHAT_ID || '',
        botToken: process.env.TELEGRAM_BOT_TOKEN || '',
    },
    logging: {
        level: process.env.LOG_LEVEL || 'info',
        dir: path.join(__dirname, '..', '..', 'logs'),
        maxFiles: 30,
        maxSizeMB: 100,
    },
    audit: {
        enabled: true,
        dir: path.join(__dirname, '..', '..', 'audit'),
        retentionDays: 365,
    },
    state: {
        dir: path.join(__dirname, '..', '..', 'state'),
        autoSaveIntervalMs: 60000,
    },
    backtest: {
        defaultCapital: 100000,
        commission: 0.003,
        slippageModel: 'linear',
        latencyModel: 'normal',
    },
    websocket: {
        reconnectMaxAttempts: 10,
        reconnectBaseDelayMs: 1000,
        reconnectMaxDelayMs: 30000,
        heartbeatIntervalMs: 30000,
    },
    health: {
        checkIntervalMs: 60000,
        alertThreshold: 3,
    },
};

class Config {
    constructor() {
        this._data = this._load();
        this._validate();
    }

    _load() {
        let fileConfig = {};
        if (fs.existsSync(CONFIG_PATH)) {
            try {
                fileConfig = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
            } catch (e) {
                console.error(`[CONFIG ERROR] ${CONFIG_PATH} okunamadi: ${e.message}`);
            }
        }
        const envConfig = this._loadFromEnv();
        return this._deepMerge(DEFAULTS, fileConfig, envConfig);
    }

    _loadFromEnv() {
        const env = {};
        for (const key of Object.keys(process.env)) {
            if (key.startsWith(ENV_PREFIX)) {
                const path = key.slice(ENV_PREFIX.length).toLowerCase().split('_');
                let target = env;
                for (let i = 0; i < path.length - 1; i++) {
                    if (!target[path[i]]) target[path[i]] = {};
                    target = target[path[i]];
                }
                const last = path[path.length - 1];
                target[last] = this._parseValue(process.env[key]);
            }
        }
        return env;
    }

    _parseValue(v) {
        if (v === 'true') return true;
        if (v === 'false') return false;
        if (/^\d+$/.test(v)) return parseInt(v, 10);
        if (/^\d+\.\d+$/.test(v)) return parseFloat(v);
        try { return JSON.parse(v); } catch { }
        return v;
    }

    _deepMerge(...objs) {
        const result = {};
        for (const obj of objs) {
            for (const key of Object.keys(obj)) {
                if (typeof obj[key] === 'object' && obj[key] !== null && !Array.isArray(obj[key])) {
                    result[key] = this._deepMerge(result[key] || {}, obj[key]);
                } else {
                    result[key] = obj[key];
                }
            }
        }
        return result;
    }

    _validate() {
        const t = this._data.telegram;
        if (t.enabled && (!t.botToken || !t.chatId)) {
            console.warn('[CONFIG WARN] Telegram enabled but token/chatId missing');
        }
        if (this._data.risk.maxPositionPerStock > 0.10) {
            throw new Error('[CONFIG ERROR] maxPositionPerStock > 10% is too aggressive');
        }
    }

    get(path) {
        const keys = path.split('.');
        let val = this._data;
        for (const k of keys) {
            if (val === undefined || val === null) return undefined;
            val = val[k];
        }
        return val;
    }

    set(path, value) {
        const keys = path.split('.');
        let target = this._data;
        for (let i = 0; i < keys.length - 1; i++) {
            if (!target[keys[i]]) target[keys[i]] = {};
            target = target[keys[i]];
        }
        target[keys[keys.length - 1]] = value;
    }

    save() {
        fs.writeFileSync(CONFIG_PATH, JSON.stringify(this._data, null, 2), 'utf8');
    }

    dump() {
        return JSON.parse(JSON.stringify(this._data));
    }
}

module.exports = new Config();
