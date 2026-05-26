// ============================================================
// audit_logger.js - Immutable Audit Log (K132)
// Her karar JSONL olarak kaydedilir. Degistirilemez, silinemez.
// K132: Her islem, her onay, her RED kayit altina alinir.
// ============================================================

const fs = require('fs');
const path = require('path');
const logger = require('../core/logger');

const AUDIT_DIR = path.join(__dirname, '..', '..', 'audit');
if (!fs.existsSync(AUDIT_DIR)) fs.mkdirSync(AUDIT_DIR, { recursive: true });

class AuditLogger {
    constructor(moduleName) {
        this.module = moduleName;
        this.file = path.join(AUDIT_DIR, `${moduleName}.audit.jsonl`);
    }

    log(event, data = {}) {
        const record = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            timestamp: Date.now(),
            isoTime: new Date().toISOString(),
            module: this.module,
            event,
            data,
            pid: process.pid,
            hash: this._hash(event + JSON.stringify(data)),
        };
        const line = JSON.stringify(record) + '\n';
        fs.appendFileSync(this.file, line, 'utf8');
        logger.debug(`[AUDIT] ${this.module} ${event}`, { id: record.id });
        return record.id;
    }

    decision(decision, reason, context = {}) {
        return this.log('DECISION', { decision, reason, ...context });
    }

    trade(trade) {
        return this.log('TRADE', trade);
    }

    approval(agent, stock, result, details) {
        return this.log('APPROVAL', { agent, stock, result, details });
    }

    violation(rule, details) {
        return this.log('VIOLATION', { rule, details });
    }

    read(filterFn = null) {
        if (!fs.existsSync(this.file)) return [];
        const lines = fs.readFileSync(this.file, 'utf8').split('\n').filter(Boolean);
        const records = lines.map(l => {
            try { return JSON.parse(l); } catch { return null; }
        }).filter(Boolean);
        return filterFn ? records.filter(filterFn) : records;
    }

    _hash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash;
        }
        return hash.toString(16);
    }
}

module.exports = AuditLogger;
