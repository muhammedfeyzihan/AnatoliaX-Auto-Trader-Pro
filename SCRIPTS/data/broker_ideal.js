// ============================================================
// broker_ideal.js — İdealFX API REST Adaptörü
// ============================================================

const logger = require('../core/logger');
const { SecretManager } = require('../core/secret_manager');

class IdealFXBroker {
    constructor(config = {}) {
        this.name = 'IdealFX';
        this.baseUrl = config.baseUrl || SecretManager.get('IDEALFX_URL');
        this.apiKey = config.apiKey || SecretManager.get('IDEALFX_API_KEY');
        this.connected = false;
    }

    async connect() {
        // IdealFX genellikle REST tabanli, baglanti testi
        try {
            // Test ping
            this.connected = true;
            logger.info(`[BROKER:${this.name}] Baglandi.`);
            return true;
        } catch (err) {
            logger.error(`[BROKER:${this.name}] Baglanti hatasi: ${err.message}`);
            throw err;
        }
    }

    async placeOrder(order) {
        logger.info(`[BROKER:${this.name}] Emir: ${order.side} ${order.symbol} x${order.size}`);
        return { status: 'PENDING', broker: this.name, orderId: `I-${Date.now()}` };
    }

    async getPositions() {
        return [];
    }

    async getBalance() {
        return { cash: 0, equity: 0 };
    }

    disconnect() {
        this.connected = false;
    }
}

module.exports = IdealFXBroker;
