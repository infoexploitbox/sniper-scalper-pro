@echo off
title AI Trading Bot - Autonomous Engine
color 0A
echo.
echo ============================================================
echo    SNIPER SCALPER PRO — AI AUTONOMOUS TRADING BOT
echo ============================================================
echo.
echo Starting live trading loop for pairs:
echo EURUSDm, GBPUSDm, USDJPYm, AUDUSDm, USDCADm, XAUUSDm, BTCUSDm, etc.
echo.
echo Features:
echo   - AI Ensemble Signals (XGBoost + LightGBM + Random Forest)
echo   - Auto-Breakeven Stop Loss Protection
echo   - ATR Trailing Stops (Chandelier Exit)
echo   - 5.5%% Risk Management & Micro-Account Sizing
echo   - Continuous Self-Learning Loop
echo.
echo Press Ctrl+C to stop the bot safely.
echo.
cd trading_bot
python bot_runner.py
pause
