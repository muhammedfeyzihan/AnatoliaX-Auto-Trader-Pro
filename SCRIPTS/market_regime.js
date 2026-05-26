const fs = require('fs');

const DATA_DIR = 'C:\\Users\\feyzi\\.openclaw\\data';
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

const REGIME_FILE = `${DATA_DIR}/piyasa_rejimi.json`;
const LOG_FILE = `${DATA_DIR}/rejim_log.jsonl`;

function loadRegime() {
    if (!fs.existsSync(REGIME_FILE)) return { son_rejim: 'belirsiz', tarih: new Date().toISOString(), bist100: 0, vix: 0 };
    return JSON.parse(fs.readFileSync(REGIME_FILE, 'utf8'));
}

function saveRegime(data) {
    fs.writeFileSync(REGIME_FILE, JSON.stringify(data, null, 2), 'utf8');
    fs.appendFileSync(LOG_FILE, JSON.stringify({ ...data, timestamp: new Date().toISOString() }) + '\n', 'utf8');
}

function tespitEt(bist100, bist100Onceki, hacim, hacimOrtalama, dolar, dolarOnceki) {
    // BIST 100 degisimi
    const bistDegisim = ((bist100 - bist100Onceki) / bist100Onceki * 100);
    const hacimOran = hacim / hacimOrtalama;
    const dolarDegisim = ((dolar - dolarOnceki) / dolarOnceki * 100);

    let rejim = 'belirsiz';
    let skor = 50;
    let sebep = [];

    // BULL kosullari
    if (bistDegisim > 1.0) { skor += 20; sebep.push(`BIST +%${bistDegisim.toFixed(2)}`); }
    if (hacimOran > 1.5) { skor += 15; sebep.push(`Hacim ${hacimOran.toFixed(1)}x`); }
    if (dolarDegisim < -0.5) { skor += 10; sebep.push(`Dolar dusus %${dolarDegisim.toFixed(2)}`); }

    // BEAR kosullari
    if (bistDegisim < -1.0) { skor -= 20; sebep.push(`BIST -%${Math.abs(bistDegisim).toFixed(2)}`); }
    if (hacimOran > 1.5 && bistDegisim < 0) { skor -= 15; sebep.push(`Yuksek hacimli satis`); }
    if (dolarDegisim > 1.0) { skor -= 10; sebep.push(`Dolar yukselis %${dolarDegisim.toFixed(2)}`); }

    // SIDeways
    if (Math.abs(bistDegisim) < 0.5 && hacimOran < 1.2) { skor = 50; sebep.push('Yatay, dusuk hacim'); }

    // Rejim belirle
    if (skor >= 70) rejim = 'bull';
    else if (skor <= 40) rejim = 'bear';
    else rejim = 'sideways';

    const sonuc = {
        son_rejim: rejim,
        skor: skor,
        sebep: sebep,
        bist100: bist100,
        bist100_onceki: bist100Onceki,
        hacim_oran: hacimOran.toFixed(2),
        dolar: dolar,
        tarih: new Date().toISOString()
    };

    saveRegime(sonuc);
    return sonuc;
}

function rapor() {
    const r = loadRegime();
    const emoji = r.son_rejim === 'bull' ? '🐂' : r.son_rejim === 'bear' ? '🐻' : '🦀';
    return `
${emoji} PIYASA REJIMI RAPORU
========================
Rejim: ${r.son_rejim.toUpperCase()}
Skor: ${r.skor}/100
BIST 100: ${r.bist100}
Son Tarih: ${r.tarih ? r.tarih.substring(0, 16).replace('T', ' ') : '?'}
Sebep: ${(r.sebep || []).join(', ') || 'Veri yok'}
`;
}

// CLI
const args = process.argv.slice(2);
if (args[0] === 'tespit') {
    const sonuc = tespitEt(
        parseFloat(args[1]) || 14368,
        parseFloat(args[2]) || 14100,
        parseFloat(args[3]) || 169000000,
        parseFloat(args[4]) || 140000000,
        parseFloat(args[5]) || 45.5,
        parseFloat(args[6]) || 45.0
    );
    console.log('Rejim:', sonuc.son_rejim.toUpperCase(), '| Skor:', sonuc.skor);
} else if (args[0] === 'rapor') {
    console.log(rapor());
} else {
    console.log(`Kullanim:
  node market_regime.js tespit BIST100 BIST100_ONCEKI HACIM HACIM_ORT DOLAR DOLAR_ONCEKI
  node market_regime.js rapor`);
}

module.exports = { tespitEt, rapor, loadRegime };
