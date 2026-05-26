// ============================================================
// broker_foreks.js — Foreks API Adaptörü
// ============================================================

const logger = require('../core/logger');
const { SecretManager } = require('../core/secret_manager');

class ForeksBroker {
    constructor(config = {}) {
        this.name = 'Foreks';
        this.wsUrl = config.wsUrl || SecretManager.get('FOREKS_WS_URL');
        this.restUrl = config.restUrl || SecretManager.get('FOREKS_REST_URL');
        this.apiKey = config.apiKey || SecretManager.get('FOREKS_API_KEY');
        this.ws = null;
        this.connected = false;
    }

    async connect() {
        const WebSocket = require('ws');
        return new Promise((resolve, reject) => {
            this.ws = new WebSocket(this.wsUrl, {
                headers: { 'X-API-KEY': this.apiKey },
            });
            this.ws.on('open', () => {
                this.connected = true;
                logger.info(`[BROKER:${this.name}] Baglandi.`);
                resolve(true);
            });
            this.ws.on('error', (err) => reject(err));
            this.ws.on('close', () => { this.connected = false; });
        });
    }

    async placeOrder(order) {
        logger.info(`[BROKER:${this.name}] Emir: ${order.side} ${order.symbol}`);
        return { status: 'PENDING', broker: this.name, orderId: `F-${Date.now()}` };
    }

    async getPositions() {
        return [];
    }

    disconnect() {
        if (this.ws) { this.ws.close(); this.connected = false; }
    }
}

module.exports = ForeksBroker;
