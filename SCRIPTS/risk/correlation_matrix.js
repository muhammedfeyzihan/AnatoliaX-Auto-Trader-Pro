// ============================================================
// correlation_matrix.js - Korelasyon Hesaplama (K128)
// ============================================================

class CorrelationMatrix {
    constructor() {
        this.matrix = {};
    }

    calculate(returns) {
        const symbols = Object.keys(returns);
        for (const s1 of symbols) {
            this.matrix[s1] = {};
            for (const s2 of symbols) {
                this.matrix[s1][s2] = this._correlation(returns[s1], returns[s2]);
            }
        }
        return this.matrix;
    }

    _correlation(a, b) {
        const n = Math.min(a.length, b.length);
        const meanA = a.slice(0, n).reduce((s, v) => s + v, 0) / n;
        const meanB = b.slice(0, n).reduce((s, v) => s + v, 0) / n;
        let num = 0, denA = 0, denB = 0;
        for (let i = 0; i < n; i++) {
            const da = a[i] - meanA;
            const db = b[i] - meanB;
            num += da * db;
            denA += da * da;
            denB += db * db;
        }
        const denom = Math.sqrt(denA * denB);
        return denom > 0 ? num / denom : 0;
    }

    get(symbol1, symbol2) {
        return this.matrix[symbol1]?.[symbol2] || 0;
    }

    findHighCorrelation(threshold = 0.80) {
        const pairs = [];
        const symbols = Object.keys(this.matrix);
        for (let i = 0; i < symbols.length; i++) {
            for (let j = i + 1; j < symbols.length; j++) {
                const corr = Math.abs(this.matrix[symbols[i]][symbols[j]]);
                if (corr > threshold) pairs.push({ s1: symbols[i], s2: symbols[j], correlation: corr });
            }
        }
        return pairs;
    }
}

module.exports = CorrelationMatrix;
