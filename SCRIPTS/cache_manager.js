const fs = require('fs');
const path = require('path');
const http = require('https');

const CACHE_DIR = 'C:\\Users\\feyzi\\.openclaw\\cache';
const CACHE_TTL = 15 * 60 * 1000; // 15 dakika (Bigpara gecikmesi)

if (!fs.existsSync(CACHE_DIR)) fs.mkdirSync(CACHE_DIR, { recursive: true });

function getCachePath(key) {
    return path.join(CACHE_DIR, `${key.replace(/[^a-zA-Z0-9]/g, '_')}.json`);
}

function get(key, ttl = CACHE_TTL) {
    const p = getCachePath(key);
    if (!fs.existsSync(p)) return null;
    try {
        const data = JSON.parse(fs.readFileSync(p, 'utf8'));
        if (Date.now() - data._timestamp > ttl) {
            fs.unlinkSync(p);
            return null;
        }
        return data.value;
    } catch(e) {
        return null;
    }
}

function set(key, value) {
    const p = getCachePath(key);
    fs.writeFileSync(p, JSON.stringify({ value, _timestamp: Date.now() }, null, 2), 'utf8');
}

function clear() {
    const files = fs.readdirSync(CACHE_DIR);
    for (const f of files) {
        if (f.endsWith('.json')) fs.unlinkSync(path.join(CACHE_DIR, f));
    }
    console.log(`Cache temizlendi: ${files.length} dosya silindi.`);
}

// Bigpara proxy with cache
function fetchBigpara(url, key) {
    return new Promise((res, rej) => {
        const cached = get(key);
        if (cached) {
            console.log(`[CACHE HIT] ${key}`);
            return res(cached);
        }
        console.log(`[CACHE MISS] ${key} - Bigpara'dan cekiliyor...`);
        http.get(url, (r) => {
            let d = '';
            r.on('data', c => d += c);
            r.on('end', () => {
                try {
                    const data = JSON.parse(d);
                    set(key, data);
                    res(data);
                } catch(e) {
                    res(d);
                }
            });
        }).on('error', rej);
    });
}

// CLI
const args = process.argv.slice(2);
if (args[0] === 'clear') {
    clear();
} else if (args[0] === 'stats') {
    const files = fs.readdirSync(CACHE_DIR).filter(f => f.endsWith('.json'));
    console.log(`Cache durumu: ${files.length} dosya`);
    for (const f of files) {
        const p = path.join(CACHE_DIR, f);
        const stat = fs.statSync(p);
        const data = JSON.parse(fs.readFileSync(p, 'utf8'));
        const age = Math.floor((Date.now() - data._timestamp) / 1000);
        console.log(`  ${f}: ${stat.size} byte | yas: ${age}s`);
    }
} else {
    console.log(`Kullanim:
  node cache.js clear  -> Tum cache'i temizle
  node cache.js stats  -> Cache durumunu goster`);
}

module.exports = { get, set, clear, fetchBigpara };
