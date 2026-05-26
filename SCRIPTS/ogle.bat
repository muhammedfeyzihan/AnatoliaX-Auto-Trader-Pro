@echo off
chcp 65001 >nul
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] AnatoliaX Ogle Guncellemesi basladi >> "%USERPROFILE%\.openclaw\scripts\cron.log"
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

echo [%date% %time%] === CANLI VERI: Bigpara + KAP === >> "%USERPROFILE%\.openclaw\scripts\cron.log"

echo [%date% %time%] === AJAN C (HABER) KAP TARAMASI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent3 --message "12:00 KAP TARAMASI - KAP.gov.tr adresine git, son 4 saatteki ozel durum bildirimlerini, pay alim-satimlarini, araci kurum raporlarini oku. Onemli haber var mi? Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN B (TEKNIK) PIYASA DURUMU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent2 --message "12:00 PIYASA DURUMU - Bigpara canli borsadan BIST 100 anlik deger, gunluk degisim, hacim. En cok artan/azalan 5 hisse. Teknik durum degisti mi? Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN D (RISK) POZISYON KONTROLU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent4 --message "12:00 POZISYON KONTROLU - Acik pozisyonlarin CANLI fiyatlarindan P/L durumunu hesapla. Stop calisti mi? Hedefe yaklasildi mi? Risk degisti mi? Guncelleme oner. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN A (LIDER) OGLE RAPORU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent main --message "12:00 OGLE GUNCELLEMESI - KAP, piyasa ve pozisyon durumlarini topla. Efendiye kisa ozet: BIST durumu, haber ozeti, pozisyonlar, oneriler. Telegram YOUR_CHAT_ID_HERE'a gonder." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1

echo [%date% %time%] === OGLE GUNCELLEMESI TAMAMLANDI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
