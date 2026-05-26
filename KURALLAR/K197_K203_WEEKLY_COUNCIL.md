# K197-K203 — Haftalik Strateji Konseyi Kurallari

**Versiyon:** 3.2  
**Tarih:** 2026-05-22  
**Kapsam:** Her cumartesi toplanan 3-ajan konseyi, haftalik hedef carpani, gecmis tecrube birlestirme.

---

## K197 — Cumartesi Toplantisi Zorunlulugu

Her cumartesi gunu (saat fark etmez) Sinyal + Risk + Strateji ajanlari `WeeklyCouncil.convene()` ile bir araya gelir.

- **Sinyal Ajan:** Gecen haftanin setup analizini raporlar (best/worst setup, win rate, zaman dilimi PnL).
- **Risk Ajan:** Drawdown, volatilite, behavioral metrikleri, rejim tespiti raporlar.
- **Strateji Ajan:** Gecmis haftalari analiz edip hedef carpani ve birincil stratejiyi belirler.

**Eger konsey toplanmazsa:** Sistem bir onceki haftanin stratejisini korur ama hedef carpani 0.5x'e duser (ultra-korumali mod).

---

## K198 — Hedef Carpani Matematigi (Multiplier)

Matematiksel olarak kademeli hedef carpani:

| Onceki Hafta Durumu | Yeni Carpani | Ornek |
|---|---|---|
| Net PnL > 0 (kazanc) | Carpani x2 | 1 → 2, 2 → 4, 4 → 8 |
| Net PnL < 0 (zarar) | Carpani /2 | 8 → 4, 2 → 1, 1 → 0.5 |
| Net PnL = 0 (notr) | Sabit | Degismez |

- **Ust Sinir:** 8.0 (asla gecilmez)
- **Alt Sinir:** 0.25 (asla dusmez)
- **Neden:** Compound growth korunurken asiri risk engellenir.

---

## K199 — 3/3 Onay Sarti

Konsey karari **sadece** 3 ajandan 3'u de APPROVE verirse yururluge girer.

- **Sinyal Ajan:** Win rate >= %40 → APPROVE, degilse REJECT
- **Risk Ajan:** Risk level != HIGH ve max DD <= %5 → APPROVE, degilse REJECT
- **Strateji Ajan:** Daima APPROVE (tum verileri birlestirir)

1 RED = karar RED. Onceki haftanin stratejisi korunur, hedef carpani 0.5x.

---

## K200 — Gecmis Tecrube Birlestirme

Konsey en az **4 haftalik gecmis veri** gerektirir. Daha az varsa:

- Hedef carpani sabit 1.0x
- Birincil strateji: "balanced"
- Tum zaman dilimleri esit agirlikli

4+ hafta oldugunda:
- En iyi setup'lar tespit edilir
- En kazancli zaman dilimi(leri) onceliklendirilir
- Rejim bazli strateji secimi aktif olur

---

## K201 — Rejim Bazli Strateji Secimi

Risk ajaninin tespit ettigi piyasa rejimine gore birincil strateji:

| Rejim | Birincil Strateji | Zaman Dilimleri |
|---|---|---|
| Bull | trend_following | H1, D1 |
| Bear | mean_reversion + hedge | M15, H1 |
| Sideways | scalping_range | M5, M15 |

Rejim degisimi tespit edilirse, onceki rejimin stratejisi yavas yavas azaltilir (1 haftada tam gecis).

---

## K202 — Risk Ayarlamalari

Konsey kararinda asagidaki risk limitleri mutlaka bulunur:

- **Max DD:** %5 (asla gecilmez)
- **Kelly Fraction:** 0.25 (Fractional Kelly)
- **Pozisyon Olcegi:**
  - DD < %2 → 1.0x
  - %2 <= DD < %5 → 0.75x
  - DD >= %5 → 0.5x

---

## K203 — Rapor Arsivi ve Izleme

Her konsey karari `CouncilDecision` olarak JSON formatinda arsivlenir.

- En az **son 8 hafta** rapor bellekte tutulur.
- Haftalik rapor ozeti:
  - Total islem, win rate, net PnL
  - Ortalama hedef carpani
  - En iyi ve en kotu hafta

Telegram botu cumartesi aksami konsey kararini otomatik iletir.

---

*AnatoliaX Trading System v3.2 — Sadakat. Guven. Kusursuzluk.*
