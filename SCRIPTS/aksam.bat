@echo off
chcp 65001 >nul
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] AnatoliaX Aksam Kapanis Raporu basladi >> "%USERPROFILE%\.openclaw\scripts\cron.log"
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

echo [%date% %time%] === CANLI KAPANIS VERILERI: Bigpara === >> "%USERPROFILE%\.openclaw\scripts\cron.log"

echo [%date% %time%] === AJAN B (TEKNIK) GUN SONU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent2 --message "18:00 GUN SONU TEKNIK ANALIZI - Bigpara canli borsadan BIST 100 kapanis degeri, gunluk degisim%, hacim, en cok artan/azalanlar. Gunluk mum formasyonu ne? Destek/direnc durumu? Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN C (HABER) GUN SONU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent3 --message "18:00 GUN SONU HABERLERI - KAP.gov.tr ve bigpara'dan gun boyu olan biten: KAP aciklamalari, araci kurum hedef fiyat guncellemeleri. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN D (RISK) POZISYON DEGERLENDIRMESI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent4 --message "18:00 POZISYON DEGERLENDIRMESI - Tum acik pozisyonlarin CANLI kapanis fiyatlarindan gunluk P/L hesapla. Haftalik P/L. Stop calisan var mi? Hedefe ulasan? Risk guncellemesi. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN F (DEDEKTIF) ANOMALI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent6 --message "18:00 ANOMALI ANALIZI - Gun icindeki hacimli ve ani hareketleri incele. Spekulatif hisselerde abnormal hareket var mi? Likidite avi? Gunluk anomali raporu. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN G (HAFIZA) HATA/DERS === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent7 --message "18:00 HATA ANALIZI - Bugun onerilen hisseler ne yapti? Beklenen vs gerceklesen. Hata nedenleri. Ogrenilecek dersler. MEMORY.md ve gunluk dosya guncelle. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN A (LIDER) AKSAM RAPORU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent main --message "18:00 AKSAM KAPANIS RAPORU - Tum ajan raporlarini topla. Gun sonu degerlendirme: BIST kapanis, acik pozisyonlar, P/L, hedeflere ulasma orani, hatalar, dersler. MEMORY.md ve gunluk dosya guncelle. Yarin icin risk skoru ve strateji. Efendiye rapor sun ve Telegram YOUR_CHAT_ID_HERE'a gonder." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1

echo [%date% %time%] === AKSAM KAPANIS RAPORU TAMAMLANDI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
