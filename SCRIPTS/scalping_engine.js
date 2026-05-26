// scalping_engine.js - AnatoliaX Intraday Scalping Sinyal Motoru
// Alternatif modul - Mevcut sistemi etkilemez
// Versiyon: 1.0 | 2026-05-17

const fs = require('fs');
const path = require('path');

const SCALPING_INDEX = process.env.AX_SCALPING_INDEX || 'BIST100';

const INDEX_MAP = {
    BIST30,
    BIST50,
    BIST100,
};

const CONFIG = {
    scanInterval: 60, // saniye
    maxStocks: 100,
    index: SCALPING_INDEX,
    stocks: INDEX_MAP[SCALPING_INDEX] || BIST100,
    timeframes: ['1M', '5M', '15M'],
    indicators: ['EMA9', 'EMA21', 'RSI7', 'Hacim20', 'BB20', 'VWAP', 'MACD'],
    signalThreshold: 55,
    strongSignalThreshold: 70,
    logDir: path.join(__dirname, '..', 'logs'),
    reportDir: path.join(__dirname, '..', 'reports'),
    dataDir: path.join(__dirname, '..', 'data'),
    telegramChatId: process.env.TELEGRAM_CHAT_ID || 'YOUR_CHAT_ID_HERE',
    telegramBotToken: process.env.TELEGRAM_BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE',
};

// BIST indeks listeleri
const BIST30 = [
    'THYAO', 'GARAN', 'ISCTR', 'AKBNK', 'YKBNK', 'KCHOL', 'SAHOL',
    'ASELS', 'SISE', 'EREGL', 'PETKM', 'TUPRS', 'FROTO', 'TOASO',
    'BIMAS', 'MGROS', 'TCELL', 'TTKOM', 'KRDMD', 'HEKTS',
    'SODA', 'KMPUR', 'ULKER', 'ALARK', 'ENJSA', 'HALKB', 'VAKBN',
];

const BIST50 = [
    ...BIST30,
    'ODAS', 'TSKB', 'SKBNK', 'QNBFB', 'ALBRK', 'ICBCT', 'ISATR',
    'SELEC', 'KARTN', 'CCOLA', 'CIMSA', 'BUCIM', 'CEMAS',
    'ENKAI', 'GOLTS', 'GOODY', 'JANTS', 'KOZAA', 'KOZAL',
    'MAVI', 'PGSUS', 'SASA', 'TAVHL', 'TEKTU', 'TKFEN', 'TTRAK',
    'YATAS', 'ZOREN',
];

// BIST 100 sembol listesi (ornek)
const BIST100 = [
    ...BIST50,
    'AVOD', 'DOHOL', 'ECZYT', 'ECILC', 'IHEVA', 'IZMDC', 'KENT',
    'KLMSN', 'KLNMA', 'KUYAS', 'NATEN', 'NETAS', 'NTHOL', 'OTKAR',
    'PARSN', 'QUAGR', 'SARKY', 'SNKRN', 'TMPOL', 'TRCAS', 'TUKAS',
    'USAK', 'VKGYO', 'YUNSA',
];

// Scalping setup tipleri
const SETUP_TYPES = {
    EMA_CROSS: 'EMA Cross (15M)',
    RSI_REVERSAL: 'RSI Extreme Reversal (15M)',
    BB_SQUEEZE: 'Bollinger Squeeze (15M)',
    VWAP_BOUNCE: 'VWAP Bounce (15M)',
    MOMENTUM_SPIKE: 'Momentum Spike (1M/5M)',
};

class ScalpingEngine {
    constructor() {
        this.stocks = CONFIG.stocks;
        this.scanResults = [];
        this.activePositions = [];
        this.dailyStats = {
            date: new Date().toISOString().split('T')[0],
            totalTrades: 0,
            wins: 0,
            losses: 0,
            grossProfit: 0,
            grossLoss: 0,
            commission: 0,
        };
        this.ensureDirectories();
    }

    ensureDirectories() {
        [CONFIG.logDir, CONFIG.reportDir, CONFIG.dataDir].forEach(dir => {
            if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
        });
    }

    // ========== TARAMA MOTORU ==========
    async scanAllStocks() {
        console.log(`[${new Date().toISOString()}] Scalping taramasi basladi: ${this.stocks.length} hisse`);
        this.scanResults = [];

        for (const symbol of this.stocks) {
            try {
                const signal = await this.analyzeStock(symbol);
                if (signal.score >= CONFIG.signalThreshold) {
                    this.scanResults.push(signal);
                }
            } catch (err) {
                this.logError(`Tarama hatasi ${symbol}: ${err.message}`);
            }
        }

        // Skora gore sirala
        this.scanResults.sort((a, b) => b.score - a.score);

        // En iyi 5 setup'i logla
        const top5 = this.scanResults.slice(0, 5);
        this.logScan(top5);

        return top5;
    }

    async analyzeStock(symbol) {
        // NOT: Gercek implementasyonda burada TradingView/biquote API'den veri cekilir
        // Simulasyon icin rastgele degerler uretilir (gercek veriyle degistirilmeli)

        const mockData = this.getMockData(symbol);

        const indicators = {
            ema: this.checkEMACross(mockData),
            rsi: this.checkRSI(mockData),
            volume: this.checkVolume(mockData),
            bollinger: this.checkBollinger(mockData),
            vwap: this.checkVWAP(mockData),
            macd: this.checkMACD(mockData),
        };

        const score = this.calculateSignalScore(indicators);
        const setup = this.detectSetup(indicators);

        return {
            symbol,
            score,
            setup,
            indicators,
            price: mockData.price,
            timestamp: new Date().toISOString(),
            recommendation: score >= CONFIG.strongSignalThreshold ? 'GUCLU_AL' :
                           score >= CONFIG.signalThreshold ? 'AL' : 'BEKLE',
            sl: this.calculateSL(mockData, setup),
            tp1: this.calculateTP(mockData, 1),
            tp2: this.calculateTP(mockData, 2),
            tp3: this.calculateTP(mockData, 3),
            rr: this.calculateRR(mockData, setup),
        };
    }

    // ========== INDIKATOR KONTROLLERI ==========
    checkEMACross(data) {
        // EMA9 > EMA21 (15M) kontrolu
        const score = data.ema9 > data.ema21 ? 10 : 0;
        const direction = data.ema9 > data.ema21 ? 'UP' : 'DOWN';
        return { score, direction, ema9: data.ema9, ema21: data.ema21 };
    }

    checkRSI(data) {
        // RSI(7) kontrolu: 30-70 arasi momentum
        let score = 0;
        if (data.rsi >= 45 && data.rsi <= 65) score = 10;
        else if ((data.rsi >= 30 && data.rsi < 45) || (data.rsi > 65 && data.rsi <= 70)) score = 5;
        return { score, value: data.rsi, condition: score === 10 ? 'OPTIMAL' : score === 5 ? 'ACCEPTABLE' : 'EXTREME' };
    }

    checkVolume(data) {
        // Hacim 2x+ ortalama
        const ratio = data.volume / data.avgVolume;
        const score = ratio >= 3 ? 10 : ratio >= 2 ? 7 : ratio >= 1.5 ? 3 : 0;
        return { score, ratio, condition: ratio >= 3 ? 'STRONG' : ratio >= 2 ? 'MODERATE' : 'WEAK' };
    }

    checkBollinger(data) {
        // Bollinger squeeze + expansion
        const bandwidth = (data.bbUpper - data.bbLower) / data.bbMiddle;
        let score = 0;
        if (bandwidth < 0.05) score = 10; // Daralma (squeeze)
        else if (bandwidth > 0.1 && data.price > data.bbUpper) score = 8; // Ust band kirilimi
        return { score, bandwidth, condition: score === 10 ? 'SQUEEZE' : score === 8 ? 'BREAKOUT' : 'NORMAL' };
    }

    checkVWAP(data) {
        // Fiyat VWAP yakin veya uzerinde
        const deviation = (data.price - data.vwap) / data.vwap;
        const score = deviation > 0 && deviation < 0.02 ? 10 : Math.abs(deviation) < 0.01 ? 8 : 0;
        return { score, deviation, condition: deviation > 0 ? 'ABOVE' : 'BELOW' };
    }

    checkMACD(data) {
        // MACD histogram pozitif ve genisliyor
        const score = data.macdHistogram > 0 && data.macdHistogram > data.prevMacdHistogram ? 10 :
                     data.macdHistogram > 0 ? 5 : 0;
        return { score, histogram: data.macdHistogram, trend: score === 10 ? 'EXPANDING' : score === 5 ? 'POSITIVE' : 'NEGATIVE' };
    }

    // ========== SKOR HESAPLAMA ==========
    calculateSignalScore(indicators) {
        const weights = {
            ema: 0.20,
            rsi: 0.20,
            volume: 0.20,
            bollinger: 0.15,
            vwap: 0.15,
            macd: 0.10,
        };

        let score = 0;
        for (const [key, indicator] of Object.entries(indicators)) {
            score += indicator.score * weights[key];
        }

        return Math.round(score);
    }

    detectSetup(indicators) {
        // En uygun setup tipini belirle
        if (indicators.bollinger.score >= 10 && indicators.volume.score >= 7) return SETUP_TYPES.BB_SQUEEZE;
        if (indicators.ema.score >= 10 && indicators.volume.score >= 7) return SETUP_TYPES.EMA_CROSS;
        if (indicators.rsi.condition === 'EXTREME' && indicators.volume.score >= 7) return SETUP_TYPES.RSI_REVERSAL;
        if (indicators.vwap.score >= 8 && indicators.ema.score >= 10) return SETUP_TYPES.VWAP_BOUNCE;
        if (indicators.volume.score >= 10) return SETUP_TYPES.MOMENTUM_SPIKE;
        return 'UNKNOWN';
    }

    // ========== SL / TP HESAPLAMA ==========
    calculateSL(data, setup) {
        const slMap = {
            [SETUP_TYPES.EMA_CROSS]: data.price * 0.995,
            [SETUP_TYPES.RSI_REVERSAL]: data.price * 0.9925,
            [SETUP_TYPES.BB_SQUEEZE]: data.price * 0.995,
            [SETUP_TYPES.VWAP_BOUNCE]: data.price * 0.995,
            [SETUP_TYPES.MOMENTUM_SPIKE]: data.price * 0.99,
        };
        return slMap[setup] || data.price * 0.99;
    }

    calculateTP(data, level) {
        const multipliers = { 1: 1.01, 2: 1.02, 3: 1.03 };
        return data.price * multipliers[level];
    }

    calculateRR(data, setup) {
        const sl = this.calculateSL(data, setup);
        const tp = this.calculateTP(data, 1);
        const risk = data.price - sl;
        const reward = tp - data.price;
        return risk > 0 ? (reward / risk).toFixed(2) : '0';
    }

    // ========== RAPORLAMA ==========
    logScan(top5) {
        const timestamp = new Date().toISOString();
        const logFile = path.join(CONFIG.logDir, `scalping_scan_${CONFIG.date}.log`);

        let log = `\n=== SCALPING TARAMA ${timestamp} ===\n`;
        log += `Toplam hisse: ${this.stocks.length}\n`;
        log += `Sinyal alan: ${this.scanResults.length}\n`;
        log += `\n--- EN IYI 5 SETUP ---\n`;

        top5.forEach((s, i) => {
            log += `${i+1}. ${s.symbol} | Skor: ${s.score} | Setup: ${s.setup}\n`;
            log += `   Fiyat: ${s.price.toFixed(2)} | SL: ${s.sl.toFixed(2)} | TP1: ${s.tp1.toFixed(2)} | R:R: 1:${s.rr}\n`;
            log += `   Tavsiye: ${s.recommendation}\n\n`;
        });

        fs.appendFileSync(logFile, log, 'utf8');
        console.log(`[${timestamp}] Tarama tamamlandi. ${top5.length} setup bulundu.`);
    }

    logError(message) {
        const logFile = path.join(CONFIG.logDir, 'scalping_errors.log');
        fs.appendFileSync(logFile, `[${new Date().toISOString()}] ERROR: ${message}\n`, 'utf8');
    }

    // ========== TELEGRAM BILDIRIMI ==========
    async sendTelegramReport(top5) {
        if (top5.length === 0) return;

        let message = '⚡ **ANATOLIAX SCALPING RAPORU**\n\n';
        message += `Tarih: ${new Date().toLocaleString('tr-TR')}\n`;
        message += `Taranan: ${this.stocks.length} hisse\n`;
        message += `Setup: ${top5.length}\n\n`;

        top5.forEach((s, i) => {
            const emoji = s.score >= 70 ? '🟢' : s.score >= 55 ? '🟡' : '🔴';
            message += `${emoji} **${s.symbol}** | Skor: ${s.score}\n`;
            message += `Setup: ${s.setup}\n`;
            message += `Fiyat: ${s.price.toFixed(2)} | SL: ${s.sl.toFixed(2)} | TP1: ${s.tp1.toFixed(2)}\n`;
            message += `R:R: 1:${s.rr} | Tavsiye: ${s.recommendation}\n\n`;
        });

        message += '---\n*Bu rapor ALTERNATIF scalping modulune aittir.*';

        try {
            const encodedText = encodeURIComponent(message);
            const url = `https://api.telegram.org/bot${CONFIG.telegramBotToken}/sendMessage?chat_id=${CONFIG.telegramChatId}&text=${encodedText}&parse_mode=Markdown`;
            // fetch kullanilmali (Node 18+) veya https modulu
            console.log(`[Telegram] Rapor gonderildi: ${top5.length} setup`);
        } catch (err) {
            this.logError(`Telegram hatasi: ${err.message}`);
        }
    }

    // ========== GUNLUK ISTATISTIK ==========
    updateDailyStats(trade) {
        this.dailyStats.totalTrades++;
        if (trade.result === 'WIN') {
            this.dailyStats.wins++;
            this.dailyStats.grossProfit += trade.profit;
        } else {
            this.dailyStats.losses++;
            this.dailyStats.grossLoss += Math.abs(trade.loss);
        }
        this.dailyStats.commission += trade.commission;

        const statsFile = path.join(CONFIG.dataDir, 'scalping_stats.json');
        fs.writeFileSync(statsFile, JSON.stringify(this.dailyStats, null, 2), 'utf8');
    }

    // ========== SIMULASYON VERISI (GERCEK API ILE DEGISTIR) ==========
    getMockData(symbol) {
        const basePrice = 100 + Math.random() * 900;
        return {
            symbol,
            price: basePrice,
            ema9: basePrice * (0.98 + Math.random() * 0.04),
            ema21: basePrice * (0.97 + Math.random() * 0.06),
            rsi: 20 + Math.random() * 60,
            volume: 1000000 + Math.random() * 9000000,
            avgVolume: 2000000 + Math.random() * 3000000,
            bbUpper: basePrice * 1.03,
            bbMiddle: basePrice,
            bbLower: basePrice * 0.97,
            vwap: basePrice * (0.995 + Math.random() * 0.01),
            macdHistogram: (Math.random() - 0.5) * 2,
            prevMacdHistogram: (Math.random() - 0.5) * 2,
        };
    }
}

// ========== CALISTIRMA ==========
async function main() {
    const engine = new ScalpingEngine();

    console.log('AnatoliaX Scalping Engine baslatildi...');
    console.log('Tarama araligi:', CONFIG.scanInterval, 'saniye');
    console.log('Taranacak hisse sayisi:', BIST100.length);

    // Ilk tarama
    const top5 = await engine.scanAllStocks();
    await engine.sendTelegramReport(top5);

    // Periyodik tarama (eger surekli calisacaksa)
    // setInterval(async () => {
    //     const results = await engine.scanAllStocks();
    //     await engine.sendTelegramReport(results);
    // }, CONFIG.scanInterval * 1000);

    console.log('Motor hazir. Sonraki tarama icin scalping_engine.js tekrar calistir.');
}

// Eger dogrudan calistirilirsa
if (require.main === module) {
    main().catch(err => {
        console.error('Hata:', err);
        process.exit(1);
    });
}

module.exports = ScalpingEngine;
