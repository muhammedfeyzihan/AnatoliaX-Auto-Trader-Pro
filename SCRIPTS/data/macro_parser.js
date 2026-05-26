// ============================================================
// macro_parser.js — Makro Veri Isleme ve Rejim Tespiti
// TCMB faiz, enflasyon, doviz, altin, petrol, VIX -> piyasa rejimi
// ============================================================

const logger = require('../core/logger');

class MacroParser {
    constructor() {
        this.weights = {
            trend: 0.35,
            momentum: 0.25,
            volume: 0.20,
            closeStrength: 0.10,
            news: 0.10,
        };
    }

    /**
     * Ham makro verisini isle, skorlar uret.
     * @param {Array<{type:string, value:number}>} rawData
     * @returns {{regime:string, score:number, details:object}}
     */
    parse(rawData) {
        const map = {};
        rawData.forEach(d => { map[d.type] = d.value; });

        // 1. Trend skoru (USD/TRY + BIST100)
        const trendScore = this.calcTrend(map.USDTRY, map.BIST100);

        // 2. Momentum skoru (VIX + SP500)
        const momentumScore = this.calcMomentum(map.VIX, map.SP500);

        // 3. Hacim skoru (Altin + Petrol)
        const volumeScore = this.calcVolume(map.GOLD, map.BRENT);

        // 4. Kapanis gucu (enflasyon + faiz)
        const closeScore = this.calcCloseStrength(map.INFLATION, map.TCMB_RATE);

        // 5. Haber/hissiyat (EURTRY)
        const newsScore = this.calcNews(map.EURTRY);

        const totalScore = Math.round(
            trendScore * this.weights.trend +
            momentumScore * this.weights.momentum +
            volumeScore * this.weights.volume +
            closeScore * this.weights.closeStrength +
            newsScore * this.weights.news
        );

        const regime = this.classifyRegime(totalScore);

        logger.info(`[MACRO_PARSER] Rejim: ${regime} | Skor: ${totalScore}`);

        return {
            regime,
            score: totalScore,
            details: {
                trend: trendScore,
                momentum: momentumScore,
                volume: volumeScore,
                closeStrength: closeScore,
                news: newsScore,
                raw: map,
            },
        };
    }

    calcTrend(usdtry, bist100) {
        if (!usdtry || !bist100) return 50;
        // USD/TRY duserse + BIST100 yukseliyorsa = BULL (100)
        // USD/TRY yukseliyorsa + BIST100 duserse = BEAR (0)
        let s = 50;
        if (usdtry < 35) s += 25;
        else if (usdtry > 40) s -= 25;
        if (bist100 > 10000) s += 25;
        else if (bist100 < 8000) s -= 25;
        return Math.max(0, Math.min(100, s));
    }

    calcMomentum(vix, sp500) {
        if (!vix || !sp500) return 50;
        // VIX < 20 = sakin, > 30 = volatil
        let s = 50;
        if (vix < 20) s += 20;
        else if (vix > 30) s -= 20;
        if (sp500 > 5000) s += 10;
        return Math.max(0, Math.min(100, s));
    }

    calcVolume(gold, brent) {
        if (!gold || !brent) return 50;
        // Altin yukseliyorsa = risk off = BIST icin notr
        let s = 50;
        if (gold > 2300) s -= 10;
        if (brent > 85) s -= 10; // petrol pahali = enflasyon baskisi
        return Math.max(0, Math.min(100, s));
    }

    calcCloseStrength(inflation, rate) {
        if (!inflation || !rate) return 50;
        // Faiz > enflasyon = pozitif reel faiz = BIST icin iyi
        let s = 50;
        if (rate > inflation + 5) s += 20;
        else if (rate < inflation) s -= 20;
        return Math.max(0, Math.min(100, s));
    }

    calcNews(eurtry) {
        if (!eurtry) return 50;
        // EUR/TRY istikrarsizligi = risk
        let s = 50;
        if (eurtry > 38) s -= 15;
        else if (eurtry < 35) s += 10;
        return Math.max(0, Math.min(100, s));
    }

    classifyRegime(score) {
        if (score >= 70) return 'BULL';
        if (score >= 41) return 'SIDEWAYS';
        return 'BEAR';
    }
}

module.exports = new MacroParser();
