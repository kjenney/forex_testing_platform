from app.strategies.base import BaseStrategy, Signal
import pandas as pd
import numpy as np


class TrendFollowingStrategy(BaseStrategy):
    """
    Trend following strategy on 15-minute and 1-hour charts

    Entry Rules:
    - Trend filter: 20-EMA above 50-EMA (bullish), below (bearish)
    - Entry on pullback to 20-EMA or Fibonacci 38.2-61.8% retracement
    - Confirmation: Price bounces off EMA with momentum

    Exit Rules:
    - Trailing stop: 1.5× ATR
    - Target: 1.5:1 risk-reward minimum
    - Exit if trend breaks (EMA crossover)
    """

    def __init__(self, client, config=None):
        default_config = {
            'ema_fast': 20,
            'ema_slow': 50,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'risk_reward_ratio': 1.5,
            'fib_min': 0.382,
            'fib_max': 0.618,
            'granularity': 'M15',
            'lookback_candles': 100,
            'min_trend_strength': 10  # Minimum pips between EMAs for valid trend
        }

        if config:
            default_config.update(config)

        super().__init__(client, default_config)

    def identify_swing_points(self, df: pd.DataFrame, lookback: int = 20) -> tuple:
        """
        Identify recent swing high and low for Fibonacci retracement

        Returns:
            Tuple of (swing_high, swing_low)
        """
        recent_df = df.tail(lookback)

        swing_high = recent_df['high'].max()
        swing_low = recent_df['low'].min()

        return swing_high, swing_low

    def calculate_fibonacci_levels(self, swing_high: float, swing_low: float) -> dict:
        """
        Calculate Fibonacci retracement levels

        Returns:
            Dict with Fibonacci levels
        """
        diff = swing_high - swing_low

        return {
            '0.0': swing_low,
            '0.236': swing_low + (0.236 * diff),
            '0.382': swing_low + (0.382 * diff),
            '0.5': swing_low + (0.5 * diff),
            '0.618': swing_low + (0.618 * diff),
            '0.786': swing_low + (0.786 * diff),
            '1.0': swing_high
        }

    def analyze(self, instrument: str) -> Signal:
        """
        Analyze instrument and generate trend following signal
        """
        # Fetch candle data
        df = self.get_candles_df(
            instrument,
            self.config['granularity'],
            self.config['lookback_candles']
        )

        if df.empty or len(df) < self.config['ema_slow']:
            return Signal('hold', instrument, 0, 0, 0, "Insufficient data")

        # Calculate indicators
        ema_20 = self.calculate_ema(df, self.config['ema_fast'])
        ema_50 = self.calculate_ema(df, self.config['ema_slow'])
        atr = self.calculate_atr(df, self.config['atr_period'])

        # Get current values
        current_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        current_ema_20 = ema_20.iloc[-1]
        current_ema_50 = ema_50.iloc[-1]
        prev_ema_20 = ema_20.iloc[-2]

        # Get current bid/ask
        prices = self.get_current_price(instrument)
        current_bid = prices['bid']
        current_ask = prices['ask']

        pip_value = 0.0001 if 'JPY' not in instrument else 0.01

        # Determine trend direction
        is_uptrend = current_ema_20 > current_ema_50
        is_downtrend = current_ema_20 < current_ema_50

        # Check trend strength
        ema_distance_pips = abs(current_ema_20 - current_ema_50) / pip_value

        if ema_distance_pips < self.config['min_trend_strength']:
            return Signal('hold', instrument, 0, 0, 0, f"Weak trend: EMAs only {ema_distance_pips:.1f} pips apart")

        # Identify swing points for Fibonacci
        swing_high, swing_low = self.identify_swing_points(df, 20)

        # Check distance from current price to EMA (looking for pullback)
        distance_to_ema_20 = abs(current_close - current_ema_20) / pip_value

        # Bullish trend following setup
        if is_uptrend:
            # Calculate Fibonacci levels (for uptrend, we retraced from high to low)
            fib_levels = self.calculate_fibonacci_levels(swing_high, swing_low)
            fib_382 = fib_levels['0.382']
            fib_618 = fib_levels['0.618']

            # Check if price is pulling back to EMA or in Fib zone
            is_at_ema = distance_to_ema_20 < 5 and current_close >= current_ema_20
            is_in_fib_zone = fib_382 <= current_close <= fib_618

            # Check for bounce (previous candle touched/crossed EMA, current is above)
            bounced_from_ema = prev_close <= prev_ema_20 and current_close > current_ema_20

            if (bounced_from_ema or is_at_ema) and current_close > current_ema_20:

                # Get account balance
                account_info = self.client.get_account_summary()
                account_balance = float(account_info['account']['balance'])

                # Calculate stop loss
                stop_loss_pips = (atr / pip_value) * self.config['atr_multiplier']
                stop_loss = current_ask - (stop_loss_pips * pip_value)

                # Ensure stop is below EMA for trend protection
                stop_loss = min(stop_loss, current_ema_20 - (5 * pip_value))

                # Recalculate stop_loss_pips based on actual stop
                stop_loss_pips = (current_ask - stop_loss) / pip_value

                units = self.calculate_position_size(
                    account_balance,
                    1.0,
                    stop_loss_pips,
                    pip_value
                )

                # Calculate take profit
                take_profit_pips = stop_loss_pips * self.config['risk_reward_ratio']
                take_profit = current_ask + (take_profit_pips * pip_value)

                reason = f"Bullish trend: Pullback entry, EMA20 {ema_distance_pips:.1f} pips above EMA50"
                if is_in_fib_zone:
                    reason += ", in Fib golden zone"

                return Signal('buy', instrument, units, stop_loss, take_profit, reason)

        # Bearish trend following setup
        elif is_downtrend:
            # Calculate Fibonacci levels (for downtrend, swing high is resistance)
            fib_levels = self.calculate_fibonacci_levels(swing_high, swing_low)
            fib_382 = fib_levels['0.382']
            fib_618 = fib_levels['0.618']

            # Check if price is pulling back to EMA or in Fib zone
            is_at_ema = distance_to_ema_20 < 5 and current_close <= current_ema_20
            is_in_fib_zone = fib_382 <= current_close <= fib_618

            # Check for bounce (previous candle touched/crossed EMA, current is below)
            bounced_from_ema = prev_close >= prev_ema_20 and current_close < current_ema_20

            if (bounced_from_ema or is_at_ema) and current_close < current_ema_20:

                account_info = self.client.get_account_summary()
                account_balance = float(account_info['account']['balance'])

                # Calculate stop loss
                stop_loss_pips = (atr / pip_value) * self.config['atr_multiplier']
                stop_loss = current_bid + (stop_loss_pips * pip_value)

                # Ensure stop is above EMA for trend protection
                stop_loss = max(stop_loss, current_ema_20 + (5 * pip_value))

                # Recalculate stop_loss_pips based on actual stop
                stop_loss_pips = (stop_loss - current_bid) / pip_value

                units = self.calculate_position_size(
                    account_balance,
                    1.0,
                    stop_loss_pips,
                    pip_value
                )

                # For sell, units should be negative
                units = -units

                # Calculate take profit
                take_profit_pips = stop_loss_pips * self.config['risk_reward_ratio']
                take_profit = current_bid - (take_profit_pips * pip_value)

                reason = f"Bearish trend: Pullback entry, EMA20 {ema_distance_pips:.1f} pips below EMA50"
                if is_in_fib_zone:
                    reason += ", in Fib golden zone"

                return Signal('sell', instrument, units, stop_loss, take_profit, reason)

        return Signal('hold', instrument, 0, 0, 0, "No trend following setup")
