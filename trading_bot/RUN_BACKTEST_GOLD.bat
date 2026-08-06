@echo off
title Gold Backtest - 3 Months with $10
color 0E
echo.
echo ========================================
echo    GOLD BACKTEST - 3 MONTHS
echo ========================================
echo.
echo Starting Balance: $10
echo Symbol: XAUUSD (Gold)
echo Period: Last 3 months
echo Timeframe: M5
echo.
echo This will:
echo 1. Fetch 3 months of Gold historical data
echo 2. Train AI model on 70%% of data
echo 3. Test on remaining 30%%
echo 4. Show detailed results
echo.
echo Please wait, this may take 5-10 minutes...
echo.
python backtest.py
echo.
echo ========================================
echo Backtest Complete!
echo ========================================
pause
