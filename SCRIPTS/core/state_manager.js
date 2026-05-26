// ============================================================
// state_manager.js - Persistent State Recovery (K131)
// SQLite yerine JSON dosya tabanli state. Her modul kendi state'ini kaydeder.
// Auto-save periyodik. Crash sonrasi recovery.
// ============================================================

const fs = require('fs');
const path = require('path');
const logger = require('./logger');

const STATE_DIR = path.join(__dirname, '..', '..', 'state');
if (!fs.existsSync(STATE_DIR)) fs.mkdirSync(STATE_DIR, { recursive: true });

class StateManager {
    constructor(moduleName) {
        this.module = moduleName;
        this.file = path.join(STATE_DIR, `${moduleName}.state.json`);
        this.data = this._load();
        this.dirty = false;
        this.autoSaveInterval = setInterval(() => this._autoSave(), 60000);
        process.on('SIGINT', () => this.saveSync());
        process.on('SIGTERM', () => this.saveSync());
        process.on('exit', () => this.saveSync());
    }

    _load() {
        if (fs.existsSync(this.file)) {
            try {
                const raw = fs.readFileSync(this.file, 'utf8');
                const parsed = JSON.parse(raw);
                logger.info(`[STATE] ${this.module} yuklendi`, { file: this.file });
                return parsed;
            } catch (e) {
                logger.error(`[STATE] ${this.module} yukleme hatasi: ${e.message}`);
            }
        }
        return { _created: Date.now(), _version: 1, data: {} };
    }

    get(key, defaultValue) {
        return this.data.data?.[key] ?? defaultValue;
    }

    set(key, value) {
        if (!this.data.data) this.data.data = {};
        this.data.data[key] = value;
        this.data._updated = Date.now();
        this.dirty = true;
    }

    remove(key) {
        delete this.data.data[key];
        this.dirty = true;
    }

    clear() {
        this.data.data = {};
        this.dirty = true;
    }

    save() {
        if (!this.dirty) return;
        this.data._saved = Date.now();
        return new Promise((res, rej) => {
            fs.writeFile(this.file, JSON.stringify(this.data, null, 2), 'utf8', (err) => {
                if (err) { logger.error(`[STATE] ${this.module} save hatasi: ${err.message}`); rej(err); }
                else { this.dirty = false; res(); }
            });
        });
    }

    saveSync() {
        if (!this.dirty) return;
        this.data._saved = Date.now();
        try {
            fs.writeFileSync(this.file, JSON.stringify(this.data, null, 2), 'utf8');
            this.dirty = false;
        } catch (e) {
            logger.error(`[STATE] ${this.module} sync save hatasi: ${e.message}`);
        }
    }

    _autoSave() {
        if (this.dirty) this.save().catch(() => {});
    }

    snapshot() {
        return JSON.parse(JSON.stringify(this.data));
    }

    restore(snapshot) {
        this.data = JSON.parse(JSON.stringify(snapshot));
        this.dirty = true;
    }
}

module.exports = StateManager;
