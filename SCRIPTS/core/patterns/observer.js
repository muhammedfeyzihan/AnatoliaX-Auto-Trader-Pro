// ============================================================
// observer.js - Observer Pattern (K122)
// Sinyal tespit edenler (subject) abonelere (observers) bildirir.
// ============================================================

const logger = require('../logger');

class Subject {
    constructor(name) {
        this.name = name;
        this.observers = new Map();
    }

    subscribe(observerId, callback, priority = 0) {
        this.observers.set(observerId, { callback, priority });
        logger.debug(`[OBSERVER] ${this.name}: ${observerId} abone oldu`);
    }

    unsubscribe(observerId) {
        this.observers.delete(observerId);
        logger.debug(`[OBSERVER] ${this.name}: ${observerId} abonelik iptal`);
    }

    notify(data) {
        const sorted = Array.from(this.observers.values())
            .sort((a, b) => b.priority - a.priority);
        for (const { callback } of sorted) {
            try {
                callback(data, this.name);
            } catch (err) {
                logger.error(`[OBSERVER] ${this.name} callback hatasi: ${err.message}`);
            }
        }
    }
}

class SignalSubject extends Subject {
    constructor() {
        super('SIGNAL');
        this._lastSignals = new Map();
    }

    emitSignal(symbol, signal) {
        const envelope = { symbol, signal, timestamp: Date.now() };
        this._lastSignals.set(symbol, envelope);
        this.notify(envelope);
    }

    getLastSignal(symbol) {
        return this._lastSignals.get(symbol) || null;
    }
}

module.exports = { Subject, SignalSubject };
