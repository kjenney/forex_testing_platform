from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
import numpy as np


class Signal:
    """Trading signal representation"""

    def __init__(self, action: str, instrument: str, units: float, stop_loss: float, take_profit: float, reason: str = ""):
        self.action = action  # 'buy', 'sell', or 'hold'
        self.instrument = instrument
        self.units = units
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason

    def to_dict(self):
        return {
            'action': self.action,
            'instrument': self.instrument,
            'units': self.units,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'reason': self.reason
        }


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies"""

    def __init__(self, client, config: Dict):
        self.client = client
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def analyze(self, instrument: str) -> Signal:
        """
        Analyze market data and return trading signal

        Args:
            instrument: Instrument to analyze (e.g., 'EUR_USD')

        Returns:
            Signal object with action, units, stop_loss, take_profit
        """
        pass

    def get_candles_df(self, instrument: str, granularity: str = 'M5', count: int = 100) -> pd.DataFrame:
        """
        Fetch candle data and convert to pandas DataFrame

        Args:
            instrument: Instrument name
            granularity: Candle granularity
            count: Number of candles

        Returns:
            DataFrame with OHLC data
        """
        response = self.client.get_candles(instrument, granularity, count)
        candles = response.get('candles', [])

        data = []
        for candle in candles:
            if candle.get('complete', False):
                mid = candle['mid']
                data.append({
                    'time': pd.to_datetime(candle['time']),
                    'open': float(mid['o']),
                    'high': float(mid['h']),
                    'low': float(mid['l']),
                    'close': float(mid['c']),
                    'volume': int(candle['volume'])
                })

        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('time', inplace=True)

        return df

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        stop_loss_pips: float,
        pip_value: float = 1.0
    ) -> float:
        """
        Calculate position size using 1% risk rule

        Args:
            account_balance: Current account balance
            risk_percent: Risk percentage (e.g., 1.0 for 1%)
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value of 1 pip for the instrument

        Returns:
            Position size in units
        """
        risk_amount = account_balance * (risk_percent / 100)
        position_size = risk_amount / (stop_loss_pips * pip_value)
        return abs(position_size)

    def calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """
        Calculate Average True Range (ATR)

        Args:
            df: DataFrame with OHLC data
            period: ATR period

        Returns:
            Current ATR value
        """
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr.iloc[-1] if not atr.empty else 0.0

    def calculate_ema(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()

    def calculate_sma(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return df['close'].rolling(window=period).mean()

    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> tuple:
        """
        Calculate Bollinger Bands

        Returns:
            Tuple of (upper_band, middle_band, lower_band)
        """
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()

        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)

        return upper_band, sma, lower_band

    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """
        Calculate MACD

        Returns:
            Tuple of (macd_line, signal_line, histogram)
        """
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def get_current_price(self, instrument: str) -> Dict[str, float]:
        """
        Get current bid/ask prices

        Returns:
            Dict with 'bid' and 'ask' prices
        """
        response = self.client.get_prices([instrument])
        prices = response.get('prices', [])

        if prices:
            price_data = prices[0]
            return {
                'bid': float(price_data['bids'][0]['price']),
                'ask': float(price_data['asks'][0]['price'])
            }

        return {'bid': 0.0, 'ask': 0.0}

    def execute_trade(self, signal: Signal) -> Optional[Dict]:
        """
        Execute trade based on signal

        Args:
            signal: Signal object with trade details

        Returns:
            Response from API or None if no action
        """
        if signal.action == 'hold':
            return None

        try:
            response = self.client.create_market_order(
                instrument=signal.instrument,
                units=signal.units,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit
            )
            return response
        except Exception as e:
            print(f"Trade execution failed: {str(e)}")
            return None
