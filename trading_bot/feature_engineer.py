import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange

class FeatureEngineer:
    """Extract technical indicators and features for ML model"""
    
    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to dataframe"""
        df = df.copy()
        
        # Trend Indicators
        df['sma_20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
        df['sma_50'] = SMAIndicator(close=df['close'], window=50).sma_indicator()
        df['ema_12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
        df['ema_26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
        
        # MACD
        macd = MACD(close=df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Momentum Indicators
        df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Volatility Indicators
        bb = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['bb_mid'] = bb.bollinger_mavg()
        df['bb_width'] = (df['bb_high'] - df['bb_low']) / df['bb_mid']
        
        df['atr'] = AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()
        
        # Price Action Features
        df['price_change'] = df['close'].pct_change()
        df['high_low_range'] = (df['high'] - df['low']) / df['close']
        df['close_open_diff'] = (df['close'] - df['open']) / df['open']
        
        # Volume Features
        df['volume_sma'] = df['tick_volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
        
        # Trend Strength
        df['trend_strength'] = (df['close'] - df['sma_50']) / df['sma_50']
        
        # Support/Resistance levels
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        df['distance_to_resistance'] = (df['resistance'] - df['close']) / df['close']
        df['distance_to_support'] = (df['close'] - df['support']) / df['close']
        
        return df
    
    @staticmethod
    def create_labels(df: pd.DataFrame, forward_periods: int = 5, threshold: float = 0.0002) -> pd.DataFrame:
        """Create labels for supervised learning"""
        df = df.copy()
        
        # Future price movement
        df['future_close'] = df['close'].shift(-forward_periods)
        df['future_return'] = (df['future_close'] - df['close']) / df['close']
        
        # Create labels: 1 = BUY, 0 = HOLD, -1 = SELL
        df['label'] = 0
        df.loc[df['future_return'] > threshold, 'label'] = 1
        df.loc[df['future_return'] < -threshold, 'label'] = -1
        
        return df
    
    @staticmethod
    def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare final feature set for model"""
        feature_columns = [
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'macd', 'macd_signal', 'macd_diff',
            'rsi', 'stoch_k', 'stoch_d',
            'bb_high', 'bb_low', 'bb_mid', 'bb_width',
            'atr', 'price_change', 'high_low_range', 'close_open_diff',
            'volume_ratio', 'trend_strength',
            'distance_to_resistance', 'distance_to_support'
        ]
        
        # Drop rows with NaN values
        df = df.dropna(subset=feature_columns + ['label'])
        
        return df[feature_columns + ['label', 'time', 'close']]
