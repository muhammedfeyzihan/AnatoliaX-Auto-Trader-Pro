// ============================================================
// websocket_client.js - Auto-Reconnect WebSocket (K130)
// Exponential backoff + heartbeat + reconnect limit.
// SignalR veya native WS destekler.
// ============================================================

const WebSocket = require('ws');
const logger = require('../core/logger');

class ReconnectingWebSocket {
    constructor(url, options = {}) {
        this.url = url;
        this.protocols = options.protocols || [];
        this.maxAttempts = options.maxAttempts || 10;
        this.baseDelayMs = options.baseDelayMs || 1000;
        this.maxDelayMs = options.maxDelayMs || 30000;
        this.heartbeatIntervalMs = options.heartbeatIntervalMs || 30000;
        this.heartbeatMsg = options.heartbeatMsg || JSON.stringify({ type: 'ping' });
        this.reconnectDecay = options.reconnectDecay || 2;

        this.ws = null;
        this.attempts = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.ready = false;
        this._listeners = { open: [], message: [], close: [], error: [] };
        this._queue = [];

        this._connect();
    }

    _connect() {
        try {
            logger.info(`[WS] Baglaniliyor: ${this.url}`);
            this.ws = new WebSocket(this.url, this.protocols);

            this.ws.on('open', () => {
                this.attempts = 0;
                this.ready = true;
                logger.info(`[WS] Baglandi: ${this.url}`);
                this._startHeartbeat();
                this._flushQueue();
                this._emit('open');
            });

            this.ws.on('message', (data) => {
                this._emit('message', data);
            });

            this.ws.on('close', (code, reason) => {
                this.ready = false;
                this._stopHeartbeat();
                logger.warn(`[WS] Kapandi: ${code} ${reason}`);
                this._emit('close', { code, reason });
                this._scheduleReconnect();
            });

            this.ws.on('error', (err) => {
                logger.error(`[WS] Hata: ${err.message}`);
                this._emit('error', err);
            });
        } catch (err) {
            logger.error(`[WS] Baglanti hatasi: ${err.message}`);
            this._scheduleReconnect();
        }
    }

    _scheduleReconnect() {
        if (this.attempts >= this.maxAttempts) {
            logger.error(`[WS] Max deneme asildi (${this.maxAttempts}). Baglanti birakildi.`);
            return;
        }
        const delay = Math.min(this.baseDelayMs * Math.pow(this.reconnectDecay, this.attempts), this.maxDelayMs);
        this.attempts++;
        logger.info(`[WS] ${delay}ms sonra yeniden baglanilacak (deneme ${this.attempts}/${this.maxAttempts})`);
        this.reconnectTimer = setTimeout(() => this._connect(), delay);
    }

    _startHeartbeat() {
        this.heartbeatTimer = setInterval(() => {
            if (this.ready) this.send(this.heartbeatMsg);
        }, this.heartbeatIntervalMs);
    }

    _stopHeartbeat() {
        if (this.heartbeatTimer) { clearInterval(this.heartbeatTimer); this.heartbeatTimer = null; }
    }

    _flushQueue() {
        while (this._queue.length > 0 && this.ready) {
            const msg = this._queue.shift();
            this.ws.send(msg);
        }
    }

    send(data) {
        const msg = typeof data === 'string' ? data : JSON.stringify(data);
        if (this.ready) {
            this.ws.send(msg);
        } else {
            this._queue.push(msg);
        }
    }

    on(event, handler) {
        if (!this._listeners[event]) this._listeners[event] = [];
        this._listeners[event].push(handler);
    }

    _emit(event, data) {
        for (const h of this._listeners[event] || []) {
            try { h(data); } catch (e) { logger.error(`[WS] Listener hatasi: ${e.message}`); }
        }
    }

    close() {
        this._stopHeartbeat();
        if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null; }
        if (this.ws) { this.ws.close(); this.ws = null; }
        this.attempts = this.maxAttempts + 1; // Prevent reconnect
    }

    getStatus() {
        return {
            url: this.url,
            ready: this.ready,
            attempts: this.attempts,
            queueSize: this._queue.length,
        };
    }
}

module.exports = ReconnectingWebSocket;
