// ============================================================
// event_bus.js - Event-Driven Pub/Sub (K127)
// Tum moduller arasi iletisim buradan gecer.
// Loose coupling, test edilebilirlik.
// ============================================================

const EventEmitter = require('events');
const logger = require('./logger');

class EventBus extends EventEmitter {
    constructor() {
        super();
        this.setMaxListeners(100);
        this._history = [];
        this._maxHistory = 1000;
    }

    emit(event, data) {
        const envelope = {
            id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
            event,
            timestamp: Date.now(),
            data,
        };
        this._history.push(envelope);
        if (this._history.length > this._maxHistory) this._history.shift();
        logger.debug(`[EVENT] ${event}`, { eventId: envelope.id });
        super.emit(event, envelope);
        super.emit('*', envelope);
        return envelope.id;
    }

    on(event, handler) {
        const wrapped = (envelope) => {
            try {
                handler(envelope.data, envelope);
            } catch (err) {
                logger.error(`[EVENT HANDLER ERROR] ${event}: ${err.message}`, { stack: err.stack });
            }
        };
        super.on(event, wrapped);
        return () => this.off(event, wrapped);
    }

    once(event, handler) {
        const wrapped = (envelope) => {
            try {
                handler(envelope.data, envelope);
            } catch (err) {
                logger.error(`[EVENT HANDLER ERROR] ${event}: ${err.message}`, { stack: err.stack });
            }
        };
        super.once(event, wrapped);
    }

    history(filterFn) {
        return filterFn ? this._history.filter(filterFn) : [...this._history];
    }

    last(event) {
        for (let i = this._history.length - 1; i >= 0; i--) {
            if (this._history[i].event === event) return this._history[i];
        }
        return null;
    }
}

module.exports = new EventBus();
