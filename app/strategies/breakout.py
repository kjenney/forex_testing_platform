from app.strategies.base import BaseStrategy, Signal
import pandas as pd
import numpy as np


class BreakoutStrategy(BaseStrategy):
    """
    Breakout trading strategy on 15-minute charts

    Entry Rules:
    - Identify consolidation via Bollinger Band squeeze
    - Entry on candle close outside range
    - Volume > 120% of 20-bar average
    - Confirmation from ADX or momentum

    Exit Rules:
    - Risk-reward 1:2 to 1:3
    - Stop: 1.5× ATR beyond breakout point
    """

    def __init__(self, client, config=None):
        default_config = {
            'bb_period': 20,
            'bb_std': 2.0,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'volume_threshold': 1.2,  # 120% of average
            'risk_reward_ratio': 2.5,  # Middle of 1:2 to 1:3
            'granularity': 'M15',
            'lookback_candles': 100,
            'squeeze_threshold': 0.02  # Bollinger Band width threshold for squeeze
        }

        if config:
            default_config.update(config)

        super().__init__(client, default_config)

    def analyze(self, instrument: str) -> Signal:
        """
        Analyze instrument and generate breakout signal
        """
        # Fetch candle data
        df = self.get_candles_df(
            instrument,
            self.config['granularity'],
            self.config['lookback_candles']
        )

        if df.empty or len(df) < self.config['bb_period']:
            return Signal('hold', instrument, 0, 0, 0, "Insufficient data")

        # Calculate indicators
        upper_band, middle_band, lower_band = self.calculate_bollinger_bands(
            df,
            self.config['bb_period'],
            self.config['bb_std']
        )
        atr = self.calculate_atr(df, self.config['atr_period'])

        # Calculate Bollinger Band width (for squeeze detection)
        bb_width = (upper_band - lower_band) / middle_band

        # Calculate average volume
        avg_volume = df['volume'].rolling(window=20).mean()

        # Get current values
        current_close = df['close'].iloc[-1]
        prev_close = df['close'].iloc[-2]
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        prev_upper = upper_band.iloc[-2]
        prev_lower = lower_band.iloc[-2]
        current_volume = df['volume'].iloc[-1]
        current_avg_volume = avg_volume.iloc[-1]
        current_bb_width = bb_width.iloc[-1]

        # Check for squeeze (narrow bands)
        is_squeeze = current_bb_width < self.config['squeeze_threshold']

        # Check for high volume
        volume_confirmed = current_volume > (current_avg_volume * self.config['volume_threshold'])

        # Get current bid/ask
        prices = self.get_current_price(instrument)
        current_bid = prices['bid']
        current_ask = prices['ask']

        pip_value = 0.0001 if 'JPY' not in instrument else 0.01

        # Bullish breakout (price breaks above upper band)
        if (prev_close <= prev_upper and current_close > current_upper and
            volume_confirmed):

            # Calculate stop loss
            stop_loss_pips = (atr / pip_value) * self.config['atr_multiplier']

            # Get account balance
            account_info = self.client.get_account_summary()
            account_balance = float(account_info['account']['balance'])

            units = self.calculate_position_size(
                account_balance,
                1.0,
                stop_loss_pips,
                pip_value
            )

            stop_loss = current_ask - (stop_loss_pips * pip_value)
            take_profit_pips = stop_loss_pips * self.config['risk_reward_ratio']
            take_profit = current_ask + (take_profit_pips * pip_value)

            reason = f"Bullish breakout: Price broke upper BB, volume {current_volume/current_avg_volume:.1f}x avg"
            if is_squeeze:
                reason += ", squeeze detected"

            return Signal('buy', instrument, units, stop_loss, take_profit, reason)

        # Bearish breakout (price breaks below lower band)
        elif (prev_close >= prev_lower and current_close < current_lower and
              volume_confirmed):

            stop_loss_pips = (atr / pip_value) * self.config['atr_multiplier']

            account_info = self.client.get_account_summary()
            account_balance = float(account_info['account']['balance'])

            units = self.calculate_position_size(
                account_balance,
                1.0,
                stop_loss_pips,
                pip_value
            )

            # For sell, units should be negative
            units = -units

            stop_loss = current_bid + (stop_loss_pips * pip_value)
            take_profit_pips = stop_loss_pips * self.config['risk_reward_ratio']
            take_profit = current_bid - (take_profit_pips * pip_value)

            reason = f"Bearish breakout: Price broke lower BB, volume {current_volume/current_avg_volume:.1f}x avg"
            if is_squeeze:
                reason += ", squeeze detected"

            return Signal('sell', instrument, units, stop_loss, take_profit, reason)

        return Signal('hold', instrument, 0, 0, 0, "No breakout setup")
