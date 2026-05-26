// ============================================================
// broker_manager.js — Broker Secimi ve Failover
// Birincil: Matriks, Yedek: IdealFX, Son Carek: Foreks
// ============================================================

const logger = require('../core/logger');
const MatriksBroker = require('./broker_matriks');
const IdealFXBroker = require('./broker_ideal');
const ForeksBroker = require('./broker_foreks');

class BrokerManager {
    constructor(config = {}) {
        this.brokers = [
            { name: 'Matriks', instance: new MatriksBroker(config.matriks), priority: 1 },
            { name: 'IdealFX', instance: new IdealFXBroker(config.ideal), priority: 2 },
            { name: 'Foreks', instance: new ForeksBroker(config.foreks), priority: 3 },
        ];
        this.active = null;
    }

    async connect() {
        for (const b of this.brokers.sort((a, b) => a.priority - b.priority)) {
            try {
                await b.instance.connect();
                this.active = b.instance;
                logger.info(`[BROKER_MGR] Aktif broker: ${b.name}`);
                return this.active;
            } catch (err) {
                logger.warn(`[BROKER_MGR] ${b.name} baglanti basarisiz: ${err.message}`);
            }
        }
        throw new Error('[BROKER_MGR] Hicbir broker baglanamadi.');
    }

    async placeOrder(order) {
        if (!this.active) await this.connect();
        try {
            return await this.active.placeOrder(order);
        } catch (err) {
            logger.error(`[BROKER_MGR] Emir hatasi: ${err.message}. Failover deneniyor...`);
            return this._failover(order);
        }
    }

    async _failover(order) {
        const currentIndex = this.brokers.findIndex(b => b.instance === this.active);
        for (let i = currentIndex + 1; i < this.brokers.length; i++) {
            try {
                await this.brokers[i].instance.connect();
                this.active = this.brokers[i].instance;
                logger.info(`[BROKER_MGR] Failover: ${this.brokers[i].name}`);
                return await this.active.placeOrder(order);
            } catch (err) {
                logger.warn(`[BROKER_MGR] Failover ${this.brokers[i].name} basarisiz.`);
            }
        }
        throw new Error('[BROKER_MGR] Tum brokerler basarisiz. Emir iptal.');
    }

    getActive() {
        return this.active;
    }

    disconnectAll() {
        this.brokers.forEach(b => b.instance.disconnect());
        this.active = null;
    }
}

module.exports = BrokerManager;
