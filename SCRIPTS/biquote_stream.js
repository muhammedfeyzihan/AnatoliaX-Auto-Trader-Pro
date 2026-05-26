// AnatoliaX - biquote.io BIST Canli Veri Stream
// Ucretsiz, auth gerektirmez
// Node.js 24 yerlesik WebSocket kullanir

const https = require('https');
const http = require('http');

const BASE_URL = 'biquote.io';
const LOG_FILE = 'C:\\Users\\feyzi\\.openclaw\\scripts\\biquote.log';
const fs = require('fs');

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try { fs.appendFileSync(LOG_FILE, line, 'utf8'); } catch(e) {}
  console.log(line.trim());
}

// 1. Anlik fiyat al
function getQuote(symbol) {
  return new Promise((res, rej) => {
    https.get(`https://${BASE_URL}/api/v1/quote/${symbol}`, (r) => {
      let d = '';
      r.on('data', c => d += c);
      r.on('end', () => { try { res(JSON.parse(d)); } catch(e) { res(null); } });
    }).on('error', rej);
  });
}

// 2. Webhook tetikle
function triggerWebhook(data) {
  const payload = JSON.stringify({
    symbol: data.symbol || data.Symbol,
    price: data.price || data.LastPrice,
    alert_name: `${data.symbol || data.Symbol} Momentum Alert`,
    message: `Gunluk degisim: %${data.changePercent || data.ChangePercent}, Hacim: ${data.volume || data.Volume}`
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
    log(`Webhook gonderildi: ${data.symbol || data.Symbol} (status: ${res.statusCode})`);
  });
  req.on('error', (e) => log(`Webhook hatasi: ${e.message}`));
  req.write(payload);
  req.end();
}

async function main() {
  log('========================================');
  log('AnatoliaX biquote.io Test BASLADI');
  log('========================================');

  const symbols = ['THYAO', 'GARAN', 'ISCTR', 'AKBNK', 'KCHOL'];

  for (const sym of symbols) {
    try {
      const quote = await getQuote(sym);
      if (quote) {
        log(`[SNAPSHOT] ${sym}: Fiyat=${quote.price || quote.LastPrice} | Degisim=%${quote.changePercent || quote.ChangePercent} | Hacim=${quote.volume || quote.Volume}`);

        if ((quote.changePercent || quote.ChangePercent || 0) > 4.5) {
          log(`ALERT: ${sym} %${quote.changePercent} - GAP-UP Kriteri!`);
          triggerWebhook(quote);
        }
      } else {
        log(`[SNAPSHOT] ${sym}: Veri alinamadi`);
      }
    } catch(e) {
      log(`HATA ${sym}: ${e.message}`);
    }
    await new Promise(r => setTimeout(r, 1000));
  }

  log('Test tamamlandi. WebSocket stream icin ws modulu yuklenmeli.');
  log('Kurulum: npm install -g ws');
}

main().catch(err => log(`MAIN HATA: ${err.message}`));
