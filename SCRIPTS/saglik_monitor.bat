@echo off
chcp 65001 >nul
:: AnatoliaX SAGLIK MONITORU - Self-Healing
:: Her 60 saniyede gateway, browser, webhook server kontrol eder
:: Calistirma: saglik_monitor.bat (arka planda)

set LOG=%USERPROFILE%\.openclaw\scripts\saglik.log
set GATEWAY_URL=http://127.0.0.1:18789/health
set BROWSER_URL=http://127.0.0.1:18800/json/version
set WEBHOOK_URL=http://127.0.0.1:3001/
set SIGNALR_PID_FILE=%USERPROFILE%\.openclaw\scripts\signalr.pid
set OPENCLAW="%APPDATA%\npm\openclaw.cmd"

:loop
echo [%date% %time%] Kontrol basladi >> %LOG%

:: 1. Gateway Kontrol
curl -s %GATEWAY_URL% >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Gateway KAPALI - Yeniden baslatiliyor... >> %LOG%
    taskkill //IM node.exe //F >nul 2>&1
    timeout //t 2 //nobreak >nul
    start /min "" %OPENCLAW% gateway run --force
    timeout //t 8 //nobreak >nul
    echo [%date% %time%] Gateway baslatildi >> %LOG%
) else (
    echo [%date% %time%] Gateway OK >> %LOG%
)

:: 2. Browser Kontrol
curl -s %BROWSER_URL% >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Browser KAPALI - Yeniden baslatiliyor... >> %LOG%
    %OPENCLAW% browser --browser-profile openclaw start >nul 2>&1
    timeout //t 8 //nobreak >nul
    echo [%date% %time%] Browser baslatildi >> %LOG%
) else (
    echo [%date% %time%] Browser OK >> %LOG%
)

:: 3. Webhook Server Kontrol
curl -s %WEBHOOK_URL% >nul
if %errorlevel% neq 0 (
    echo [%date% %time%] Webhook Server KAPALI - Yeniden baslatiliyor... >> %LOG%
    taskkill //FI "WINDOWTITLE eq webhook*" //F >nul 2>&1
    start /min "" node "%USERPROFILE%\.openclaw\scripts\webhook_server.js"
    timeout //t 3 //nobreak >nul
    echo [%date% %time%] Webhook Server baslatildi >> %LOG%
) else (
    echo [%date% %time%] Webhook Server OK >> %LOG%
)

:: 4. Telegram Bot Kontrol (PID kontrolu)
:: PowerShell ile kontrol, varsa OK, yoksa baslat
powershell -Command "if (Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object {$_.CommandLine -like '*telegram_listener*'}) { exit 0 } else { exit 1 }"
if %errorlevel% neq 0 (
    echo [%date% %time%] Telegram Bot KAPALI - Yeniden baslatiliyor... >> %LOG%
    start /min "" powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File "%USERPROFILE%\.openclaw\scripts\telegram_listener.ps1"
    echo [%date% %time%] Telegram Bot baslatildi >> %LOG%
) else (
    echo [%date% %time%] Telegram Bot OK >> %LOG%
)

:: 5. SignalR Tick Akisi Kontrol
powershell -Command "$pidFile='%SIGNALR_PID_FILE%'; if (Test-Path $pidFile) { $pid=Get-Content $pidFile; try { $p=Get-Process -Id $pid -ErrorAction Stop; if ($p.ProcessName -eq 'node') { exit 0 } else { exit 1 } } catch { exit 1 } } else { exit 1 }"
if %errorlevel% neq 0 (
    echo [%date% %time%] SignalR KAPALI - Yeniden baslatiliyor... >> %LOG%
    start /min "" cmd /c "cd /d %USERPROFILE%\.openclaw & node scripts\biquote_signalr.js > nul 2>&1 & echo !errorlevel! > %SIGNALR_PID_FILE%"
    timeout //t 3 //nobreak > nul
    echo [%date% %time%] SignalR baslatildi >> %LOG%
) else (
    echo [%date% %time%] SignalR OK >> %LOG%
)

echo [%date% %time%] --- >> %LOG%
timeout //t 60 //nobreak >nul
goto loop
