@echo off
chcp 65001 >nul
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] AnatoliaX GECE STRATEJISI basladi >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Strateji: Aksam al - Sabah %6+ ACMAKTAN EMIN HISSELER >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Kural: SADECE %6+ gap-up olasiligi %70+ olan hisseler >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Eger %6+ acmazsa sabah en yuksek fiyattan sat (minimum zarar) >> "%USERPROFILE%\.openclaw\scripts\cron.log"
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

echo [%date% %time%] === CANLI VERI: Bigpara (Gun Sonu) === >> "%USERPROFILE%\.openclaw\scripts\cron.log"

echo [%date% %time%] === AJAN B (TEKNIK) GECE TARAMASI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent2 --message "17:30 GECE STRATEJISI - Bigpara canli borsadan 30+ hisse arasinda YARIN SABAH %6+ GAP-UP ACMASI EN YUKSEK OLASILIKLI hisseleri bul. Kriterler: 1) Gunluk degisim > +%4.5 (cok guclu), 2) Son 2 saatte pozitif momentum artisi, 3) Hacim gunluk ortalamanin 2.5x uzerinde, 4) Fiyat gunluk en yuksek seviyeye %2 icinde kapaniyor, 5) BB ust bandini kirmis ve uzerinde tutunuyor, 6) Son 3 gunluk trend yukari, 7) Sektor lideri. 10 aday sec ama SADECE %6+ gap-up olasiligi %70+ olanlari listele. Hisse | Fiyat | Gunluk % | Hacim | Gap-Up %6+ Olasiligi | Guven. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN C (HABER) KAPANIS ONCESI HABER === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent3 --message "17:30 KAPANIS ONCESI HABER - KAP.gov.tr'den son 2 saatteki aciklamalari kontrol et. Aday hisselerle ilgili olumlu/olumsuz haber var mi? Haber risk skoru (1-5). Olumlu haberli ve riski <3 olan hisseleri isaretle. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN F (DEDEKTIF) KAPANIS MANIPULASYONU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent6 --message "17:30 KAPANIS ANALIZI - Aday hisselerde gun sonu manipulasyon var mi? Fake kapanis, asiri hacimli son dakika alimi, spike. MiroFish skoru >70 olanlari gec. Gercek momentum tasiyanlari isaretle. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN D (RISK) GECE RISK ANALIZI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent4 --message "17:30 GECE RISK ANALIZI - Aday hisseler icin overnight risk hesapla. Kriterler: 1) Gecelik stop-loss (gunluk low'un %2 altinda), 2) Hedef: Sabah acilista %6+ gap-up bekleniyor, 3) Eger %6+ acmazsa sabah en yuksek fiyattan sat, 4) Pozisyon buyuklugu max %2, 5) VaR gunluk %1. Overnight gap-down olasiligi %20 altinda olanlari isaretle. SADECE yuksek guvenlileri gec. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN H (HESAP) GAP-UP OLASILIGI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent8 --message "17:30 GAP-UP ANALIZI - Aday hisselerin yarin sabah icin %6+ gap-up olasiligini matematiksel olarak hesapla. Formul: Gunluk momentum * 0.35 + hacim gucu * 0.25 + kapanis gucu * 0.20 + sektor trendi * 0.10 + haber etkisi * 0.10. SADECE hesaplanan olasilik %70+ olanlari listele. Overnight beklenen getiri hesapla. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN E (MAKRO) GECE PIYASASI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent5 --message "17:30 MAKRO GECE DURUMU - ABD vadeli endeksler (gece seansi), USD/TRY, altin durumu. Global piyasa gece boyu ne bekliyor? BIST yarinki acilis icin olumlu/olumsuz sinyal var mi? Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN A (LIDER) GECE RAPORU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent main --message "17:30 GECE STRATEJISI RAPORU - Tum ajan raporlarini topla. SADECE 8/8 onay alan ve %6+ gap-up olasiligi %70+ olan hisseleri listele. Rapor formati: Hisse | Fiyat | Gunluk % | %6+ Gap-Up Olasiligi | SL (Gun Low) | Beklenen Sabah Acilis | Guven | Pozisyon %. Telegram YOUR_CHAT_ID_HERE'a gonder. Efendiye: Bu hisseler YARIN SABAH %6+ GAP-UP ACMASI EN YUKSEK OLASILIKLI hisselerdir. Aksam al, sabah %6+ acinca sat. Eger %6+ acmazsa sabah ilk 5 dakikada yuksek fiyattan sat." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1

echo [%date% %time%] === GECE STRATEJISI TAMAMLANDI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
