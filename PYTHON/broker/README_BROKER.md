# Real Broker BIST Integration

**Versiyon:** 1.0.0 | **Modul:** `PYTHON/broker/`

## Ozet

Gercek BIST araci kurum entegrasyonu: FIX, WebSocket, REST protokolleri ile Matriks, Gedik, Is Yatirim adaptoreri.

## Bilesenler

- `core/` — Soyut arayuz, fabrika, emir tipleri, onaylayici
- `protocols/` — FIX 4.2/4.4 oturum, WebSocket, REST istemcileri
- `adapters/` — Matriks, Gedik, Is Yatirim, MockBroker
- `bist/` — Devre kesici, VBTS, aciga satis yasak
- `viop/` — Marjin hesaplayici, VIOP adaptoru
- `risk/` — On-ticaret risk kontrolu (<10us)
- `reconciliation/` — Gun sonu konum uzlastirma
- `reporting/` — Turk vergi duzenlemelerine uygun raporlama

## Kural Uyumu

- K142-K148: BIST duzenlemeleri
- K94: Sembol basina maksimum %2
- K101: VIOP marjin kontrolu
