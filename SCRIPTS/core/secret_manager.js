// ============================================================
// secret_manager.js - Secret Management (K137)
// Token, sifre, API key'ler asla kodda degil.
// .env dosyasi + process.env + runtime override.
// Eger .env yoksa uyar, ama process.env varsa devam et.
// ============================================================

const fs = require('fs');
const path = require('path');
const logger = require('./logger');

const ENV_PATH = path.join(__dirname, '..', '..', '.env');

class SecretManager {
    constructor() {
        this._secrets = new Map();
        this._loadEnvFile();
        this._loadProcessEnv();
    }

    _loadEnvFile() {
        if (!fs.existsSync(ENV_PATH)) {
            logger.warn(`[SECRET] .env dosyasi bulunamadi: ${ENV_PATH}`);
            return;
        }
        const lines = fs.readFileSync(ENV_PATH, 'utf8').split('\n');
        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed || trimmed.startsWith('#')) continue;
            const eq = trimmed.indexOf('=');
            if (eq === -1) continue;
            const key = trimmed.slice(0, eq).trim();
            let value = trimmed.slice(eq + 1).trim();
            if (value.startsWith('"') && value.endsWith('"')) value = value.slice(1, -1);
            if (value.startsWith("'") && value.endsWith("'")) value = value.slice(1, -1);
            if (!this._secrets.has(key)) this._secrets.set(key, value);
        }
        logger.info('[SECRET] .env dosyasi yuklendi');
    }

    _loadProcessEnv() {
        for (const [key, value] of Object.entries(process.env)) {
            this._secrets.set(key, value);
        }
    }

    get(key, fallback = null) {
        const val = this._secrets.get(key);
        if (val === undefined || val === null || val === '') {
            if (fallback !== null) return fallback;
            throw new Error(`[SECRET] ${key} bulunamadi`);
        }
        return val;
    }

    getSafe(key, fallback = null) {
        try { return this.get(key, fallback); } catch { return fallback; }
    }

    set(key, value) {
        this._secrets.set(key, value);
        process.env[key] = value;
    }

    has(key) {
        const val = this._secrets.get(key);
        return val !== undefined && val !== null && val !== '';
    }

    mask(key) {
        const val = this._secrets.get(key);
        if (!val) return '***';
        if (val.length <= 8) return '***';
        return val.slice(0, 3) + '...' + val.slice(-3);
    }

    validate(requiredKeys) {
        const missing = [];
        for (const key of requiredKeys) {
            if (!this.has(key)) missing.push(key);
        }
        if (missing.length > 0) {
            throw new Error(`[SECRET] Eksik key'ler: ${missing.join(', ')}`);
        }
        return true;
    }

    list() {
        const keys = [];
        for (const key of this._secrets.keys()) {
            keys.push({ key, value: this.mask(key) });
        }
        return keys;
    }
}

module.exports = new SecretManager();
