@echo off
title AI Trading Bot - Auto Trading Mode
color 0A
echo.
echo ========================================
echo    AI TRADING BOT - AUTO MODE
echo ========================================
echo.
echo Starting the bot...
echo The bot will trade automatically based on AI signals
echo.
echo Press Ctrl+C to stop the bot
echo.
cd trading_bot
python bot_runner.py
pause
