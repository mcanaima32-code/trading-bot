import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Tuple
import logging
from src.binance_client import BinanceClient
from config.settings import settings

logger = logging.getLogger(__name__)

class MarketAnalyzer:
    def __init__(self):
        self.binance_client = BinanceClient()
        
    async def get_market_data(self, symbol: str, interval: str = '1h', limit: int = 100) -> Dict:
        """Obtener datos de mercado básicos"""
        try:
            # Obtener ticker de 24h
            ticker_24h = await self.binance_client.get_24hr_ticker(symbol)
            
            # Obtener klines para análisis técnico
            klines = await self.binance_client.get_klines(symbol, interval, limit)
            
            if not klines:
                return {}
            
            # Convertir a DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Convertir tipos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col])
            
            return {
                'symbol': symbol,
                'price': ticker_24h.get('price', 0),
                'change_24h': ticker_24h.get('change_percent', 0),
                'volume_24h': ticker_24h.get('volume', 0),
                'high_24h': ticker_24h.get('high', 0),
                'low_24h': ticker_24h.get('low', 0),
                'dataframe': df,
                'last_update': pd.Timestamp.now()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de mercado para {symbol}: {e}")
            return {}
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcular RSI (Relative Strength Index)"""
        try:
            return ta.momentum.RSIIndicator(df['close'], window=period).rsi()
        except Exception as e:
            logger.error(f"Error calculando RSI: {e}")
            return pd.Series([50] * len(df))
    
    def calculate_macd(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcular MACD"""
        try:
            macd_indicator = ta.trend.MACD(df['close'])
            return {
                'macd': macd_indicator.macd(),
                'macd_signal': macd_indicator.macd_signal(),
                'macd_histogram': macd_indicator.macd_diff()
            }
        except Exception as e:
            logger.error(f"Error calculando MACD: {e}")
            return {
                'macd': pd.Series([0] * len(df)),
                'macd_signal': pd.Series([0] * len(df)),
                'macd_histogram': pd.Series([0] * len(df))
            }
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20) -> Dict[str, pd.Series]:
        """Calcular Bandas de Bollinger"""
        try:
            bb_indicator = ta.volatility.BollingerBands(df['close'], window=period)
            return {
                'bb_upper': bb_indicator.bollinger_hband(),
                'bb_middle': bb_indicator.bollinger_mavg(),
                'bb_lower': bb_indicator.bollinger_lband(),
                'bb_width': bb_indicator.bollinger_wband(),
                'bb_percent': bb_indicator.bollinger_pband()
            }
        except Exception as e:
            logger.error(f"Error calculando Bollinger Bands: {e}")
            return {
                'bb_upper': df['close'],
                'bb_middle': df['close'],
                'bb_lower': df['close'],
                'bb_width': pd.Series([0] * len(df)),
                'bb_percent': pd.Series([0.5] * len(df))
            }
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcular medias móviles"""
        try:
            return {
                'sma_10': ta.trend.SMAIndicator(df['close'], window=10).sma_indicator(),
                'sma_20': ta.trend.SMAIndicator(df['close'], window=20).sma_indicator(),
                'sma_50': ta.trend.SMAIndicator(df['close'], window=50).sma_indicator(),
                'ema_12': ta.trend.EMAIndicator(df['close'], window=12).ema_indicator(),
                'ema_26': ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
            }
        except Exception as e:
            logger.error(f"Error calculando medias móviles: {e}")
            return {
                'sma_10': df['close'],
                'sma_20': df['close'],
                'sma_50': df['close'],
                'ema_12': df['close'],
                'ema_26': df['close']
            }
    
    def calculate_stochastic(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcular oscilador estocástico"""
        try:
            stoch_indicator = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
            return {
                'stoch_k': stoch_indicator.stoch(),
                'stoch_d': stoch_indicator.stoch_signal()
            }
        except Exception as e:
            logger.error(f"Error calculando estocástico: {e}")
            return {
                'stoch_k': pd.Series([50] * len(df)),
                'stoch_d': pd.Series([50] * len(df))
            }
    
    def calculate_volume_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calcular indicadores de volumen"""
        try:
            return {
                'volume_sma': ta.volume.VolumeSMAIndicator(df['close'], df['volume']).volume_sma(),
                'obv': ta.volume.OnBalanceVolumeIndicator(df['close'], df['volume']).on_balance_volume(),
                'vwap': ta.volume.VolumeSMAIndicator(df['close'], df['volume']).volume_sma()
            }
        except Exception as e:
            logger.error(f"Error calculando indicadores de volumen: {e}")
            return {
                'volume_sma': df['volume'],
                'obv': pd.Series([0] * len(df)),
                'vwap': df['close']
            }
    
    async def technical_analysis(self, symbol: str) -> Dict:
        """Realizar análisis técnico completo"""
        try:
            # Obtener datos de mercado
            market_data = await self.get_market_data(symbol)
            if not market_data or market_data['dataframe'].empty:
                return {'score': 5.0, 'signals': [], 'indicators': {}}
            
            df = market_data['dataframe']
            current_price = float(df['close'].iloc[-1])
            
            # Calcular indicadores
            rsi = self.calculate_rsi(df)
            macd = self.calculate_macd(df)
            bb = self.calculate_bollinger_bands(df)
            ma = self.calculate_moving_averages(df)
            stoch = self.calculate_stochastic(df)
            volume = self.calculate_volume_indicators(df)
            
            # Valores actuales de indicadores
            current_rsi = float(rsi.iloc[-1]) if not rsi.empty else 50
            current_macd = float(macd['macd'].iloc[-1]) if not macd['macd'].empty else 0
            current_macd_signal = float(macd['macd_signal'].iloc[-1]) if not macd['macd_signal'].empty else 0
            current_bb_percent = float(bb['bb_percent'].iloc[-1]) if not bb['bb_percent'].empty else 0.5
            current_stoch_k = float(stoch['stoch_k'].iloc[-1]) if not stoch['stoch_k'].empty else 50
            
            # Análisis de señales
            signals = []
            score = 5.0  # Score neutro
            
            # RSI Analysis
            if current_rsi < 30:
                signals.append({'type': 'BUY', 'indicator': 'RSI', 'strength': 'STRONG', 'value': current_rsi})
                score += 2
            elif current_rsi < 40:
                signals.append({'type': 'BUY', 'indicator': 'RSI', 'strength': 'WEAK', 'value': current_rsi})
                score += 1
            elif current_rsi > 70:
                signals.append({'type': 'SELL', 'indicator': 'RSI', 'strength': 'STRONG', 'value': current_rsi})
                score -= 2
            elif current_rsi > 60:
                signals.append({'type': 'SELL', 'indicator': 'RSI', 'strength': 'WEAK', 'value': current_rsi})
                score -= 1
            
            # MACD Analysis
            if current_macd > current_macd_signal:
                signals.append({'type': 'BUY', 'indicator': 'MACD', 'strength': 'MEDIUM', 'value': current_macd})
                score += 1.5
            else:
                signals.append({'type': 'SELL', 'indicator': 'MACD', 'strength': 'MEDIUM', 'value': current_macd})
                score -= 1.5
            
            # Bollinger Bands Analysis
            if current_bb_percent < 0.2:
                signals.append({'type': 'BUY', 'indicator': 'BB', 'strength': 'MEDIUM', 'value': current_bb_percent})
                score += 1.5
            elif current_bb_percent > 0.8:
                signals.append({'type': 'SELL', 'indicator': 'BB', 'strength': 'MEDIUM', 'value': current_bb_percent})
                score -= 1.5
            
            # Moving Average Analysis
            sma_20 = float(ma['sma_20'].iloc[-1]) if not ma['sma_20'].empty else current_price
            if current_price > sma_20:
                signals.append({'type': 'BUY', 'indicator': 'SMA20', 'strength': 'WEAK', 'value': current_price/sma_20})
                score += 0.5
            else:
                signals.append({'type': 'SELL', 'indicator': 'SMA20', 'strength': 'WEAK', 'value': current_price/sma_20})
                score -= 0.5
            
            # Stochastic Analysis
            if current_stoch_k < 20:
                signals.append({'type': 'BUY', 'indicator': 'STOCH', 'strength': 'MEDIUM', 'value': current_stoch_k})
                score += 1
            elif current_stoch_k > 80:
                signals.append({'type': 'SELL', 'indicator': 'STOCH', 'strength': 'MEDIUM', 'value': current_stoch_k})
                score -= 1
            
            # Normalizar score (0-10)
            score = max(0, min(10, score))
            
            return {
                'symbol': symbol,
                'score': score,
                'signals': signals,
                'current_price': current_price,
                'indicators': {
                    'rsi': current_rsi,
                    'macd': current_macd,
                    'macd_signal': current_macd_signal,
                    'bb_percent': current_bb_percent,
                    'stoch_k': current_stoch_k,
                    'sma_20': sma_20
                },
                'trend': 'BULLISH' if score > 6 else 'BEARISH' if score < 4 else 'NEUTRAL'
            }
            
        except Exception as e:
            logger.error(f"Error en análisis técnico de {symbol}: {e}")
            return {'score': 5.0, 'signals': [], 'indicators': {}}
    
    async def should_buy(self, symbol: str) -> Dict:
        """Determinar si se debe comprar basado en análisis"""
        try:
            analysis = await self.technical_analysis(symbol)
            
            # Criterios para compra
            should_buy = False
            reasons = []
            
            # Score técnico alto
            if analysis['score'] >= 7:
                should_buy = True
                reasons.append(f"Score técnico alto: {analysis['score']:.1f}/10")
            
            # Múltiples señales de compra
            buy_signals = [s for s in analysis['signals'] if s['type'] == 'BUY']
            if len(buy_signals) >= 3:
                should_buy = True
                reasons.append(f"Múltiples señales de compra: {len(buy_signals)}")
            
            # RSI oversold
            if analysis['indicators'].get('rsi', 50) < 30:
                should_buy = True
                reasons.append(f"RSI oversold: {analysis['indicators']['rsi']:.1f}")
            
            # Calcular cantidad sugerida basada en riesgo
            balance = await self.binance_client.get_account_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            max_risk_amount = usdt_balance * settings.MAX_RISK_PER_TRADE
            
            # Ajustar cantidad basada en confianza del análisis
            confidence_multiplier = min(1.0, analysis['score'] / 10)
            suggested_amount = max_risk_amount * confidence_multiplier
            
            return {
                'should_buy': should_buy,
                'reasons': reasons,
                'suggested_amount': suggested_amount,
                'confidence': analysis['score'] / 10,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error determinando compra para {symbol}: {e}")
            return {
                'should_buy': False,
                'reasons': [f"Error en análisis: {str(e)}"],
                'suggested_amount': 0,
                'confidence': 0
            }
    
    async def should_sell(self, symbol: str) -> Dict:
        """Determinar si se debe vender basado en análisis"""
        try:
            analysis = await self.technical_analysis(symbol)
            
            # Criterios para venta
            should_sell = False
            reasons = []
            
            # Score técnico bajo
            if analysis['score'] <= 3:
                should_sell = True
                reasons.append(f"Score técnico bajo: {analysis['score']:.1f}/10")
            
            # Múltiples señales de venta
            sell_signals = [s for s in analysis['signals'] if s['type'] == 'SELL']
            if len(sell_signals) >= 3:
                should_sell = True
                reasons.append(f"Múltiples señales de venta: {len(sell_signals)}")
            
            # RSI overbought
            if analysis['indicators'].get('rsi', 50) > 70:
                should_sell = True
                reasons.append(f"RSI overbought: {analysis['indicators']['rsi']:.1f}")
            
            return {
                'should_sell': should_sell,
                'reasons': reasons,
                'confidence': (10 - analysis['score']) / 10,
                'analysis': analysis
            }
            
        except Exception as e:
            logger.error(f"Error determinando venta para {symbol}: {e}")
            return {
                'should_sell': False,
                'reasons': [f"Error en análisis: {str(e)}"],
                'confidence': 0
            }
    
    async def quick_analysis(self, symbol: str) -> Dict:
        """Análisis rápido para decisiones inmediatas"""
        try:
            # Obtener datos básicos
            ticker = await self.binance_client.get_24hr_ticker(symbol)
            
            # Análisis simple basado en cambio de precio
            change_24h = ticker.get('change_percent', 0)
            volume_24h = ticker.get('volume', 0)
            
            # Señal de compra simple
            buy_signal = False
            
            if change_24h > -5 and change_24h < 2 and volume_24h > 1000:
                buy_signal = True
            
            # Cantidad sugerida
            balance = await self.binance_client.get_account_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            suggested_amount = usdt_balance * settings.MAX_RISK_PER_TRADE * 0.5  # Más conservador
            
            return {
                'buy_signal': buy_signal,
                'suggested_amount': suggested_amount,
                'change_24h': change_24h,
                'volume_24h': volume_24h
            }
            
        except Exception as e:
            logger.error(f"Error en análisis rápido de {symbol}: {e}")
            return {
                'buy_signal': False,
                'suggested_amount': 0,
                'change_24h': 0,
                'volume_24h': 0
            }
    
    async def get_top_performers(self, limit: int = 10) -> List[Dict]:
        """Obtener las mejores criptomonedas del día"""
        try:
            performers = []
            
            for symbol in settings.TRADING_PAIRS:
                ticker = await self.binance_client.get_24hr_ticker(symbol)
                if ticker:
                    performers.append({
                        'symbol': symbol,
                        'price': ticker['price'],
                        'change_24h': ticker['change_percent'],
                        'volume': ticker['volume']
                    })
            
            # Ordenar por cambio de precio
            performers.sort(key=lambda x: x['change_24h'], reverse=True)
            
            return performers[:limit]
            
        except Exception as e:
            logger.error(f"Error obteniendo top performers: {e}")
            return []