const http = require('http');
const { exec } = require('child_process');
const fs = require('fs');

const PORT = 3001;
const OPENCLAW = process.env.OPENCLAW_CMD || 'openclaw';
const TELEGRAM_BOT = process.env.TELEGRAM_BOT_TOKEN || 'YOUR_BOT_TOKEN_HERE';
const TELEGRAM_CHAT = process.env.TELEGRAM_CHAT_ID || 'YOUR_CHAT_ID_HERE';
const LOG_FILE = process.env.LOG_FILE || './logs/webhook.log';

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try { fs.appendFileSync(LOG_FILE, line, 'utf8'); } catch(e) {}
  console.log(line.trim());
}

function sendTelegram(text) {
  const https = require('https');
  const encoded = encodeURIComponent(text.substring(0, 4000));
  const path = `/bot${TELEGRAM_BOT}/sendMessage?chat_id=${TELEGRAM_CHAT}&text=${encoded}&parse_mode=HTML`;
  https.get(`https://api.telegram.org${path}`, (res) => {}).on('error', () => {});
}

function selectAgent(alertName, message) {
  const text = ((alertName || '') + ' ' + (message || '')).toLowerCase();
  if (text.includes('haber') || text.includes('kap')) return 'agent3';
  if (text.includes('makro') || text.includes('dolar') || text.includes('abd')) return 'agent5';
  if (text.includes('risk') || text.includes('sl') || text.includes('tp')) return 'agent4';
  if (text.includes('manip')) return 'agent6';
  if (text.includes('hesap') || text.includes('olasilik')) return 'agent8';
  return 'agent2';
}

function buildPrompt(payload) {
  const s = payload.symbol || payload.ticker || '?';
  const p = payload.price || payload.close || '?';
  const a = payload.alert_name || payload.alertName || 'Alert';
  const m = payload.message || payload.description || '';
  return `TRADINGVIEW ALERT: ${s} @ ${p}\nAlert: ${a}\nMesaj: ${m}\n\nBu hisseyi AnatoliaX konsey kurallarina gore teknik analiz et. RSI, MACD, EMA, gap-up olasiligi, risk skoru hesapla. Kisa rapor.`;
}

async function runAgent(agent, prompt) {
  return new Promise((res) => {
    const cmd = `${OPENCLAW} agent --agent ${agent} --message "${prompt.replace(/"/g, '\\"')}"`;
    exec(cmd, { timeout: 90000, windowsHide: true }, (err, stdout, stderr) => {
      if (err) res(`Hata: ${err.message}`);
      else res((stdout || stderr || 'Yanut yok').trim());
    });
  });
}

const server = http.createServer(async (req, res) => {
  // CORS headers for dashboard
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  // API: System stats
  if (req.method === 'GET' && req.url === '/api/stats') {
    try {
      const statsPath = process.env.STATS_PATH || './data/istatistikler.json';
      const stats = fs.existsSync(statsPath) ? JSON.parse(fs.readFileSync(statsPath, 'utf8')) : {};
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, stats }));
    } catch(e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: e.message }));
    }
    return;
  }

  // API: Market regime
  if (req.method === 'GET' && req.url === '/api/regime') {
    try {
      const regimePath = process.env.REGIME_PATH || './data/piyasa_rejimi.json';
      const regime = fs.existsSync(regimePath) ? JSON.parse(fs.readFileSync(regimePath, 'utf8')) : { son_rejim: 'belirsiz' };
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, regime }));
    } catch(e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: e.message }));
    }
    return;
  }

  // API: Win rate trigger
  if (req.method === 'POST' && req.url === '/api/winrate') {
    let body = '';
    req.on('data', c => body += c);
    req.on('end', () => {
      try {
        const payload = JSON.parse(body);
        const winRatePath = process.env.WIN_RATE_PATH || './scripts/win_rate.js';
        if (fs.existsSync(winRatePath)) {
          const { ekleIslem } = require(winRatePath);
          const id = ekleIslem(payload);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, id }));
        } else {
          res.writeHead(404, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: false, error: 'win_rate.js not found' }));
        }
      } catch(e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: e.message }));
      }
    });
    return;
  }

  if (req.method !== 'POST' || req.url !== '/tradingview') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true, msg: 'AnatoliaX Webhook Server - POST /tradingview | GET /api/stats | GET /api/regime' }));
    return;
  }

  let body = '';
  req.setEncoding('utf8');
  req.on('data', chunk => { body += chunk; });
  req.on('end', async () => {
    try {
      const payload = JSON.parse(body);
      log(`Webhook: ${JSON.stringify(payload).substring(0, 200)}`);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, received: true }));

      const agent = selectAgent(payload.alert_name, payload.message);
      const prompt = buildPrompt(payload);
      log(`Agent: ${agent}`);

      const result = await runAgent(agent, prompt);
      log(`Result uzunluk: ${result.length}`);

      const symbol = payload.symbol || '?';
      const price = payload.price || '?';
      sendTelegram(`<b>TradingView Alert</b>\n<b>Sembol:</b> ${symbol}\n<b>Fiyat:</b> ${price}\n\n<b>Konsey (${agent.toUpperCase()}):</b>\n${result.substring(0, 3500)}`);
    } catch (e) {
      log(`Hata: ${e.message}`);
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false, error: e.message }));
    }
  });
});

server.listen(PORT, () => {
  log('========================================');
  log('AnatoliaX Webhook Server BASLADI');
  log(`Port: ${PORT}`);
  log(`URL: ${process.env.WEBHOOK_URL || 'https://YOUR_TUNNEL_URL/tradingview'}`);
  log('========================================');
});
