// ============================================================
// biquote_adapter.js - Biquote SignalR Adapter (K130)
// Mevcut biquote_signalr.js OOP + event_bus entegrasyonlu refactor.
// Tick verisi EventBus uzerinden yayilir.
// ============================================================

const signalR = require('@microsoft/signalr');
const logger = require('../core/logger');
const eventBus = require('../core/event_bus');
const StateManager = require('../core/state_manager');

class BiquoteAdapter {
    constructor(config = {}) {
        this.url = config.hubUrl || 'https://biquote.io/hubs/tick';
        this.connection = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = config.maxReconnectAttempts || 10;
        this.baseDelay = config.baseDelayMs || 1000;
        this.state = new StateManager('biquote');
        this.subscribedSymbols = new Set();
    }

    async connect() {
        this.connection = new signalR.HubConnectionBuilder()
            .withUrl(this.url)
            .withAutomaticReconnect({
                nextRetryDelayInMilliseconds: (ctx) => {
                    if (ctx.previousRetryCount >= this.maxReconnectAttempts) return null;
                    return Math.min(this.baseDelay * Math.pow(2, ctx.previousRetryCount), 30000);
                },
            })
            .configureLogging(signalR.LogLevel.Warning)
            .build();

        this.connection.on('Tick', (tick) => {
            const envelope = {
                symbol: tick.symbol,
                price: tick.last,
                bid: tick.bid,
                ask: tick.ask,
                volume: tick.volume,
                time: tick.time,
                source: 'biquote',
                timestamp: Date.now(),
            };
            eventBus.emit('TICK_RECEIVED', envelope);
            logger.trace(`[BIQUOTE] ${tick.symbol} ${tick.last}`);
        });

        this.connection.onreconnecting(() => {
            this.connected = false;
            logger.warn('[BIQUOTE] Yeniden baglaniliyor...');
        });

        this.connection.onreconnected(() => {
            this.connected = true;
            this.reconnectAttempts = 0;
            logger.info('[BIQUOTE] Yeniden baglandi');
            for (const sym of this.subscribedSymbols) {
                this.subscribe(sym).catch(() => {});
            }
        });

        this.connection.onclose((err) => {
            this.connected = false;
            logger.error(`[BIQUOTE] Kapandi: ${err?.message || 'Bilinmeyen'}`);
        });

        try {
            await this.connection.start();
            this.connected = true;
            this.reconnectAttempts = 0;
            logger.info('[BIQUOTE] Baglandi');
        } catch (err) {
            logger.error(`[BIQUOTE] Baslangic hatasi: ${err.message}`);
            throw err;
        }
    }

    async subscribe(symbol) {
        if (!this.connected) return;
        this.subscribedSymbols.add(symbol);
        try {
            await this.connection.invoke('Subscribe', symbol);
            logger.debug(`[BIQUOTE] Abone olundu: ${symbol}`);
        } catch (err) {
            logger.error(`[BIQUOTE] Abone hatasi ${symbol}: ${err.message}`);
        }
    }

    async unsubscribe(symbol) {
        if (!this.connected) return;
        this.subscribedSymbols.delete(symbol);
        try {
            await this.connection.invoke('Unsubscribe', symbol);
        } catch (err) {
            logger.error(`[BIQUOTE] Abonelik iptal hatasi ${symbol}: ${err.message}`);
        }
    }

    disconnect() {
        if (this.connection) {
            this.connection.stop();
            this.connected = false;
        }
    }

    getStatus() {
        return {
            connected: this.connected,
            url: this.url,
            subscribed: Array.from(this.subscribedSymbols),
        };
    }
}

module.exports = BiquoteAdapter;
