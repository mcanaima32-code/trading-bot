import asyncio
import logging
from binance import AsyncClient, BinanceSocketManager
from binance.exceptions import BinanceAPIException
from decimal import Decimal, ROUND_DOWN
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class BinanceClient:
    def __init__(self):
        self.client = None
        self.testnet = settings.BINANCE_TESTNET
        
    async def initialize(self):
        """Inicializar cliente de Binance"""
        try:
            self.client = await AsyncClient.create(
                api_key=settings.BINANCE_API_KEY,
                api_secret=settings.BINANCE_SECRET_KEY,
                testnet=self.testnet
            )
            logger.info(f"Cliente Binance inicializado (Testnet: {self.testnet})")
            return True
        except Exception as e:
            logger.error(f"Error inicializando cliente Binance: {e}")
            return False
    
    async def get_account_balance(self) -> Dict[str, float]:
        """Obtener balance de la cuenta"""
        if not self.client:
            await self.initialize()
        
        try:
            account = await self.client.get_account()
            balances = {}
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    balances[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            return balances
            
        except BinanceAPIException as e:
            logger.error(f"Error obteniendo balance: {e}")
            return {}
    
    async def get_symbol_info(self, symbol: str) -> Dict:
        """Obtener información del símbolo"""
        if not self.client:
            await self.initialize()
        
        try:
            exchange_info = await self.client.get_exchange_info()
            
            for symbol_info in exchange_info['symbols']:
                if symbol_info['symbol'] == symbol:
                    return symbol_info
            
            return {}
            
        except Exception as e:
            logger.error(f"Error obteniendo info del símbolo {symbol}: {e}")
            return {}
    
    async def get_current_price(self, symbol: str) -> float:
        """Obtener precio actual"""
        if not self.client:
            await self.initialize()
        
        try:
            ticker = await self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
            
        except Exception as e:
            logger.error(f"Error obteniendo precio de {symbol}: {e}")
            return 0.0
    
    async def get_24hr_ticker(self, symbol: str) -> Dict:
        """Obtener estadísticas de 24 horas"""
        if not self.client:
            await self.initialize()
        
        try:
            ticker = await self.client.get_ticker(symbol=symbol)
            return {
                'symbol': ticker['symbol'],
                'price': float(ticker['lastPrice']),
                'change': float(ticker['priceChange']),
                'change_percent': float(ticker['priceChangePercent']),
                'high': float(ticker['highPrice']),
                'low': float(ticker['lowPrice']),
                'volume': float(ticker['volume'])
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo ticker de {symbol}: {e}")
            return {}
    
    def calculate_quantity(self, symbol_info: Dict, usdt_amount: float, price: float) -> float:
        """Calcular cantidad basada en filtros del símbolo"""
        try:
            # Encontrar filtros
            lot_size_filter = None
            min_notional_filter = None
            
            for filter_info in symbol_info.get('filters', []):
                if filter_info['filterType'] == 'LOT_SIZE':
                    lot_size_filter = filter_info
                elif filter_info['filterType'] == 'MIN_NOTIONAL':
                    min_notional_filter = filter_info
            
            if not lot_size_filter:
                return 0
            
            # Calcular cantidad base
            quantity = usdt_amount / price
            
            # Aplicar step size
            step_size = float(lot_size_filter['stepSize'])
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
            
            # Redondear hacia abajo
            quantity = float(Decimal(str(quantity)).quantize(
                Decimal(str(step_size)), rounding=ROUND_DOWN
            ))
            
            # Verificar cantidad mínima
            min_qty = float(lot_size_filter['minQty'])
            if quantity < min_qty:
                return 0
            
            # Verificar valor mínimo
            if min_notional_filter:
                min_notional = float(min_notional_filter['minNotional'])
                if quantity * price < min_notional:
                    return 0
            
            return quantity
            
        except Exception as e:
            logger.error(f"Error calculando cantidad: {e}")
            return 0
    
    async def place_buy_order(self, symbol: str, usdt_amount: float) -> Dict:
        """Ejecutar orden de compra"""
        if not self.client:
            await self.initialize()
        
        try:
            # Obtener información del símbolo
            symbol_info = await self.get_symbol_info(symbol)
            if not symbol_info:
                return {'success': False, 'error': 'Símbolo no encontrado'}
            
            # Obtener precio actual
            current_price = await self.get_current_price(symbol)
            if current_price == 0:
                return {'success': False, 'error': 'No se pudo obtener precio'}
            
            # Calcular cantidad
            quantity = self.calculate_quantity(symbol_info, usdt_amount, current_price)
            if quantity == 0:
                return {'success': False, 'error': 'Cantidad insuficiente'}
            
            # Ejecutar orden
            order = await self.client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'BUY',
                'quantity': float(order['executedQty']),
                'price': float(order['fills'][0]['price']) if order['fills'] else current_price,
                'total': float(order['cummulativeQuoteQty']),
                'timestamp': order['transactTime']
            }
            
        except BinanceAPIException as e:
            logger.error(f"Error en orden de compra: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error inesperado en compra: {e}")
            return {'success': False, 'error': str(e)}
    
    async def place_sell_order(self, symbol: str, quantity: float) -> Dict:
        """Ejecutar orden de venta"""
        if not self.client:
            await self.initialize()
        
        try:
            # Obtener información del símbolo
            symbol_info = await self.get_symbol_info(symbol)
            if not symbol_info:
                return {'success': False, 'error': 'Símbolo no encontrado'}
            
            # Ajustar cantidad según step size
            for filter_info in symbol_info.get('filters', []):
                if filter_info['filterType'] == 'LOT_SIZE':
                    step_size = float(filter_info['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = float(Decimal(str(quantity)).quantize(
                        Decimal(str(step_size)), rounding=ROUND_DOWN
                    ))
                    break
            
            # Ejecutar orden
            order = await self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            return {
                'success': True,
                'order_id': order['orderId'],
                'symbol': symbol,
                'side': 'SELL',
                'quantity': float(order['executedQty']),
                'price': float(order['fills'][0]['price']) if order['fills'] else 0,
                'total': float(order['cummulativeQuoteQty']),
                'timestamp': order['transactTime']
            }
            
        except BinanceAPIException as e:
            logger.error(f"Error en orden de venta: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Error inesperado en venta: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_position(self, symbol: str) -> Dict:
        """Obtener posición actual de un símbolo"""
        try:
            balance = await self.get_account_balance()
            asset = symbol.replace('USDT', '')
            
            if asset in balance:
                return {
                    'symbol': symbol,
                    'quantity': balance[asset]['total'],
                    'free': balance[asset]['free'],
                    'locked': balance[asset]['locked']
                }
            
            return {'symbol': symbol, 'quantity': 0, 'free': 0, 'locked': 0}
            
        except Exception as e:
            logger.error(f"Error obteniendo posición de {symbol}: {e}")
            return {'symbol': symbol, 'quantity': 0, 'free': 0, 'locked': 0}
    
    async def get_open_positions(self) -> List[Dict]:
        """Obtener todas las posiciones abiertas"""
        try:
            balances = await self.get_account_balance()
            positions = []
            
            for asset, balance_info in balances.items():
                if asset != 'USDT' and balance_info['total'] > 0:
                    symbol = f"{asset}USDT"
                    current_price = await self.get_current_price(symbol)
                    
                    positions.append({
                        'symbol': symbol,
                        'asset': asset,
                        'quantity': balance_info['total'],
                        'current_price': current_price,
                        'current_value': balance_info['total'] * current_price
                    })
            
            return positions
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones abiertas: {e}")
            return []
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[List]:
        """Obtener datos de velas (klines)"""
        if not self.client:
            await self.initialize()
        
        try:
            klines = await self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            return klines
            
        except Exception as e:
            logger.error(f"Error obteniendo klines de {symbol}: {e}")
            return []
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """Obtener libro de órdenes"""
        if not self.client:
            await self.initialize()
        
        try:
            order_book = await self.client.get_order_book(symbol=symbol, limit=limit)
            return {
                'bids': [[float(price), float(qty)] for price, qty in order_book['bids']],
                'asks': [[float(price), float(qty)] for price, qty in order_book['asks']]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo order book de {symbol}: {e}")
            return {'bids': [], 'asks': []}
    
    async def close(self):
        """Cerrar conexión"""
        if self.client:
            await self.client.close_connection()