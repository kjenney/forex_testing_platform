import requests
from typing import Dict, List, Optional
from datetime import datetime


class ForexClient:
    """
    Wrapper for GAIN Capital API (used by Forex.com)
    API Documentation: https://docs.labs.gaincapital.com/
    """

    BASE_URL = 'https://ciapi.cityindex.com/TradingAPI'

    def __init__(self, username: str, password: str, appkey: str):
        self.username = username
        self.password = password
        self.appkey = appkey
        self.session = requests.Session()
        self.session_token = None
        self.trading_account_id = None

        # Authenticate and get session
        self._authenticate()

    def _authenticate(self):
        """Authenticate with GAIN Capital API and get session token"""
        url = f"{self.BASE_URL}/session"

        auth_data = {
            "UserName": self.username,
            "Password": self.password,
            "AppKey": self.appkey
        }

        try:
            response = self.session.post(url, json=auth_data, timeout=10)
            response.raise_for_status()
            data = response.json()

            self.session_token = data.get('Session')

            # Set session headers
            self.session.headers.update({
                'Content-Type': 'application/json',
                'UserName': self.username,
                'Session': self.session_token
            })

            # Get trading account ID
            self._get_trading_account_id()

        except requests.exceptions.RequestException as e:
            raise Exception(f"Authentication failed: {str(e)}")

    def _get_trading_account_id(self):
        """Get the trading account ID from user account info"""
        try:
            response = self._request('GET', '/UserAccount/ClientAndTradingAccount')

            # Extract first trading account ID
            trading_accounts = response.get('TradingAccounts', [])
            if trading_accounts:
                self.trading_account_id = trading_accounts[0].get('TradingAccountId')
            else:
                raise Exception("No trading accounts found")

        except Exception as e:
            raise Exception(f"Failed to get trading account ID: {str(e)}")

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict:
        """Make HTTP request to GAIN Capital API"""
        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            # Try to get error details from response
            error_msg = str(e)
            if hasattr(e.response, 'text'):
                error_msg = f"{error_msg} - Response: {e.response.text}"
            raise Exception(f"API request failed: {error_msg}")

    def get_account(self) -> Dict:
        """Fetch account details including balance, equity, margin"""
        return self.get_account_summary()

    def get_account_summary(self) -> Dict:
        """Fetch account summary with balance and margin info"""
        try:
            # Get margin info which includes balance
            margin_response = self._request('GET', '/margin/ClientAccountMargin')

            # Get account info
            account_response = self._request('GET', '/UserAccount/ClientAndTradingAccount')

            # Get open positions for unrealized P&L
            positions_response = self.get_open_positions()

            # Calculate unrealized P&L from positions
            unrealized_pl = 0.0
            open_count = 0

            positions = positions_response.get('OpenPositions', [])
            for pos in positions:
                unrealized_pl += float(pos.get('CurrentProfit', 0))
                open_count += 1

            # Extract balance information
            cash = float(margin_response.get('Cash', 0))
            margin_used = float(margin_response.get('Margin', 0))

            # GAIN Capital API structure - map to our expected format
            return {
                'account': {
                    'id': str(self.trading_account_id),
                    'balance': cash,
                    'NAV': cash + unrealized_pl,  # Net Asset Value (equity)
                    'marginUsed': margin_used,
                    'marginAvailable': cash - margin_used,
                    'openTradeCount': open_count,
                    'unrealizedPL': unrealized_pl,
                    'pl': float(margin_response.get('ProfitLoss', 0))
                }
            }

        except Exception as e:
            raise Exception(f"Failed to get account summary: {str(e)}")

    def get_prices(self, instruments: List[str]) -> Dict:
        """
        Get current bid/ask prices for instruments

        Args:
            instruments: List of instrument names (e.g., ['EURUSD', 'GBPUSD'])

        Note: GAIN Capital uses market IDs, not instrument names
        This is a simplified implementation
        """
        # For now, return empty structure - full implementation would require
        # market ID lookup or use the streaming API
        return {
            'prices': []
        }

    def _get_market_id(self, instrument: str) -> Optional[int]:
        """
        Get market ID for an instrument name

        Args:
            instrument: Instrument name (e.g., 'EURUSD', 'EUR_USD')

        Returns:
            Market ID or None if not found
        """
        try:
            # Remove underscore if present (EUR_USD -> EURUSD)
            market_name = instrument.replace('_', '')
            print(f"[DEBUG] Looking up market: {market_name}")

            # Search for market
            endpoint = f'/cfd/markets?MarketName={market_name}'
            response = self._request('GET', endpoint)
            print(f"[DEBUG] Market search response keys: {response.keys()}")

            markets = response.get('Markets', [])
            print(f"[DEBUG] Found {len(markets)} markets")

            if markets:
                market_id = markets[0].get('MarketId')
                print(f"[DEBUG] First market ID: {market_id}, Name: {markets[0].get('Name')}")
                return market_id

            print(f"[ERROR] No markets found for {market_name}")
            return None

        except Exception as e:
            import traceback
            print(f"[ERROR] Failed to get market ID for {instrument}: {str(e)}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return None

    def get_candles(self, instrument: str, granularity: str = 'M5', count: int = 100) -> Dict:
        """
        Fetch historical candlestick data

        Args:
            instrument: Instrument name (e.g., 'EURUSD' or 'EUR_USD')
            granularity: Candle interval (M1, M5, M15, H1, H4, D, etc.)
            count: Number of candles to fetch

        Returns:
            Dict with candles in OANDA-compatible format
        """
        try:
            print(f"[DEBUG] get_candles called: instrument={instrument}, granularity={granularity}, count={count}")

            # Get market ID
            market_id = self._get_market_id(instrument)
            print(f"[DEBUG] Market ID for {instrument}: {market_id}")

            if not market_id:
                print(f"[ERROR] No market ID found for {instrument}")
                return {'candles': []}

            # Map granularity to GAIN Capital format
            # M1=MINUTE(1), M5=MINUTE(5), M15=MINUTE(15), H1=HOUR(1), H4=HOUR(4), D=DAY(1)
            interval_map = {
                'M1': ('MINUTE', 1),
                'M5': ('MINUTE', 5),
                'M15': ('MINUTE', 15),
                'M30': ('MINUTE', 30),
                'H1': ('HOUR', 1),
                'H4': ('HOUR', 4),
                'D': ('DAY', 1),
            }

            interval, span = interval_map.get(granularity, ('MINUTE', 5))

            # Get OHLC data
            endpoint = f'/market/{market_id}/barhistory'
            params = {
                'interval': interval,
                'span': span,
                'PriceBars': count
            }

            response = self._request('GET', endpoint, params=params)
            print(f"[DEBUG] API response keys: {response.keys()}")
            print(f"[DEBUG] Number of price bars: {len(response.get('PriceBars', []))}")

            # Convert to OANDA-compatible format
            candles = []
            price_bars = response.get('PriceBars', [])

            for bar in price_bars:
                # Only include complete bars
                candles.append({
                    'time': bar.get('BarDate'),
                    'complete': True,
                    'volume': 1,  # Not provided by GAIN Capital
                    'mid': {
                        'o': str(bar.get('Open', 0)),
                        'h': str(bar.get('High', 0)),
                        'l': str(bar.get('Low', 0)),
                        'c': str(bar.get('Close', 0))
                    }
                })

            print(f"[DEBUG] Returning {len(candles)} candles for {instrument}")
            return {'candles': candles}

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Failed to get candles for {instrument}: {str(e)}")
            print(f"Error details: {error_details}")
            return {'candles': []}

    def create_market_order(
        self,
        instrument: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Create a market order

        Args:
            instrument: Instrument name (e.g., 'EURUSD')
            units: Number of units (positive for buy, negative for sell)
            stop_loss: Stop loss price
            take_profit: Take profit price
        """
        # Determine direction
        direction = 'buy' if units > 0 else 'sell'
        quantity = abs(int(units))

        # Build order data
        order_data = {
            'TradingAccountId': self.trading_account_id,
            'MarketName': instrument,
            'Direction': direction,
            'Quantity': quantity,
            'BidPrice': 0,  # Will be filled by market
            'OfferPrice': 0,  # Will be filled by market
            'AuditId': f'order_{datetime.utcnow().timestamp()}',
            'PositionMethodId': 1
        }

        # Add IfDone orders for stop loss and take profit
        if_done = []

        if stop_loss:
            if_done.append({
                'Stop': {
                    'TriggerPrice': stop_loss,
                    'Quantity': quantity,
                    'Direction': 'sell' if direction == 'buy' else 'buy'
                }
            })

        if take_profit:
            if_done.append({
                'Limit': {
                    'TriggerPrice': take_profit,
                    'Quantity': quantity,
                    'Direction': 'sell' if direction == 'buy' else 'buy'
                }
            })

        if if_done:
            order_data['IfDone'] = if_done

        try:
            response = self._request('POST', '/order/newtradeorder', data=order_data)

            # Map response to expected format
            return {
                'orderFillTransaction': {
                    'id': str(response.get('OrderId', '')),
                    'instrument': instrument,
                    'units': str(units),
                    'price': str(response.get('Price', 0)),
                    'pl': '0'
                }
            }

        except Exception as e:
            raise Exception(f"Failed to create market order: {str(e)}")

    def close_position(self, instrument: str, long_units: str = 'ALL', short_units: str = 'ALL') -> Dict:
        """
        Close position for an instrument

        Args:
            instrument: Instrument name (e.g., 'EURUSD')
        """
        try:
            # Get open positions for this instrument
            positions = self.get_open_positions()

            for pos in positions.get('OpenPositions', []):
                if pos.get('MarketName') == instrument:
                    # Close this position
                    close_data = {
                        'TradingAccountId': self.trading_account_id,
                        'OrderId': pos.get('OrderId')
                    }

                    return self._request('POST', '/order/cancel', data=close_data)

            return {'message': 'No position found to close'}

        except Exception as e:
            raise Exception(f"Failed to close position: {str(e)}")

    def get_positions(self) -> Dict:
        """List all positions"""
        return self.get_open_positions()

    def get_open_positions(self) -> Dict:
        """List only open positions"""
        try:
            endpoint = f'/order/openpositions?TradingAccountId={self.trading_account_id}'
            response = self._request('GET', endpoint)

            # Map to expected format
            positions = []
            for pos in response.get('OpenPositions', []):
                positions.append({
                    'instrument': pos.get('MarketName', ''),
                    'long': {
                        'units': str(pos.get('Quantity', 0)) if pos.get('Direction') == 'buy' else '0'
                    },
                    'short': {
                        'units': str(pos.get('Quantity', 0)) if pos.get('Direction') == 'sell' else '0'
                    },
                    'unrealizedPL': str(pos.get('CurrentProfit', 0)),
                    'marginUsed': '0'  # Not directly available
                })

            return {
                'positions': positions,
                'OpenPositions': response.get('OpenPositions', [])
            }

        except Exception as e:
            raise Exception(f"Failed to get open positions: {str(e)}")

    def get_trades(self) -> Dict:
        """List all trades (active orders)"""
        return self.get_open_trades()

    def get_open_trades(self) -> Dict:
        """List only open trades"""
        try:
            data = {
                'TradingAccountId': self.trading_account_id,
                'MaxResults': 100
            }

            response = self._request('POST', '/order/activeorders', data=data)

            # Map to expected format
            trades = []
            for order in response.get('ActiveOrders', []):
                trades.append({
                    'id': str(order.get('OrderId', '')),
                    'instrument': order.get('MarketName', ''),
                    'currentUnits': str(order.get('Quantity', 0)),
                    'price': str(order.get('Price', 0)),
                    'unrealizedPL': '0',
                    'marginUsed': '0',
                    'openTime': order.get('StatusChanged', '')
                })

            return {
                'trades': trades
            }

        except Exception as e:
            raise Exception(f"Failed to get open trades: {str(e)}")

    def close_trade(self, trade_id: str) -> Dict:
        """Close a specific trade by ID"""
        try:
            data = {
                'TradingAccountId': self.trading_account_id,
                'OrderId': int(trade_id)
            }

            response = self._request('POST', '/order/cancel', data=data)

            # Map to expected format
            return {
                'orderFillTransaction': {
                    'id': trade_id,
                    'price': '0',
                    'pl': '0'
                }
            }

        except Exception as e:
            raise Exception(f"Failed to close trade: {str(e)}")

    def get_instruments(self) -> Dict:
        """List all available trading instruments"""
        # GAIN Capital requires market search or specific market info
        # This would need to be implemented with market search endpoint
        return {
            'instruments': []
        }
