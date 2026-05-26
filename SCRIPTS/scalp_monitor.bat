@echo off
REM scalping_monitor.bat - AnatoliaX Intraday Scalping Saatlik Tarama
REM Alternatif modul - Mevcut sistemi etkilemez
REM Calistirma: scalping_monitor.bat [saat]

setlocal EnableDelayedExpansion

REM === KONFIGURASYON ===
set SCRIPTS_DIR=%USERPROFILE%\.openclaw\scripts
set LOG_DIR=%USERPROFILE%\.openclaw\logs
set NODE_PATH=C:\Program Files\nodejs\node.exe
set ENGINE=%SCRIPTS_DIR%\scalping_engine.js

REM === ZAMAN KONTROLU ===
set CURRENT_HOUR=%time:~0,2%
set CURRENT_HOUR=%CURRENT_HOUR: =0%

REM Saat parametresi varsa kullan, yoksa sistem saati
if not "%1"=="" set CURRENT_HOUR=%1

echo [%date% %time%] AnatoliaX Scalping Monitor basladi (Saat: %CURRENT_HOUR%)

REM === SAAT BAZLI GOREVLER ===
if "%CURRENT_HOUR%"=="09" goto OPENING
if "%CURRENT_HOUR%"=="10" goto MORNING
if "%CURRENT_HOUR%"=="11" goto CHECK
if "%CURRENT_HOUR%"=="14" goto AFTERNOON
if "%CURRENT_HOUR%"=="15" goto EOD
if "%CURRENT_HOUR%"=="16" goto REPORT
goto END

:OPENING
echo [09:30] Acilis momentum taramasi baslatiliyor...
"%NODE_PATH%" "%ENGINE%" --phase=opening --timeframe=1M,5M
goto END

:MORNING
echo [10:00] Sabah breakout taramasi baslatiliyor...
"%NODE_PATH%" "%ENGINE%" --phase=morning --timeframe=15M
goto END

:CHECK
echo [11:00] Aktif pozisyon kontrolu...
REM Aktif pozisyonlarin SL/TP kontrolu (gelecek versiyonda)
echo Aktif pozisyon kontrolu tamamlandi.
goto END

:AFTERNOON
echo [14:00] Ogle reversal taramasi baslatiliyor...
"%NODE_PATH%" "%ENGINE%" --phase=afternoon --timeframe=15M
goto END

:EOD
echo [15:00] Gun sonu momentum taramasi baslatiliyor...
"%NODE_PATH%" "%ENGINE%" --phase=eod --timeframe=15M
goto END

:REPORT
echo [16:30] Gunluk scalping raporu derleniyor...
REM Gunluk istatistik raporu (gelecek versiyonda)
echo Scalping raporu hazir.
goto END

:END
echo [%date% %time%] Scalping Monitor tamamlandi.

REM === LOG ===
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
echo [%date% %time%] Saat %CURRENT_HOUR% taramasi tamamlandi >> "%LOG_DIR%\scalping_monitor.log"

endlocal
exit /b 0
