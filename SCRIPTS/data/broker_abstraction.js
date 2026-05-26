// ============================================================
// broker_abstraction.js - Broker Soyutlama (K129)
// Araci kurumdan bagimsiz calisir. Her broker ayni interface'i implemente eder.
// Su an icin sadece MockBroker var. Gercek broker implementasyonu sonrasi eklenecek.
// ============================================================

const { AbstractBroker, MockBroker } = require('../core/patterns/factory');

module.exports = { AbstractBroker, MockBroker };
