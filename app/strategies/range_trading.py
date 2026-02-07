from app.strategies.base import BaseStrategy, Signal
import pandas as pd
import numpy as np


class RangeTradingStrategy(BaseStrategy):
    """
    Range trading strategy on 1-hour charts

    Entry Rules:
    - Identify horizontal support/resistance levels
    - Buy near support when RSI < 30 (oversold)
    - Sell near resistance when RSI > 70 (overbought)
    - Price bounces at boundaries (candlestick confirmation)

    Exit Rules:
    - Target: Opposite boundary or 1:1 risk-reward
    - Stop: Beyond boundary with 5-pip buffer
    """

    def __init__(self, client, config=None):
        default_config = {
            'rsi_period': 14,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'lookback_period': 50,  # For identifying support/resistance
            'boundary_buffer_pips': 5,
            'granularity': 'H1',
            'lookback_candles': 100,
            'range_min_touches': 2  # Minimum touches to confirm level
        }

        if config:
            default_config.update(config)

        super().__init__(client, default_config)

    def identify_support_resistance(self, df: pd.DataFrame) -> tuple:
        """
        Identify support and resistance levels using recent swing highs/lows

        Returns:
            Tuple of (support_level, resistance_level)
        """
        # Calculate local highs and lows
        lookback = self.config['lookback_period']
        recent_df = df.tail(lookback)

        # Find swing highs (local maxima)
        highs = recent_df['high'].rolling(window=3, center=True).max()
        swing_highs = recent_df[recent_df['high'] == highs]['high'].values

        # Find swing lows (local minima)
        lows = recent_df['low'].rolling(window=3, center=True).min()
        swing_lows = recent_df[recent_df['low'] == lows]['low'].values

        if len(swing_highs) == 0 or len(swing_lows) == 0:
            return None, None

        # Calculate most common resistance (cluster of highs)
        resistance = np.median(swing_highs[-5:]) if len(swing_highs) >= 5 else max(swing_highs)

        # Calculate most common support (cluster of lows)
        support = np.median(swing_lows[-5:]) if len(swing_lows) >= 5 else min(swing_lows)

        return support, resistance

    def analyze(self, instrument: str) -> Signal:
        """
        Analyze instrument and generate range trading signal
        """
        # Fetch candle data
        df = self.get_candles_df(
            instrument,
            self.config['granularity'],
            self.config['lookback_candles']
        )

        if df.empty or len(df) < self.config['lookback_period']:
            return Signal('hold', instrument, 0, 0, 0, "Insufficient data")

        # Calculate indicators
        rsi = self.calculate_rsi(df, self.config['rsi_period'])

        # Identify support and resistance
        support, resistance = self.identify_support_resistance(df)

        if support is None or resistance is None:
            return Signal('hold', instrument, 0, 0, 0, "Cannot identify range")

        # Check if we're in a valid range (not too narrow)
        pip_value = 0.0001 if 'JPY' not in instrument else 0.01
        range_pips = (resistance - support) / pip_value

        if range_pips < 20:  # Minimum 20 pips for meaningful range
            return Signal('hold', instrument, 0, 0, 0, f"Range too narrow: {range_pips:.1f} pips")

        # Get current values
        current_close = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Get current bid/ask
        prices = self.get_current_price(instrument)
        current_bid = prices['bid']
        current_ask = prices['ask']

        # Calculate distance to boundaries
        distance_to_support = abs(current_close - support) / pip_value
        distance_to_resistance = abs(current_close - resistance) / pip_value

        # Buy signal: Near support + oversold RSI
        if distance_to_support < 10 and current_rsi < self.config['rsi_oversold']:

            # Get account balance
            account_info = self.client.get_account_summary()
            account_balance = float(account_info['account']['balance'])

            # Stop loss below support with buffer
            stop_loss = support - (self.config['boundary_buffer_pips'] * pip_value)
            stop_loss_pips = (current_ask - stop_loss) / pip_value

            units = self.calculate_position_size(
                account_balance,
                1.0,
                stop_loss_pips,
                pip_value
            )

            # Target: resistance or 1:1 risk-reward, whichever is closer
            target_at_resistance = resistance
            target_at_rr = current_ask + (stop_loss_pips * pip_value)
            take_profit = min(target_at_resistance, target_at_rr)

            reason = f"Range buy at support: RSI={current_rsi:.1f}, {distance_to_support:.1f} pips from support, range={range_pips:.1f} pips"

            return Signal('buy', instrument, units, stop_loss, take_profit, reason)

        # Sell signal: Near resistance + overbought RSI
        elif distance_to_resistance < 10 and current_rsi > self.config['rsi_overbought']:

            account_info = self.client.get_account_summary()
            account_balance = float(account_info['account']['balance'])

            # Stop loss above resistance with buffer
            stop_loss = resistance + (self.config['boundary_buffer_pips'] * pip_value)
            stop_loss_pips = (stop_loss - current_bid) / pip_value

            units = self.calculate_position_size(
                account_balance,
                1.0,
                stop_loss_pips,
                pip_value
            )

            # For sell, units should be negative
            units = -units

            # Target: support or 1:1 risk-reward, whichever is closer
            target_at_support = support
            target_at_rr = current_bid - (stop_loss_pips * pip_value)
            take_profit = max(target_at_support, target_at_rr)

            reason = f"Range sell at resistance: RSI={current_rsi:.1f}, {distance_to_resistance:.1f} pips from resistance, range={range_pips:.1f} pips"

            return Signal('sell', instrument, units, stop_loss, take_profit, reason)

        return Signal('hold', instrument, 0, 0, 0, f"No range setup (RSI={current_rsi:.1f}, dist to support={distance_to_support:.1f}, dist to resistance={distance_to_resistance:.1f})")
