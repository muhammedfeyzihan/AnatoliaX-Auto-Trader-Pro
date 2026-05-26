// ============================================================
// logger.js - Structured Logging (K125)
// Pino benzeri JSON structured log. Seviyeler: fatal, error, warn, info, debug, trace
// Dosyaya yazma + console. Rotation yoktur (harici tool onerilir: logrotate)
// ============================================================

const fs = require('fs');
const path = require('path');
const config = require('./config');

const LOG_DIR = config.get('logging.dir') || path.join(__dirname, '..', '..', 'logs');
const LOG_LEVEL = config.get('logging.level') || 'info';
const LEVELS = { fatal: 0, error: 1, warn: 2, info: 3, debug: 4, trace: 5 };

if (!fs.existsSync(LOG_DIR)) fs.mkdirSync(LOG_DIR, { recursive: true });

function now() { return new Date().toISOString(); }

function writeLog(level, msg, meta = {}) {
    if (LEVELS[level] > LEVELS[LOG_LEVEL]) return;
    const entry = {
        time: now(),
        level,
        msg,
        pid: process.pid,
        ...meta,
    };
    const line = JSON.stringify(entry) + '\n';
    fs.appendFileSync(path.join(LOG_DIR, `${level}.log`), line, 'utf8');
    if (level === 'error' || level === 'fatal') {
        fs.appendFileSync(path.join(LOG_DIR, 'combined.log'), line, 'utf8');
    }
    // Console output for dev
    if (process.env.NODE_ENV !== 'production') {
        const color = {
            fatal: '\x1b[35m', error: '\x1b[31m', warn: '\x1b[33m',
            info: '\x1b[32m', debug: '\x1b[34m', trace: '\x1b[37m',
        }[level] || '';
        console.log(`${color}[${entry.time}] ${level.toUpperCase()}: ${msg}\x1b[0m`);
    }
}

class Logger {
    child(meta) { return new Logger(meta); }
    constructor(defaultMeta = {}) { this.meta = defaultMeta; }

    fatal(msg, meta) { writeLog('fatal', msg, { ...this.meta, ...meta }); }
    error(msg, meta) { writeLog('error', msg, { ...this.meta, ...meta }); }
    warn(msg, meta)  { writeLog('warn',  msg, { ...this.meta, ...meta }); }
    info(msg, meta)  { writeLog('info',  msg, { ...this.meta, ...meta }); }
    debug(msg, meta) { writeLog('debug', msg, { ...this.meta, ...meta }); }
    trace(msg, meta) { writeLog('trace', msg, { ...this.meta, ...meta }); }
}

module.exports = new Logger();
