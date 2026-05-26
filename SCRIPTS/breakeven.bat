@echo off
chcp 65001 >nul
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] AnatoliaX BREAKEVEN KONTROLU (14:00) >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Strateji: K71 Kar Koruma >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] Hedef: Acik pozisyonlarda SL cekme, kar koruma >> "%USERPROFILE%\.openclaw\scripts\cron.log"
echo [%date% %time%] ============================ >> "%USERPROFILE%\.openclaw\scripts\cron.log"

REM Gateway kontrol
curl -s http://127.0.0.1:18789/health >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Gateway kapali, baslatiliyor... >> "%USERPROFILE%\.openclaw\scripts\cron.log"
    start /min "" "%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" gateway run --force
    timeout /t 8 /nobreak >nul
)

echo [%date% %time%] === AJAN D - BREAKEVEN / KAR KORUMA (K71) === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent4 --message "14:00 BREAKEVEN KONTROLU - K71 Kar Koruma Stratejisi. Acik pozisyonlar icin: 1) +%5 kar varsa SL=Entry (breakeven) cek ve %25 kapat (TP1), 2) +%8 kar varsa SL=Entry+%3 cek ve %25 daha kapat (TP2), 3) +%10 kar varsa SL=Entry+%5 cek ve %25 daha kapat (TP3), 4) +%12+ kar varsa Trailing Stop aktif (EMA9 takip). Pozisyon listesi: Hisse | Entry | Anlik | K/Z | Yeni SL | Islem. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN B - TRAILING STOP GUNCELLEME === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent agent2 --message "14:00 TRAILING STOP - TP1 gecilmis pozisyonlar icin: EMA9 seviyelerini kontrol et. Her +%2 kazanc = SL %1 yukari cek. EMA9 altinda kapanis varsa CIK sinyali ver. Pozisyonlar: Hisse | EMA9 | Yeni SL | Durum. Kisa rapor." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1
timeout /t 30 /nobreak >nul

echo [%date% %time%] === AJAN A - BREAKEVEN RAPORU === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
"%USERPROFILE%\AppData\Roaming\npm\openclaw.cmd" agent --agent main --message "14:00 BREAKEVEN RAPORU - D ve B raporlarini birlestir. SL guncellemesi gereken pozisyonlari listele. Efendiye: Bu pozisyonlarda SL cekildi, kar korunuyor. Telegram YOUR_CHAT_ID_HERE'a gonder." >> "%USERPROFILE%\.openclaw\scripts\cron.log" 2>&1

echo [%date% %time%] === BREAKEVEN KONTROLU TAMAMLANDI === >> "%USERPROFILE%\.openclaw\scripts\cron.log"
