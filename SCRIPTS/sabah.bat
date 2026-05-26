@echo off
chcp 65001 >nul
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] AnatoliaX Sabah Taramasi basladi >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"

REM Gateway kontrol
curl -s http://127.0.0.1:18789/health >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Gateway kapali, baslatiliyor... >> "%USERPROFILE%\.openclaw\scripts\cron.log"
    start /min "" "%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" gateway run --force
    timeout /t 8 /nobreak >nul
)

REM Browser kontrol
curl -s http://127.0.0.1:18800/json/version >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Browser kapali, baslatiliyor... >> "%USERPROFILE%\.openclaw\scripts\cron.log"
    start /min "" "%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" browser --browser-profile openclaw start
    timeout /t 8 /nobreak >nul
)

echo [%date% %time%] === CANLI VERI KAYNAKLARI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Bigpara.hurriyet.com.tr (15 dk gecikmeli, ama gunluk guncel) >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] KAP.gov.tr (anlik) >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Investing.com/tr (global, 15 dk gecikmeli) >> "%USERPROFILE%\.openclaw\scripts\cron.log"

REM Sabah taramasi - A Lider olarak B-H ajanlarini sirayla calistir
REM NOT: Ajanlar ayni anda calisirsa gateway 1000 closure hatasi verir. SIRAYLA calismalari sart.

echo [%date% %time%] === AJAN B (TEKNIK) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent2 --message "08:30 SABAH TARAMASI - Bigpara.hurriyet.com.tr/borsa/canli-borsa/ adresine git, snapshot al. BIST 100 anlik deger, gunluk degisim, hacim. En cok artan/azalan 30+ hisseyi listele: Hisse | Fiyat | Degisim% | Hacim. Teknik durumlarini degerlendir. 10 aday sec. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN C (HABER) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent3 --message "08:45 HABER TARAMASI - KAP.gov.tr ve bigpara.hurriyet.com.tr adreslerine git. Son 24 saatteki KAP ozel durum bildirimleri, pay alim-satimlari, araci kurum raporlarini oku. Ekonomik takvimi kontrol et. Her aday hisse icin haber risk skoru (1-5). Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN E (MAKRO) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent5 --message "09:00 MAKRO ANALIZ - Bigpara'dan CANLI VERI: USD/TRY, EUR/TRY, altin, petrol, BIST 100, BIST Banka degerlerini oku. Piyasa rejimi tespit et: Trending/Momentum/Range/Volatile. Global piyasalar nasil? Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN F (DEDEKTIF) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent6 --message "09:00 MANIPULASYON ANALIZI - Aday hisselerin CANLI grafiklerinde fake breakout, liquidity sweep, spike, squeeze pattern var mi? MiroFish skoru hesapla. Anomali varsa RED. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN D (RISK) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent4 --message "09:15 RISK ANALIZI - Aday hisselerin CANLI fiyatlarindan risk/odul hesapla. Her hisse icin: Entry, SL, TP, R:R, Kelly, pozisyon buyuklugu. Risk skoru 4-5 olanlari RED. Korelasyon kontrolu yap. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN H (HESAP) BASLIYOR === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent8 --message "09:30 MATEMATIKSEL DOGRULAMA - Aday hisselerin R:R, Kelly, basari olasiligini hesapla. Monte Carlo simulasyonu. Kabul/RED karari ver. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN A (LIDER) KONSEY RAPORU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent main --message "10:00 KONSEY TOPLANTISI - B,C,D,E,F,H raporlarini topla. 8/8 onay alan hisseleri belirle. Efendiye rapor hazirla: Hisse | Guven | Entry | SL | TP | R:R | Risk. Telegram YOUR_CHAT_ID_HERE'a gonder. workspace/memory/YYYY-MM-DD.md olarak kaydet." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1

echo [%date% %time%] === SABAH TARAMASI TAMAMLANDI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
