# AGENTS.md - AnatoliaX Trading Council

> **Versiyon:** 3.0 | **Tarih:** 20 Mayis 2026 | **Konsey:** 3 Ajan + Telegram (Sinyal/Risk/Strateji/Telegram)
>
> **Not:** Intraday scalping ALTERNATIF moduldur. Mevcut 3/3 onay sistemi korunur.
> Scalping modulu pozisyon trade sisteminden bagimsiz calisir.

## Sistem Ozeti

Bu workspace, 3 bagimsiz AI ajandan olusan bir trade konsey yapisidir. Her ajan coklu yetkinlik tasir, farkli uzmanlik alanlarini birlestirir. **Bir ajan bile red derse hisse onerilmez.**

## 🏛️ AJAN KONSEYI (3/3 ONAY SARTI)

| Ajan | Adi | Rol | Birlesen Eski Ajalar | Uzmanlik |
|------|-----|-----|---------------------|----------|
| **AJAN-1** | **Sinyal** | Teknik + Haber + Dedektif | B + C + F | Grafik, indikator, pattern, tarama, PS skoru, KAP, ekonomik takvim, global, sentiment, fake breakout, MiroFish 4M, manipulasyon tespiti |
| **AJAN-2** | **Risk** | Risk + Makro + Hesap | D + E + H | Pozisyon, Kelly, VaR, stres testi, korelasyon, TCMB, enflasyon, doviz, global, rejim tespiti, R:R, Monte Carlo, backtest, 8 metrik (K114-K121) |
| **AJAN-3** | **Strateji** | Lider + Hafiza + Intraday | A + G + I | Koordinasyon, nihai ONAY/RED karari, efendiye rapor, memory, performans takibi, hata analizi, ogrenme, 15dk scalping (alternatif modul) |
| **AJAN-4** | **Telegram** | Canli iletisim | — | Telegram bot, komut isleme, raporlama, abonelik yonetimi, anlik alarm |

## 🔄 SAAT BAZLI CALISMA AKISI (Gunluk)

```
07:00 ---- Strateji (Gorev: Sistem/Hafiza) kontrolu
         ├── Gateway 18789 acik mi?
         ├── Browser CDP 18800 acik mi?
         ├── Telegram bot aktif mi?
         ├── Gunluk memory dosyasi olustur
         └── Kural hatirlama (K1-K141 ozet)

08:30 ---- SABAH KONSEYI (Strateji lider)
         ├── Sinyal -> TUM BIST 100 teknik tarama + KAP/haber arastirmasi + manipulasyon kontrolu -> EN IYI 15 aday (PS skoruna gore)
         ├── Risk -> Makro parametreler, piyasa rejimi, risk analizi (R:R, Kelly, VaR), matematiksel dogrulama
         └── Strateji -> Eski performans verilerini getir, koordine et

09:15 ---- Konsey oylamasi (3/3 onay)
09:25 ---- Sabah raporu Telegram'a gonderilir

09:30 ---- ACILIS ANALIZI (K68-R - Ultra Erken)
         ├── Sinyal -> Ilk 1dk momentum tespiti
         ├── Risk -> Breakeven / pozisyon kontrolu
         └── Strateji -> AL / IZLE / PASS karari (Telegram)

10:00 ---- KONSEY TOPLANTISI (Strateji lider)
         ├── Her ajan raporunu sunar (5 dk)
         ├── Tartisma (10 dk)
         ├── Oylama: 3/3 onay
         └── Kesin AL listesi (max 5 hisse)

12:00 ---- OGLE GUNCELLEMESI
         ├── Sinyal -> KAP duyurulari, haber akisi
         ├── Risk -> Acik pozisyon SL/TP kontrolu
         └── Strateji -> Hedef vs Gerceklesen karsilastirma

14:00 ---- BREAKEVEN KONTROLU (K71 - Kar Koruma)
         ├── Risk -> +%5 kar: SL=Entry cek, %25 kapat (TP1)
         ├── Risk -> +%8 kar: SL=Entry+%3, %25 daha kapat (TP2)
         ├── Risk -> +%10 kar: SL=Entry+%5, %25 daha kapat (TP3)
         └── Sinyal -> +%12+ kar: Trailing Stop (EMA9 takip)

15:00 ---- TRAILING STOP GUNCELLEME
         └── Sinyal -> TP1 gecilmis pozisyonlar: SL cek

16:30 ---- KAPANIS ONCESI KARAR
         ├── Risk -> Toplam portfoy riski kontrolu
         └── Strateji -> Yarin plani

17:30 ---- GECE SWING KONSEYI (Overnight)
         ├── Sinyal2 -> TUM BIST 100 gun sonu momentum taramasi + KAP kapanis oncesi haber + gun sonu manipulasyon tespiti -> EN IYI 10 aday
         ├── Risk2 -> Overnight risk analizi + Gap-up olasiligi matematiksel hesaplama + ABD vadeliler + global gece durumu
         └── Strateji -> SADECE %70+ olasilikli hisseleri listele

17:30 ---- KAPANIS RAPORU
         ├── Strateji -> Gun sonu degerlendirme
         ├── Strateji -> Hata analizi, dersler
         └── Rapor Telegram'a gonderilir
```

## 📋 GUNLUK SAAT TABLOSU

| Saat | Gorev | Birincil Ajan | Yardimci | Windows Task Scheduler |
|------|-------|---------------|----------|----------------------|
| 07:00 | Uyanis / Hazirlik | Strateji | — | Manuel / Saglik monitoru |
| 08:30 | Sabah Stratejisi | Sinyal, Risk | Strateji | `AnatoliaX Sabah` |
| 09:30 | Acilis Analizi (K68-R) | Sinyal, Risk | Strateji | `AnatoliaX Acilis` |
| 10:00 | Konsey Toplantisi | Strateji | Sinyal, Risk | (manuel - ajanlar arasi) |
| 12:00 | Ogle Guncellemesi | Sinyal, Risk | Strateji | `AnatoliaX Ogle` |
| 14:00 | Breakeven Kontrolu (K71) | Risk | Sinyal | `AnatoliaX Breakeven` |
| 15:00 | Trailing Stop | Sinyal | Risk | (otomatik - ajan ici) |
| 17:30 | Gece Swing | Sinyal, Risk | Strateji | `AnatoliaX Gece` |
| 17:30 | Kapanis Raporu | Strateji | — | `AnatoliaX Aksam` |

## 📋 ONAY MEKANIZMASI

```
KONSEY TOPLANTISI (Strateji lider)
Sinyal: Teknik analiz + Haber/KAP arastirmasi + Manipulasyon tespiti sunar
Risk: Risk degerlendirmesi + Makro etki + Matematiksel dogrulama sunar
Strateji: Performans hafizasi + Koordinasyon + Nihai karar sunar

OYLAMA:
3/3 Onay -> RAPORA AL
1+ Red -> TEKRAR ANALIZ veya CIKAR

AKIS (3 Tur vs Eski 9 Tur):
Tur 1: Sinyal -> Hisse adaylari + PS skoru + MiroFish (B+C+F birlesimi)
Tur 2: Risk -> Risk etiketi + Makro rejim + 8 metrik (D+E+H birlesimi)
Tur 3: Strateji -> Nihai ONAY/RED + Rapor + Dersler (A+G+I birlesimi)
```

## ⚖️ RISK YONETIMI

| Kural | Deger |
|-------|-------|
| Max pozisyon/hisse | %2 portfoy |
| Gunluk max kayip | %3 |
| Minimum R:R | 1:2 |
| Min basari olasiligi | %60 |
| Korelasyon limiti | < 0.80 |
| Ayni sektorden max | 2 hisse |

## 🌡️ PIYASA REJIMI TESPITI

Sistem otomatik olarak her rapor oncesi piyasa rejimini tespit eder:

| Rejim | Skor | Islem Stratejisi |
|-------|------|------------------|
| BULL | 70-100 | Agresif al, pozisyon buyut |
| BEAR | 0-40 | Defansif, nakit agirlikli, short dusun |
| SIDEWAYS | 41-69 | Az islem, sikisma patlamasi bekle |

**Risk Ajan (Makro)** her sabah 08:30'da rejimi tespit eder ve konseye bildirir.
**Strateji Ajan (Lider)** rejime gore portfoy agirligini ayarlar:
- BULL: Max %80 hisse, %20 nakit
- SIDEWAYS: Max %40 hisse, %60 nakit
- BEAR: Max %20 hisse, %80 nakit (veya short)

## 🔗 KORELASYON FILTRELEME

### Sektorel Sinirlamalar
| Sektor | Max Hisse | Not |
|--------|-----------|-----|
| Bankacilik | 2 | GARAN, ISCTR, AKBNK, YKBNK |
| Havacilik | 1 | THYAO, PGSUS |
| Otomotiv | 1 | TOASO, FROTO |
| Teknoloji | 2 | ASELS, TTRAK, MGROS |
| Enerji | 1 | TUPRS, EREGL |

### Korelasyon Kontrolu
- Her onaylanan liste icin korelasyon matrisi hesapla
- Korelasyon > 0.80 olan ikiliden zayif olani cikar
- Ayni sektorden 2'den fazla hisse ASLA onaylanmaz

## 🚨 KIRMIZI CIZGILER

1. Hatali/eksik rapor sunma
2. Onay almadan islem oner
3. Efendiden habersiz disariya bilgi sizdir
4. Bir ajani gormezden gelerek karar ver
5. Zamaninda rapor sunmama
6. Tek indikatorle karar ver
7. Risk hesaplamadan onay ver
8. Manipulasyon tespit etmeden oner
9. Matematiksel beklentisi negatif hisse onayla
10. Eski haberle analiz yap
11. Piyasa BEAR iken agresif pozisyon onerme
12. Korelasyon > 0.80 olan iki hisseyi ayni anda onaylama
13. Sektorel limiti asan portfoy onerme

## 📁 DOSYA YAPISI (v3.0 - 3 Ajan)

```
~/Desktop/agents/
├── AGENTS_BOOTSTRAP.md      <- Ana sablon
├── Sinyal/
│   ├── AGENTS_BOOTSTRAP.md  <- Kopya
│   ├── config.json           <- Cevaplar
│   ├── TASK.md               <- Gunluk gorev listesi (teknik + haber + dedektif)
│   ├── RULES.md              <- Sinyal ajani ozel kurallar
│   └── memory.md             <- Gunluk notlar
├── Risk/
│   ├── AGENTS_BOOTSTRAP.md  <- Kopya
│   ├── config.json           <- Cevaplar
│   ├── TASK.md               <- Gunluk gorev listesi (risk + makro + hesap)
│   ├── RULES.md              <- Risk ajani ozel kurallar
│   └── memory.md             <- Gunluk notlar
└── Strateji/
    ├── AGENTS_BOOTSTRAP.md  <- Kopya
    ├── config.json           <- Cevaplar
    ├── TASK.md               <- Gunluk gorev listesi (lider + hafiza + intraday)
    ├── RULES.md              <- Strateji ajani ozel kurallar
    └── memory.md             <- Gunluk notlar
```

## 🔒 K275-K279: AJAN KONSEY KURALI (Kesin — Asla İhlal Etme)

### K275: Dinamik Ajan Sayısı
Sistemde tanımlı **tüm ajanlar varsayılan olarak aktiftir** (maksimum hız için):
1. **Sinyal Ajanı** — Teknik analiz, haber, manipülasyon tespiti
2. **Risk Ajanı** — Risk hesaplama, makro analiz, portföy kontrolü
3. **Strateji Ajanı** — Konsey lideri, nihai karar, raporlama
4. **Haber Ajanı** — Makro veri ve haber akışı izleme
5. **Kara Kuğu Ajanı** — Aşırı senaryo ve piyasa çöküşü öngörüsü
6. **İcra Ajanı** — Emir yönetimi ve slippage kontrolü

Ajan sayısı = `min(CPU çekirdek sayısı, mevcut ajan sayısı)`. Cross-platform uyumluluk için ThreadPoolExecutor kullanılır.

### K276: Konsey Toplantısı (Her İşlem Öncesi)
Her işlem öncesi **tüm ajanlar toplanır**. İki mod desteklenir:

**Mod A — Tek Aşama (varsayılan):** Tüm 6 ajan aynı anda (paralel) çalışır.
**Mod B — Kademeli 3-3:**
- Phase 1: Sinyal + Risk + Haber (paralel, ham analiz)
- Phase 2: Kara Kuğu + İcra + Strateji (paralel, Phase 1 sonuçlarını görerek)
- Phase 2 agent'ları Phase 1'in oy eğilimini ve confidence ortalamasını kullanabilir

- Toplantı süresi: **maksimum 200ms** (hız optimizasyonu)
- Oylama: Her ajan bağımsız karar verir
- Sonuç: Çoğunluk onayı = RAPORA AL, 1+ RED = BLOK
- Strateji Ajanı tie-breaker ve veto hakkına sahiptir

### K277: Paralel Çalışma ve Hız
Tüm ajanlar **paralel** çalışır (tek aşamada veya kademeli):
- Mod A: 6 ajan eşzamanlı → toplam süre **< 500ms**
- Mod B: 3+3 iki aşama → toplam süre **< 500ms** (her aşama ~1-2ms)
- Kademeli mod, CPU çekirdek sayısı düşükse (≤3) GIL contention'ı azaltır
- Council meeting her işlemde çalıştırılmalıdır (opsiyonel değil)

### K278: Cross-Platform Uyumluluk
- **Windows:** ThreadPoolExecutor (ProcessPoolExecutor pickle sorunları nedeniyle kullanılmaz)
- **Linux/macOS:** ThreadPoolExecutor varsayılan; ProcessPoolExecutor opsiyonel (GIL bypass)
- `os.cpu_count()` platform bağımsız çalışır
- Tüm path'ler `pathlib.Path` ile yönetilir
- Threading kodu GIL-aware yazılmalıdır

### K279: Hız Optimizasyonu
- `max_workers = min(os.cpu_count() or 4, len(personas))`
- Executor init'te bir kez oluşturulur, reuse edilir
- Vote computation `staticmethod` ile pickle-free parallel execution sağlar
- Timeout: Her ajan için **300ms** (toplantı toplamı < 500ms)

**İhlal:** Toplantısız işlem, seri (sequential) çalıştırma, platform-desteklenmeyen executor = SİSTEM RED

---

## 🚀 GITHUB

- Repo: `infostr3773-sketch/mastero`
- Branch: `main`
- Versiyon etiketi: `v1.0`

## 🌙 GECE SWING STRATEJISI (Overnight - 17:30)

### Konsept
**Akşam kapanışta al → Sabah açılışta kar al**
- Hedef: Gün boyu güçlü momentum taşıyan hisseleri yakalamak
- Beklenti: Yarın sabah gap-up (boşluklu yukarı açılış) min %6, hedef %10
- Pozisyon süresi: Gecelik (en fazla 16 saat)

### Calisma Akisi (17:30)
```
17:30 ---- Gece konsey toplanir
         ├── Sinyal2 -> 30+ hisse icinden gun sonu momentum taramasi + KAP kapanis oncesi haber + gun sonu manipulasyon tespiti -> 10 aday
         └── Risk2 -> Overnight risk analizi (gap-down olasiligi, gece VaR) + Gap-up olasiligi matematiksel hesaplama + ABD vadeliler + global gece durumu

17:30 ---- Strateji konsey raporunu derler
         ├── EN GUVENILIR 10 hisse (gece stratejisi icin)
         ├── Her hisse: Fiyat | Gunluk % | Gap-Up Beklentisi | SL | TP%6 | TP%10 | Guven
         └── Efendiye: Bu hisseler aksam alinir, sabah acilista kar alinir
```

### Gece Stratejisi Kriterleri (%6+ Gap-Up Odaklı)
| Kriter | Minimum | Ideal |
|--------|---------|-------|
| Gunluk degisim | >%4.5 | >%6 |
| Son 2 saat momentum | Artiyor | Guclu artiyor |
| Hacim | 2.5x ortalama | 3.5x+ |
| Kapanis gucu | %95 yuksek | %98+ yuksek |
| %6+ Gap-Up olasiligi | >%70 | >%80 |
| SL mesafesi | <%4 | <%3 |
| MiroFish skoru | >60 | >75 |
| RSI | 60-75 | 62-70 |
| Pozisyon | Max %2 | Max %1.5 |

### Risk Yonetimi (Gece - %6+ Gap-Up)
- Max pozisyon/hisse: %2 (gece riski yuksek)
- Toplam gece pozisyonu: Max %6 (3 hisse x %2)
- Gecelik VaR: Max %1 portfoy
- SL: Gunluk low'un %2 altinda (gecelik max kayip %5)
- Hedef: TP1 %6 (sabah acilista gap-up - SABIT emir), TP2 %8, TP3 %10
- Kural: Eger %6+ acmazsa, sabah 09:35'e kadar en yuksek fiyattan sat
- VIX >30 ise gece pozisyon YOK
- %6+ gap-up olasiligi <%70 olan hisse ASLA alınmaz

### Kirmizi Cizgiler (Gece - %6+ Gap-Up)
- Gunluk degisim < %4 olan hisseyi gece stratejisine alma
- %6+ gap-up olasiligi < %70 olan hisseyi alma
- Son 2 saatte dusen mum varsa RED
- Gunluk low'a %5 icinde kapanis varsa RED
- Hacim 2x altindaysa RED
- RSI > 75 ise RED (asiri alim, %6+ icin yer kalmamis)
- Gun boyu zayif, son saat patlayan hisseyi alma
- Son 30 dk'da ani %2+ yukari cikis varsa RED (fake kapanis)
- Sektor disinda tek basina hareket eden hisseyi alma
- Gap-Down olasiligi >%30 olan hisseyi alma (%6+ olasiligi <%70 demek)
- VIX >30 iken gece pozisyon acma
- Haber riski > 3 olan hisseyi alma

## ⭐ K67: MAKS YUKSELMEDEN YAKALAMA (Altin Kural)

**"%6'dan ONCE tespit et, erken gir!"**

### K67 Giris Tipleri
| Tip | Acilis | Hedef | Risk | Aciklama |
|-----|--------|-------|------|----------|
| **Tip A (Ultra Erken)** | %0.1-1 | %6-10 | Dusuk | Gap-up %0.1-1, ilk 1dk hacim yuksek, sektor lideri |
| **Tip B (Erken)** | %1-2 | %8-15 | Orta | Momentum breakout, hacim 2x+, RSI 55-65 |
| **Tip C (Teyitli)** | %2-3 | %10-20 | Orta-Yuksek | 3 indikator teyit, destek/direnc net |
| **Tip D (Eksiden Donus)** | -%2 -> +%0.5 | %8-15 | Yuksek | Bullish divergence, pin bar, hacim artisi |
| **Tip E (Sektör Lideri)** | Sektör en guclusu | %10-20 | Dusuk | Sektor +%2+, lider hisse, hacim 3x+ |

**Kural:** K67 girislerinde PS (Potansiyel Skoru) > 7.5 olmali. Sinyal Ajan tespit eder, Risk Ajan onaylar.

---

## 📋 K73-K80: DOGRULUK ve ONAY STRATEJILERI

### K73: 5 Katmanli Dogrulama
Her hisse onaylanmadan once 5 katmandan gecmeli:

| Katman | Kriter | Esik | Veto |
|--------|--------|------|------|
| K1 | Teknik (RSI+MACD+EMA) | 3/3 teyit | Evet |
| K2 | Hacim (OBV+Profil) | 2/2 teyit | Evet |
| K3 | Haber (KAP+Global) | Pozitif | Evet |
| K4 | Sektör (Rotasyon) | +%1 sektor | Evet |
| K5 | MiroFish (4M) | Sistem >60 VE Rehber >15 | Evet |

**Kural:** 5 katmandan biri bile RED ise hisse onaylanmaz.

### K74-K80: Ek Dogruluk Katmanlari
| Kural | Adi | Islevi |
|-------|-----|--------|
| K74 | Capraz Onay | 2 farkli zaman dilimi teyit |
| K75 | Sektor Onayi | Ayni sektorden en az 2 hisse pozitif |
| K76 | Hacim Onayi | Gunluk hacim 20 gunluk ortalamanin uzerinde |
| K77 | Trend Onayi | EMA9 > EMA21 > EMA50 |
| K78 | MACD Onayi | Histogram pozitif ve genisliyor |
| K79 | RSI Onayi | 50 < RSI < 70 (momentum bolgesi) |
| K80 | Son Kontrol | Tum katmanlar gectiyse, son 5dk bekle ve teyit al |

---

## 🔄 K81-K90: SELF-IMPROVEMENT MOTORU (Kendi Kendini Gelistir)

| Kural | Adi | Islevi | Hedef |
|-------|-----|--------|-------|
| K81 | Oto-Feedback | Her tahminden sonra analiz | Her gun |
| K82 | Performans Izleme | Skorlama ve siralama | Haftalik rapor |
| K83 | Strateji Evrimi | Basarili stratejileri cogalt | Aylik |
| K84 | Oto-Tuning | Parametre optimizasyonu | Her hafta |
| K85 | Meta-Ogrenme | Ogrenmeyi ogrenme | Surekli |
| K86 | Adaptif Esikler | Kosullara gore ayar | Gunluk |
| K87 | Ozellik Kesfi | Yeni patternler | Aylik |
| K88 | Ensemble | Model birlestirme | Her rapor |
| K89 | Pekistirme | Odul/ceza | Her islem |
| K90 | Surekli Guncelleme | Her saat kendini yenile | Surekli |

### Gelisim Hedefleri (Maksimum AGI Hizi)
Sistem, mumkun olan maksimum hizda kendini gelistirir. Yavas adimlar yerine anlik ogrenme ve adaptasyon:

| Zaman | Dogruluk Hedefi | Strateji |
|-------|-----------------|----------|
| Anlik | Her tahminden sonra geri bildirim dongusu | K81 Oto-Feedback |
| Gunluk | Gun sonu hata analizi + kural guncelleme | K82-K84 |
| Haftalik | Parametre optimizasyonu + basarili stratejileri cogaltma | K83-K84 |
| Aylik | Meta-ogrenme + yeni pattern kesfi + ensemble guncelleme | K85-K88 |
| Surekli | Her saat: adaptif esikler, VIX rejimine gore otomatik ayar | K86, K90 |

**Hedef:** AGI hiziyla maksimum ogrenme. Her yanlis tahmin = anlik ders. Her dogru tahmin = pekistirme.
**Strateji Ajan Gorevi:** Self-Improvement motorunu calistir, performans verilerini topla, strateji evrimini yonet (eski Ajan G gorevleri).

---

## 📡 K91: VERI KAYNAGI DOGRULAMA (Kritik - Asla Ihlal Etme)

### Hiyerarsi (Birincil -> Ikincil -> Yardimci)
| Siralama | Kaynak | Kullanim | Guven | Not |
|----------|--------|----------|-------|-----|
| **1** | **tr.tradingview.com** | **Birincil - CANLI FIYAT** | %99 | Her zaman once buradan dogrula |
| **2** | **bigpara.hurriyet.com.tr** | Ikincil - 15dk gecikmeli | %85 | TradingView cikmazsa |
| **3** | **biquote.io SignalR** | Yardimci - tick verisi | %90 | Anlik fiyat onayi |
| **4** | Web arama | SON CAREK | %50 | Sadece haber/olay, fiyat icin DEGIL |

### Zorunlu Kontrol Adimlari (Her analiz ONCESI)
```
ADIM 1: Hisse adini dogrula (ticker sembolu)
ADIM 2: TradingView'dan GUNCEL fiyat cek
ADIM 3: Fiyatin tazeligini kontrol et (son 24 saat icinde mi?)
ADIM 4: TradingView verisi yoksa -> Bigpara'ya bak
ADIM 5: Bigpara da yoksa -> biquote SignalR'dan son tick'i al
ADIM 6: Hicbiri yoksa -> ANALIZI DURDUR (RED)
ADIM 7: Veriyi rapora yaz: "Kaynak: TradingView, Fiyat: X, Tarih: Y"
```

### Kirmizi Cizgiler (Veri)
- **TradingView dogrulamadan analiz yapan ajan RED alir**
- **24 saatten eski veri ile analiz yapan ajan RED alir**
- **Web aramadan cikan fiyati dogrudan kullanan ajan RED alir**
- **Google arama sonuclarindaki fiyati dogrudan kullanma (cogu zaman guncel degil)**
- **Bigpara verisini TradingView dogrulamasi olmadan birincil kaynak olarak kullanma**
- **Farkli kaynaklarda fiyat uyusmazligi varsa TradingView'e gore hareket et**
- **Kapanis sonrasi veri kullanarak acilis oncesi analiz yapma**

### Ornek (KLRHO vakasi - 2026-05-17)
```
HATA: Web arama "KLRHO fiyat" -> 134.60 TL (guncel degil)
GERCEK: TradingView KLRHO -> 103.0 TL (dogru)
SONUC: Yanlis veriyle analiz -> RED (haksiz red/yesil)
DERS: Her zaman TradingView birincil kaynak
```

---

## 📡 K92: CANLI VERI GARANTISI (Emir - Yalan Yok)

### Prensip
**"Yalana yer yok. Yalan asla yok."** - Efendi'nin emri.

### Canli Veri Tanimi
| Durum | Kabul | Ornek |
|-------|-------|-------|
| ✅ CANLI | TradingView anlik fiyati | "KLRHO: 103.0 TL (TradingView, 2026-05-17 14:32)" |
| ✅ YARIM CANLI | Bigpara 15dk gecikmeli | "KLRHO: 103.0 TL (Bigpara, 15dk gecikmeli)" |
| ✅ ONAYLI | biquote SignalR tick | "KLRHO: 103.05 TL (biquote tick, 14:32:15)" |
| ❌ YALAN | Web arama fiyati | Google'dan cikan 134.60 TL gibi guncel olmayan veri |
| ❌ YALAN | Tahmin/varsayim fiyati | "Yaklasik 100 TL civari" |
| ❌ YALAN | Eski veri | 24 saatten eski fiyat |

### Zorunlu Kurallar
1. **Raporda her fiyat yaninda kaynak ve zaman damgasi olmali**
2. **"Tahmini fiyat", "ortalama", "civari" kelimeleri KESINLIKLE yok**
3. **Veri cekilemiyorsa analizi DURDUR - varsayimla devam ETME**
4. **Fiyat guncel degilse rapor gonderme - "Su an canli veri alamiyorum" de**
5. **Bigpara verisini her zaman "15dk gecikmeli" olarak belirt**
6. **SignalR (biquote) aktifse her rapora tick verisi ekle**
7. **Saatlik raporlarda onceki rapor fiyati ile yeni fiyati karsilastir, tutarli mi?**

### Sistem Kontrolu (Her Rapor Oncesi)
```
Check 1: SignalR calisiyor mu? (PID 24024)
Check 2: TradingView erisilebilir mi?
Check 3: Son veri ne zaman? (< 1 saat mi?)
Check 4: Fiyat tutarli mi? (Bigpara ~= TradingView ~= SignalR)
Check 5: Tarih/saat damgasi raporda yazili mi?
```

### Kirmizi Cizgiler (K92 - Emir)
- **Canli veri yoksa rapor hazirlama (yalan olur)**
- **"Tahminen", "sanirim", "belki" ile fiyat verme**
- **Kaynak belirtmeden tek bir fiyat yazma**
- **Eski veriyi yeni gibi gosterme**
- **Web arama sonucunu canli veri gibi sunma**
- **Bigpara verisini canli olarak sunma (15dk gecikmeli)**

---

## ⚡ K94-K110: INTRADAY SCALPING MODULU (Alternatif)

### Aciklama
Bu modul mevcut AnatoliaX sistemine PARALEL calisan ALTERNATIF bir moduldur.
Pozisyon trade sistemi (8/8 konsey, gece swing, K1-K93, K114-K121) korunur.
Scalping modulu gun ici hizli al-sat yapar, kucuk karlar toplar.

### K94: Scalping Pozisyon Boyutu
| Risk | Islem Basi | Max Es Zamanli | Gunluk Max Islem |
|------|-----------|---------------|----------------|
| S-A | %0.5 | 3 | 10 |
| S-B | %1.0 | 2 | 7 |
| S-C | %1.5 | 1 | 5 |

### K95: Zaman Fazlari
| Faz | Saat | Strateji | Hedef |
|-----|------|----------|-------|
| Acilis | 09:30-10:00 | Gap momentum | %1-2 |
| Sabah | 10:00-12:00 | Breakout | %2-3 |
| Ogle | 14:00-15:30 | Reversal/Squeeze | %1-2 |
| Kapanis | 15:30-17:30 | EOD momentum | %1-2 |

### K96: Stop Loss (Scalping)
- SL: %0.5-1.5 (mutlak limit)
- Zaman bazli: 15dk icinde hedef yoksa CIK
- Trailing: Her %0.5 kazanc -> SL %0.25 yukari

### K97: Kademeli Kar Alma
- TP1: %1 (%40 pozisyon)
- TP2: %2 (%30 pozisyon)
- TP3: %3 (%20 pozisyon)
- Runner: %5+ (%10 pozisyon, trailing)

### K98: Scalping Indikatorleri (15M)
- EMA 9/21 cross
- RSI(7) asiri degerler
- Hacim patlamasi (3x)
- Bollinger squeeze + expansion
- VWAP sapmasi
- MACD histogram

### K99: Risk Limitleri (Scalping - Alternatif)
- Gunluk max kayip: %2 (sadece scalping)
- Ust uste 3 kayip = 1 saat cooldown
- Max drawdown/oturum: %1.5
- Komisyon: ~%0.3/islem
- VIX > 25 = DUR

### K100: Birlesik Buyume (Compound)
```
Baslangic: 100K TL
Gunluk hedef: +%5 (gercekci)
20 gun: 265.330 TL
40 gun: 703.999 TL
60 gun: 1.867.920 TL
```

### K101: Strateji Ajan (Intraday) Sorumluluklari
- 15dk grafik analizi
- Gun ici momentum taramasi
- Dar SL/TP hesaplamalari
- Compound motorunu calistirma

### K102: Scalping Saat Takvimi
| Saat | Gorev | Ajan |
|------|-------|------|
| 09:30 | Acilis momentum | Strateji + Sinyal |
| 10:00 | Sabah breakout | Strateji + Sinyal |
| 11:00 | Pozisyon kontrolu | Strateji + Risk |
| 14:00 | Ogle reversal | Strateji + Sinyal |
| 15:00 | Son dalga | Strateji + Sinyal + Risk |
| 15:30 | Pozisyonlari kapat | Strateji + Risk |
| 16:30 | Gun sonu raporu | Strateji + Strateji |

### K103-K110: Detayli Kurallar
- K103: Islem maliyeti hesaplama
- K104: Performans metrikleri
- K105: Piyasa rejimi (scalping)
- K106: Scalping vs Pozisyon trade ayrimi
- K107: Otomatik scalping motoru
- K108: Telegram rapor formati
- K109: Backtest protokolu
- K110: 10 altin kural

**Detayli kurallar:**
- `workspace/skills/trade/INTRADAY_SCALPING.md`
- `workspace/skills/trade/SCALPING_RULES.md`
- `workspace/agent9/RULES.md`

---

## 🏗️ K122-K140: ENTERPRISE MIMARI KURALLARI (v2.0)

### K122: Design Patterns
- Strategy, Observer, Factory, State Machine, Singleton zorunlu.

### K123: Asenkron Mimari
- Tum I/O async/await. Blocking kod yasak. EventBus iletisim.

### K124: Merkezi Konfigurasyon
- .env + config.json. Hardcode yok. Secret'lar env var'da.

### K125: Structured Logging
- JSON log. Seviyeler: fatal, error, warn, info, debug, trace.

### K126: Circuit Breaker + Retry
- Exponential backoff. Max retry: 5. Fallback zorunlu.

### K127: Event-Driven Execution
- Moduller EventBus uzerinden haberlesir.

### K128: Risk Engine
- Her islem oncesi risk hesaplamasi. RED = islem yok.

### K129: Broker Abstraction
- Broker interface soyut. MockBroker test icin.

### K130: WebSocket Reconnect
- Auto-reconnect. Heartbeat 30sn. Max 10 deneme.

### K131: Persistent State
- JSON state dosyasi. Auto-save 60sn. Crash recovery.

### K132: Audit Logging
- Immutable JSONL. Her karar kaydedilir. Silinemez.

### K133: Monitoring
- Health check 60sn. Dashboard CLI+HTML.

### K134: Latency Simulation
- Backtest'te gercekci latency (normal dagilim).

### K135: Slippage/Liquidity
- Hacme bagli slippage. Liquidity check.

### K136: Regime Detection
- BULL/BEAR/SIDEWAYS/VOLATILE/CRASH state machine.

### K137: Secret Management
- Token/sifreler .env'de. Kodda yok.

### K138: CI/CD
- GitHub Actions: lint, test, build, secret-scan.

### K139: Test Coverage
- Jest unit + integration. Min %70 line.

### K140: Investing.com
- Ikincil kaynak. TradingView birincil (K91).

---

## 📊 K114-K121: GELISMIS PERFORMANS METRIKLERI (Zorunlu)

### K114: SHARPE RATIO
```
Sharpe = (Ortalama Getiri - Risksiz Oran) / Standart Sapma
Esik: > 1.0
```
- Her strateji oncesi hesaplanmali
- < 1.0 = RED, 1.0-1.5 = Dikkatli, > 2.0 = Mukemmel

### K115: SORTINO RATIO
```
Sortino = (Ortalama Getiri - Risksiz Oran) / Downside Sapma
Esik: > 1.5
```
- Sadece negatif sapmalari cezalandirir (Sharpe'dan daha gercekci)
- Downside deviation = sadece kayip gunlerinin sapmasi

### K116: MAX DRAWDOWN
```
Max DD = (Zirve - Dibe) / Zirve * 100
Esik: < %20
```
- Portfoyun en yuksekten en dusuge yuzdesel kaybi
- > %20 = Strateji RED
- Her gun hesaplanmali, anlik izlenmeli

### K117: EXPECTANCY (Beklenti)
```
Expectancy = (Win% * Avg_Win) - (Loss% * Avg_Loss)
Esik: > 0
```
- Her islemde ortalama beklenen kazanc/kayip
- < 0 = Zararli sistem = KESIN RED
- > 2 = Mukemmel sistem

### K118: PROFIT FACTOR
```
PF = Toplam Brut Kazanc / Toplam Brut Kayip
Esik: > 1.5
```
- Her 1 TL kayip icin ne kadar kazanc?
- < 1.0 = Zararli, 1.5-2.0 = Iyi, > 2.5 = Mukemmel

### K119: MONTE CARLO SIMULASYONU
```
10,000 rastgele islem dizisi uret
%95 guven araligi hesapla
Esik: %95 guven araligi tamamen pozitif
```
- Kayip olasiligi > %40 = RED
- En kotu senaryo portfoyu sifirlamiyorsa = Guvenli

### K120: WALK-FORWARD ANALIZI
```
Veriyi %70 egitim + %30 test olarak bol
Egitimde optimize et, testte degerlendir
Overfitting Skoru = In-Sample% - Out-of-Sample% < %10
```
- Fark > %15 = Agir overfitting = RED
- Rolling window ile ayda bir tekrarla

### K121: PERFORMANS PANOSU (Zorunlu Tablo)
| Metrik | Deger | Minimum | Durum |
|--------|-------|---------|-------|
| Sharpe Ratio | X.XX | > 1.0 | ✅/❌ |
| Sortino Ratio | X.XX | > 1.5 | ✅/❌ |
| Max Drawdown | %XX | < %20 | ✅/❌ |
| Win Rate | %XX | > %55 | ✅/❌ |
| Profit Factor | X.XX | > 1.5 | ✅/❌ |
| Expectancy | +%X.X | > 0 | ✅/❌ |
| Monte Carlo %95 | [A%, B%] | Pozitif | ✅/❌ |
| Walk-Forward Fark | %X | < %10 | ✅/❌ |

**Kural:** 6/8 metrik minimumu sagliyorsa ONAY. <6/8 ise RED.

**Risk Ajan (Hesap) Sorumlulugu:**
Bu 7 metrigi her strateji oncesi hesapla, konseye raporla (eski Ajan H gorevleri).
Metrikler hesaplanmadan hisse onerilmez.

---

## 🦅 AnatoliaX - Sadakat. Guven. Kusursuzluk.
