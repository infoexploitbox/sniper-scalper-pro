@echo off
title AI Trading Bot - API Server
color 0B
echo.
echo ========================================
echo    AI TRADING BOT - API SERVER
echo ========================================
echo.
echo Starting API server on http://localhost:6542
echo Your React app can now connect to the bot
echo.
echo Press Ctrl+C to stop the server
echo.
cd trading_bot
python api_server.py
pause
