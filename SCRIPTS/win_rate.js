const fs = require('fs');
const path = require('path');

const DATA_DIR = 'C:\\Users\\feyzi\\.openclaw\\data';
const DB_FILE = path.join(DATA_DIR, 'islem_db.json');
const STATS_FILE = path.join(DATA_DIR, 'istatistikler.json');

// Klasor olustur
if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

// Baslangic verisi
function initDB() {
    if (!fs.existsSync(DB_FILE)) {
        fs.writeFileSync(DB_FILE, JSON.stringify({ islemler: [] }, null, 2), 'utf8');
    }
}

function initStats() {
    if (!fs.existsSync(STATS_FILE)) {
        fs.writeFileSync(STATS_FILE, JSON.stringify({
            toplam_islem: 0,
            kazanilan: 0,
            kaybedilen: 0,
            bekleyen: 0,
            win_rate: 0,
            ort_kar: 0,
            ort_zarar: 0,
            profit_factor: 0,
            stratejiler: {},
            ajanlar: {},
            gunluk: {}
        }, null, 2), 'utf8');
    }
}

function loadDB() {
    initDB();
    return JSON.parse(fs.readFileSync(DB_FILE, 'utf8'));
}

function saveDB(db) {
    fs.writeFileSync(DB_FILE, JSON.stringify(db, null, 2), 'utf8');
}

function loadStats() {
    initStats();
    return JSON.parse(fs.readFileSync(STATS_FILE, 'utf8'));
}

function saveStats(s) {
    fs.writeFileSync(STATS_FILE, JSON.stringify(s, null, 2), 'utf8');
}

// Islem ekle
function ekleIslem({ hisse, strateji, ajan, giris, sl, tp, durum, kar_zarar, notlar }) {
    const db = loadDB();
    const islem = {
        id: Date.now(),
        tarih: new Date().toISOString(),
        hisse,
        strateji: strateji || 'Bilinmiyor',
        ajan: ajan || 'main',
        giris: giris || 0,
        sl: sl || 0,
        tp: tp || 0,
        durum: durum || 'beklemede', // beklemde / kazanildi / kaybedildi
        kar_zarar: kar_zarar || 0,
        notlar: notlar || ''
    };
    db.islemler.push(islem);
    saveDB(db);
    guncelleIstatistikler();
    return islem.id;
}

// Islem guncelle (kapaninca)
function guncelleIslem(id, { durum, kar_zarar, notlar }) {
    const db = loadDB();
    const islem = db.islemler.find(i => i.id === id);
    if (!islem) return false;
    if (durum) islem.durum = durum;
    if (kar_zarar !== undefined) islem.kar_zarar = kar_zarar;
    if (notlar) islem.notlar = notlar;
    islem.kapanis_tarih = new Date().toISOString();
    saveDB(db);
    guncelleIstatistikler();
    return true;
}

// Istatistikleri yeniden hesapla
function guncelleIstatistikler() {
    const db = loadDB();
    const s = loadStats();
    const islemler = db.islemler;

    const kazanilan = islemler.filter(i => i.durum === 'kazanildi');
    const kaybedilen = islemler.filter(i => i.durum === 'kaybedildi');
    const bekleyen = islemler.filter(i => i.durum === 'beklemede');

    s.toplam_islem = islemler.length;
    s.kazanilan = kazanilan.length;
    s.kaybedilen = kaybedilen.length;
    s.bekleyen = bekleyen.length;
    s.win_rate = islemler.length > 0 ? (kazanilan.length / islemler.length * 100).toFixed(2) : 0;

    const toplamKar = kazanilan.reduce((sum, i) => sum + (i.kar_zarar || 0), 0);
    const toplamZarar = kaybedilen.reduce((sum, i) => sum + Math.abs(i.kar_zarar || 0), 0);
    s.ort_kar = kazanilan.length > 0 ? (toplamKar / kazanilan.length).toFixed(2) : 0;
    s.ort_zarar = kaybedilen.length > 0 ? (toplamZarar / kaybedilen.length).toFixed(2) : 0;
    s.profit_factor = toplamZarar > 0 ? (toplamKar / toplamZarar).toFixed(2) : toplamKar > 0 ? 'Infinity' : 0;

    // Strateji bazli
    s.stratejiler = {};
    for (const i of islemler) {
        if (!s.stratejiler[i.strateji]) s.stratejiler[i.strateji] = { toplam: 0, kazanilan: 0, kaybedilen: 0 };
        s.stratejiler[i.strateji].toplam++;
        if (i.durum === 'kazanildi') s.stratejiler[i.strateji].kazanilan++;
        if (i.durum === 'kaybedildi') s.stratejiler[i.strateji].kaybedilen++;
    }

    // Ajan bazli
    s.ajanlar = {};
    for (const i of islemler) {
        if (!s.ajanlar[i.ajan]) s.ajanlar[i.ajan] = { toplam: 0, kazanilan: 0, kaybedilen: 0 };
        s.ajanlar[i.ajan].toplam++;
        if (i.durum === 'kazanildi') s.ajanlar[i.ajan].kazanilan++;
        if (i.durum === 'kaybedildi') s.ajanlar[i.ajan].kaybedilen++;
    }

    saveStats(s);
}

// Rapor uret
function raporUret() {
    const s = loadStats();
    const db = loadDB();
    const son10 = db.islemler.slice(-10).reverse();

    return `
📊 ANATOLIAX WIN RATE RAPORU
=============================
Toplam Islem: ${s.toplam_islem}
Kazanilan: ${s.kazanilan} | Kaybedilen: ${s.kaybedilen} | Bekleyen: ${s.bekleyen}
Win Rate: %${s.win_rate}
Ort. Kar: %${s.ort_kar} | Ort. Zarar: %${s.ort_zarar}
Profit Factor: ${s.profit_factor}

Strateji Performanslari:
${Object.entries(s.stratejiler).map(([k,v]) => `- ${k}: ${v.kazanilan}/${v.toplam} (%${v.toplam>0?(v.kazanilan/v.toplam*100).toFixed(1):0})`).join('\n')}

Son 10 Islem:
${son10.map(i => `${i.tarih.substring(0,10)} | ${i.hisse} | ${i.strateji} | ${i.durum.toUpperCase()} | %${i.kar_zarar}`).join('\n')}
`;
}

// CLI
const args = process.argv.slice(2);
if (args[0] === 'ekle') {
    const id = ekleIslem({
        hisse: args[1] || 'Bilinmiyor',
        strateji: args[2] || 'Genel',
        ajan: args[3] || 'main',
        giris: parseFloat(args[4]) || 0,
        sl: parseFloat(args[5]) || 0,
        tp: parseFloat(args[6]) || 0,
        durum: args[7] || 'beklemede',
        kar_zarar: parseFloat(args[8]) || 0
    });
    console.log('Islem eklendi ID:', id);
} else if (args[0] === 'guncelle') {
    const ok = guncelleIslem(parseInt(args[1]), { durum: args[2], kar_zarar: parseFloat(args[3]) });
    console.log(ok ? 'Guncellendi' : 'Bulunamadi');
} else if (args[0] === 'rapor') {
    console.log(raporUret());
} else {
    console.log(`Kullanim:
  node win_rate.js ekle HISSE STRATEJI AJAN GIRIS SL TP DURUM KARZARAR
  node win_rate.js guncelle ID DURUM KARZARAR
  node win_rate.js rapor`);
}

module.exports = { ekleIslem, guncelleIslem, raporUret, loadStats };
