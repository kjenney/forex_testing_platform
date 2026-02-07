from app.strategies.base import BaseStrategy, Signal
import pandas as pd


class ScalpingStrategy(BaseStrategy):
    """
    Scalping strategy targeting 5-10 pips per trade on 5-minute charts

    Entry Rules:
    - Price crosses above 20-EMA
    - RSI(9) > 50
    - Price is above 50-EMA (trend filter)

    Exit Rules:
    - Take profit: 5-10 pips
    - Stop loss: 1.5× ATR
    """

    def __init__(self, client, config=None):
        default_config = {
            'ema_fast': 20,
            'ema_slow': 50,
            'rsi_period': 9,
            'atr_period': 14,
            'atr_multiplier': 1.5,
            'target_pips': 7,  # Middle of 5-10 range
            'granularity': 'M5',
            'lookback_candles': 100
        }

        if config:
            default_config.update(config)

        super().__init__(client, default_config)

    def analyze(self, instrument: str) -> Signal:
        """
        Analyze instrument and generate scalping signal
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
        rsi = self.calculate_rsi(df, self.config['rsi_period'])
        atr = self.calculate_atr(df, self.config['atr_period'])

        # Get current values
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2]
        current_ema_20 = ema_20.iloc[-1]
        prev_ema_20 = ema_20.iloc[-2]
        current_ema_50 = ema_50.iloc[-1]
        current_rsi = rsi.iloc[-1]

        # Get current bid/ask
        prices = self.get_current_price(instrument)
        current_bid = prices['bid']
        current_ask = prices['ask']

        # Check for bullish scalping signal
        if (prev_price <= prev_ema_20 and current_price > current_ema_20 and
            current_rsi > 50 and current_price > current_ema_50):

            # Calculate position sizing
            pip_value = 0.0001 if 'JPY' not in instrument else 0.01
            stop_loss_pips = (atr / pip_value) * self.config['atr_multiplier']

            # Get account balance for position sizing
            account_info = self.client.get_account_summary()
            account_balance = float(account_info['account']['balance'])

            units = self.calculate_position_size(
                account_balance,
                1.0,  # 1% risk
                stop_loss_pips,
                pip_value
            )

            # Calculate stop loss and take profit
            stop_loss = current_ask - (stop_loss_pips * pip_value)
            take_profit = current_ask + (self.config['target_pips'] * pip_value)

            reason = f"Bullish scalp: Price crossed 20-EMA, RSI={current_rsi:.1f}, above 50-EMA"

            return Signal('buy', instrument, units, stop_loss, take_profit, reason)

        # Check for bearish scalping signal
        elif (prev_price >= prev_ema_20 and current_price < current_ema_20 and
              current_rsi < 50 and current_price < current_ema_50):

            pip_value = 0.0001 if 'JPY' not in instrument else 0.01
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
            take_profit = current_bid - (self.config['target_pips'] * pip_value)

            reason = f"Bearish scalp: Price crossed below 20-EMA, RSI={current_rsi:.1f}, below 50-EMA"

            return Signal('sell', instrument, units, stop_loss, take_profit, reason)

        return Signal('hold', instrument, 0, 0, 0, "No scalping setup")
