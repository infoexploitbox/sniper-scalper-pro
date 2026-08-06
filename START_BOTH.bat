@echo off
title AI Trading Bot - Launcher
color 0E
echo.
echo ========================================
echo    AI TRADING BOT LAUNCHER
echo ========================================
echo.
echo Starting both API Server and Trading Bot...
echo.

REM Start API Server in new window
start "API Server" cmd /k "cd trading_bot && python api_server.py"

REM Wait 3 seconds
timeout /t 3 /nobreak >nul

REM Start Trading Bot in new window
start "Trading Bot" cmd /k "cd trading_bot && python bot_runner.py"

echo.
echo Both services started in separate windows!
echo.
echo - API Server: http://localhost:6542
echo - Trading Bot: Running automatically
echo.
echo Close this window or press any key to exit launcher
pause >nul
