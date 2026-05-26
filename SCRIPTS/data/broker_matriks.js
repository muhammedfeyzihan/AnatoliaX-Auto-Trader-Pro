// ============================================================
// broker_matriks.js — Matriks API WebSocket/REST Adaptörü
// ============================================================

const WebSocket = require('ws');
const logger = require('../core/logger');
const { SecretManager } = require('../core/secret_manager');

class MatriksBroker {
    constructor(config = {}) {
        this.name = 'Matriks';
        this.wsUrl = config.wsUrl || SecretManager.get('MATRIKS_WS_URL');
        this.restUrl = config.restUrl || SecretManager.get('MATRIKS_REST_URL');
        this.apiKey = config.apiKey || SecretManager.get('MATRIKS_API_KEY');
        this.ws = null;
        this.connected = false;
        this.subscriptions = new Set();
        this.messageQueue = [];
    }

    async connect() {
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl, {
                headers: { 'Authorization': `Bearer ${this.apiKey}` },
            });

            this.ws.on('open', () => {
                this.connected = true;
                logger.info(`[BROKER:${this.name}] WebSocket baglandi.`);
                // Bekleyen abonelikleri gonder
                this.subscriptions.forEach(sym => this.subscribe(sym));
                resolve(true);
            });

            this.ws.on('message', (data) => this._onMessage(data));
            this.ws.on('error', (err) => {
                logger.error(`[BROKER:${this.name}] WS Hata: ${err.message}`);
                reject(err);
            });
            this.ws.on('close', () => {
                this.connected = false;
                logger.warn(`[BROKER:${this.name}] WS kapandi.`);
            });
        });
    }

    _onMessage(data) {
        try {
            const msg = JSON.parse(data);
            // Tick verisi isleme
            if (msg.type === 'tick') {
                logger.trace(`[BROKER:${this.name}] Tick: ${msg.symbol} ${msg.price}`);
            }
        } catch (err) {
            logger.warn(`[BROKER:${this.name}] Mesaj parse hatasi: ${err.message}`);
        }
    }

    subscribe(symbol) {
        this.subscriptions.add(symbol);
        if (this.connected && this.ws) {
            this.ws.send(JSON.stringify({ action: 'subscribe', symbol }));
        }
    }

    unsubscribe(symbol) {
        this.subscriptions.delete(symbol);
        if (this.connected && this.ws) {
            this.ws.send(JSON.stringify({ action: 'unsubscribe', symbol }));
        }
    }

    async placeOrder(order) {
        // REST API ile emir gonderimi (ornek)
        logger.info(`[BROKER:${this.name}] Emir: ${order.side} ${order.symbol} @ ${order.price}`);
        // Gercek implementasyonda fetch kullanilmali
        return { status: 'PENDING', broker: this.name, orderId: `M-${Date.now()}` };
    }

    async getPositions() {
        return []; // Gercek implementasyonda REST cagrısı
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.connected = false;
        }
    }
}

module.exports = MatriksBroker;
