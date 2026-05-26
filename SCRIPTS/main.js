// ============================================================
// main.js - Ana Orchestrator (Event-Driven) v2.0
// Tum modulleri baslatir, event bus'u yonetir, graceful shutdown.
// Python backtest entegrasyonu, broker manager, ChromaDB.
// ============================================================

const { spawn } = require('child_process');
const config = require('./core/config');
const logger = require('./core/logger');
const eventBus = require('./core/event_bus');
const StateManager = require('./core/state_manager');
const HealthCheck = require('./monitor/health_check');
const AuditLogger = require('./monitor/audit_logger');
const RegimeDetector = require('./monitor/regime_detector');
const RiskEngine = require('./risk/risk_engine');
const { StrategyFactory } = require('./core/patterns/strategy');
const BrokerManager = require('./data/broker_manager');
const FeedAggregator = require('./data/feed_aggregator');
const MacroFetcher = require('./data/macro_fetcher');
const MacroParser = require('./data/macro_parser');

class AnatoliaX {
    constructor() {
        this.state = new StateManager('main');
        this.audit = new AuditLogger('main');
        this.health = new HealthCheck(config.get('health'));
        this.regime = new RegimeDetector();
        this.risk = new RiskEngine(config.get('risk'));
        this.broker = new BrokerManager(config.get('broker'));
        this.feed = FeedAggregator;
        this.macroFetcher = MacroFetcher;
        this.macroParser = MacroParser;
        this.running = false;
        this.startTime = Date.now();
    }

    async init() {
        logger.info('[MAIN] AnatoliaX v2.0 baslatiliyor...');
        this.audit.log('STARTUP', { version: '2.0.0', config: config.dump() });

        await this._initHealthChecks();
        await this._initEventListeners();

        this.health.start();
        this.running = true;
        logger.info('[MAIN] Basladi');
        this.audit.log('STARTUP_COMPLETE', { uptime: 0 });
    }

    async _initHealthChecks() {
        this.health.register('config', async () => config.get('market.exchange') === 'BIST', false);
        this.health.register('broker', async () => {
            try { await this.broker.connect(); return true; } catch { return false; }
        }, true);
        this.health.register('risk_engine', async () => this.risk.getStatus().openPositions >= 0, false);
    }

    _initEventListeners() {
        eventBus.on('TICK_RECEIVED', (data) => this._onTick(data));
        eventBus.on('SIGNAL_GENERATED', (data) => this._onSignal(data));
        eventBus.on('ORDER_PLACED', (data) => this._onOrder(data));
        eventBus.on('RISK_VIOLATION', (data) => {
            logger.warn(`[MAIN] Risk ihlali: ${data.violations.join(', ')}`);
            this.audit.violation('RISK', data);
        });
        eventBus.on('HEALTH_ALERT', (data) => {
            logger.error(`[MAIN] Saglik alert: ${data.name}`);
            this.audit.log('HEALTH_ALERT', data);
        });
        eventBus.on('REGIME_CHANGE', (data) => {
            logger.info(`[MAIN] Rejim degisikligi: ${data.from} -> ${data.to}`);
            this.audit.log('REGIME_CHANGE', data);
        });
    }

    async _onTick(data) {
        logger.trace(`[MAIN] Tick: ${data.symbol} ${data.price}`);
        // Feed aggregator cache guncelleme
        this.feed.cache.set(data.symbol, { price: data.price, timestamp: Date.now(), source: data.source });
    }

    async _onSignal(signal) {
        logger.info(`[MAIN] Sinyal: ${signal.action} ${signal.symbol}`);
        const validation = this.risk.validateOrder(signal);
        if (!validation.passed) {
            logger.warn(`[MAIN] Sinyal RED: ${validation.violations.join(', ')}`);
            return;
        }
        this.audit.decision('SIGNAL_ACCEPTED', 'Risk OK', signal);

        // Broker emir gonderimi
        try {
            const orderResult = await this.broker.placeOrder({
                symbol: signal.symbol,
                side: signal.action === 'BUY' ? 'BUY' : 'SELL',
                size: signal.size || 0,
                price: signal.price,
                type: 'MARKET',
            });
            logger.info(`[MAIN] Broker emir: ${orderResult.orderId} @ ${orderResult.broker}`);
        } catch (err) {
            logger.error(`[MAIN] Broker emir hatasi: ${err.message}`);
        }
    }

    async _onOrder(order) {
        logger.info(`[MAIN] Islem: ${order.symbol} ${order.side}`);
        this.audit.trade(order);
    }

    /** Python backtest modulunu calistirir. */
    async runBacktest(csvPath, symbol = 'THYAO') {
        return new Promise((resolve, reject) => {
            const py = spawn('python3', ['PYTHON/main.py', '--backtest', csvPath, '--symbol', symbol], {
                cwd: process.cwd(),
                env: { ...process.env, PYTHONUNBUFFERED: '1' },
            });
            let output = '';
            py.stdout.on('data', (data) => { output += data.toString(); });
            py.stderr.on('data', (data) => { logger.error(`[PYTHON] ${data.toString().trim()}`); });
            py.on('close', (code) => {
                if (code === 0) {
                    logger.info('[MAIN] Python backtest tamamlandi.');
                    resolve(output);
                } else {
                    reject(new Error(`Python exit code: ${code}`));
                }
            });
        });
    }

    /** Makro verilerini ceker ve rejim tespiti yapar. */
    async updateMacro() {
        try {
            const raw = await this.macroFetcher.fetchAll();
            const parsed = this.macroParser.parse(raw);
            this.state.set('market_regime', parsed);
            eventBus.emit('REGIME_CHANGE', { from: this.regime.getState(), to: parsed.regime });
            logger.info(`[MAIN] Makro guncellendi: ${parsed.regime} (skor: ${parsed.score})`);
            return parsed;
        } catch (err) {
            logger.error(`[MAIN] Makro hatasi: ${err.message}`);
            return null;
        }
    }

    /** Python analytics calistirir. */
    async runAnalytics(csvPath) {
        return new Promise((resolve, reject) => {
            const py = spawn('python3', ['PYTHON/main.py', '--analytics', csvPath], {
                cwd: process.cwd(),
                env: { ...process.env, PYTHONUNBUFFERED: '1' },
            });
            let output = '';
            py.stdout.on('data', (data) => { output += data.toString(); });
            py.stderr.on('data', (data) => { logger.error(`[PYTHON] ${data.toString().trim()}`); });
            py.on('close', (code) => {
                if (code === 0) {
                    logger.info('[MAIN] Python analytics tamamlandi.');
                    resolve(output);
                } else {
                    reject(new Error(`Python exit code: ${code}`));
                }
            });
        });
    }

    getStatus() {
        return {
            running: this.running,
            uptime: Date.now() - this.startTime,
            health: this.health.getStatus(),
            risk: this.risk.getStatus(),
            regime: this.regime.getState(),
        };
    }

    async shutdown() {
        logger.info('[MAIN] Kapaniyor...');
        this.running = false;
        this.health.stop();
        this.broker.disconnect();
        this.audit.log('SHUTDOWN', { uptime: Date.now() - this.startTime });
        process.exit(0);
    }
}

// CLI
async function main() {
    const app = new AnatoliaX();
    process.on('SIGINT', () => app.shutdown());
    process.on('SIGTERM', () => app.shutdown());
    await app.init();

    if (process.argv.includes('--health')) {
        console.log(JSON.stringify(app.getStatus(), null, 2));
        process.exit(0);
    }

    if (process.argv.includes('--dry-run')) {
        logger.info('[MAIN] Dry-run tamamlandi');
        await app.shutdown();
    }
}

if (require.main === module) {
    main().catch(err => {
        logger.fatal(`[MAIN] Baslatma hatasi: ${err.message}`);
        process.exit(1);
    });
}

module.exports = AnatoliaX;
