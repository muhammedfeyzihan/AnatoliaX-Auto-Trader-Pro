// AnatoliaX - biquote.io SignalR Gercek Zamanli Veri Akisi
// Ucretsiz, auth gerektirmez, @microsoft/signalr kullanir
// Calistirma: node biquote_signalr.js

const signalR = require('@microsoft/signalr');
const fs = require('fs');
const path = require('path');

const HUB_URL = 'https://biquote.io/hubs/tick';
const LOG_FILE = 'C:\\Users\\feyzi\\.openclaw\\scripts\\signalr_ticks.log';
const ALERT_LOG = 'C:\\Users\\feyzi\\.openclaw\\scripts\\signalr_alerts.log';

// Log fonksiyonu
function log(msg, type = 'info') {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] [${type.toUpperCase()}] ${msg}\n`;
    console.log(line.trim());
    fs.appendFileSync(LOG_FILE, line, 'utf8');
}

function alertLog(msg) {
    const timestamp = new Date().toISOString();
    const line = `[${timestamp}] 🚨 ALERT: ${msg}\n`;
    console.log(line.trim());
    fs.appendFileSync(ALERT_LOG, line, 'utf8');
}

// Webhook trigger (yerel)
function triggerWebhook(tick) {
    const http = require('http');
    const payload = JSON.stringify({
        symbol: tick.symbol,
        price: tick.last,
        bid: tick.bid,
        ask: tick.ask,
        volume: tick.volume,
        time: tick.time,
        alert_name: `${tick.symbol} SignalR Tick`,
        message: `Last: ${tick.last} | Bid: ${tick.bid} | Ask: ${tick.ask} | Vol: ${tick.volume}`
    });

    const options = {
        hostname: '127.0.0.1',
        port: 3001,
        path: '/tradingview',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(payload)
        }
    };

    const req = http.request(options, (res) => {
        log(`Webhook gonderildi: ${tick.symbol} (status: ${res.statusCode})`, 'webhook');
    });
    req.on('error', (e) => log(`Webhook hata: ${e.message}`, 'error'));
    req.write(payload);
    req.end();
}

// Alert kontrolu: Anlik degisim %4.5+ ise
const sonFiyatlar = {};
function kontrolAlert(tick) {
    const sym = tick.symbol;
    const last = parseFloat(tick.last);
    if (!sonFiyatlar[sym]) {
        sonFiyatlar[sym] = last;
        return;
    }
    const onceki = sonFiyatlar[sym];
    const degisim = ((last - onceki) / onceki * 100);
    if (Math.abs(degisim) >= 4.5) {
        alertLog(`${sym} | Onceki: ${onceki} | Simdi: ${last} | Degisim: %${degisim.toFixed(2)}`);
        triggerWebhook(tick);
    }
    sonFiyatlar[sym] = last;
}

// Ana baglanti
async function main() {
    log('========================================');
    log('AnatoliaX SignalR - biquote.io BASLADI');
    log(`Hub: ${HUB_URL}`);
    log('========================================');

    const connection = new signalR.HubConnectionBuilder()
        .withUrl(HUB_URL)
        .withAutomaticReconnect()
        .configureLogging(signalR.LogLevel.Warning)
        .build();

    // Baglanti eventleri
    connection.onreconnecting((error) => {
        log(`Yeniden baglaniyor... Hata: ${error ? error.message : 'Bilinmiyor'}`, 'reconnect');
    });

    connection.onreconnected((connectionId) => {
        log(`Yeniden baglandi. Connection ID: ${connectionId}`, 'reconnect');
    });

    connection.onclose((error) => {
        log(`Baglanti kapandi. Hata: ${error ? error.message : 'Bilinmiyor'}`, 'error');
        log('10 saniye sonra tekrar baglanilacak...', 'info');
        setTimeout(main, 10000);
    });

    // Tick verisi geldiginde
    connection.on('ReceiveTick', (tick) => {
        try {
            log(`${tick.symbol} | Last: ${tick.last} | Bid: ${tick.bid} | Ask: ${tick.ask} | Vol: ${tick.volume} | Time: ${tick.time}`, 'tick');
            kontrolAlert(tick);
        } catch (e) {
            log(`Tick isleme hatasi: ${e.message}`, 'error');
        }
    });

    try {
        await connection.start();
        log(`SignalR BAGLANDI! Connection ID: ${connection.connectionId}`, 'success');

        // Abone ol - BIST hisseleri
        const symbols = ['THYAO', 'GARAN', 'ISCTR', 'AKBNK', 'KCHOL', 'SAHOL', 'ASELS', 'SISE', 'EREGL', 'PETKM', 'TUPRS', 'FROTO', 'TOASO'];
        log(`${symbols.length} hisseye abone olunuyor: ${symbols.join(', ')}`, 'info');
        await connection.invoke('Subscribe', symbols);
        log('Abone olundu. Tick verisi bekleniyor...', 'success');

        // Sonsuz calis
        await new Promise(() => {});
    } catch (err) {
        log(`Baglanti hatasi: ${err.message}`, 'error');
        log('10 saniye sonra tekrar denenecek...', 'info');
        setTimeout(main, 10000);
    }
}

// Hata yakalama
process.on('uncaughtException', (err) => {
    log(`Yakalanmamis hata: ${err.message}`, 'fatal');
});

process.on('unhandledRejection', (reason) => {
    log(`Yakalanmamis promise reddi: ${reason}`, 'fatal');
});

main();
