import asyncio
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from config.settings import settings
from src.market_analyzer import MarketAnalyzer
from src.llm_advisor import LLMAdvisor

logger = logging.getLogger(__name__)

class Backtester:
    def __init__(self):
        self.market_analyzer = MarketAnalyzer()
        self.llm_advisor = LLMAdvisor()
        
        # Parámetros de backtesting
        self.initial_capital = 10000
        self.commission = 0.001  # 0.1% comisión por trade
        
        # Resultados
        self.trades = []
        self.portfolio_values = []
        self.daily_returns = []
        
    async def run_backtest(self, symbol: str, start_date: str, end_date: str, 
                          strategy_params: Optional[Dict] = None) -> Dict:
        """Ejecutar backtesting para un símbolo y período específico"""
        try:
            logger.info(f"Iniciando backtesting para {symbol}: {start_date} - {end_date}")
            
            # Obtener datos históricos
            historical_data = await self._get_historical_data(symbol, start_date, end_date)
            
            if historical_data.empty:
                return {'error': 'No se pudieron obtener datos históricos'}
            
            # Inicializar variables
            capital = self.initial_capital
            position = 0  # 0 = sin posición, 1 = long, -1 = short
            entry_price = 0
            entry_date = None
            
            self.trades = []
            self.portfolio_values = []
            self.daily_returns = []
            
            # Ejecutar backtesting día por día
            for i in range(50, len(historical_data)):  # Empezar después de 50 días para indicadores
                current_data = historical_data.iloc[:i+1]
                current_price = current_data['close'].iloc[-1]
                current_date = current_data.index[-1]
                
                # Calcular indicadores técnicos
                signals = await self._calculate_signals(current_data)
                
                # Tomar decisión de trading
                decision = await self._make_trading_decision(signals, position)
                
                # Ejecutar trade si es necesario
                if decision['action'] == 'BUY' and position == 0:
                    # Abrir posición long
                    position = 1
                    entry_price = current_price
                    entry_date = current_date
                    
                elif decision['action'] == 'SELL' and position == 1:
                    # Cerrar posición long
                    exit_price = current_price
                    exit_date = current_date
                    
                    # Calcular P&L
                    pnl = (exit_price - entry_price) / entry_price
                    pnl_amount = capital * pnl * (1 - self.commission * 2)  # Comisión entrada y salida
                    
                    capital += pnl_amount
                    
                    # Registrar trade
                    trade = {
                        'entry_date': entry_date,
                        'exit_date': exit_date,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'pnl_pct': pnl * 100,
                        'pnl_amount': pnl_amount,
                        'capital_after': capital,
                        'hold_days': (exit_date - entry_date).days
                    }
                    self.trades.append(trade)
                    
                    position = 0
                    entry_price = 0
                    entry_date = None
                
                # Registrar valor del portfolio
                portfolio_value = capital
                if position == 1:  # Si tenemos posición abierta
                    unrealized_pnl = (current_price - entry_price) / entry_price
                    portfolio_value = capital * (1 + unrealized_pnl)
                
                self.portfolio_values.append({
                    'date': current_date,
                    'value': portfolio_value,
                    'price': current_price
                })
            
            # Calcular métricas de rendimiento
            results = await self._calculate_performance_metrics(symbol)
            
            logger.info(f"Backtesting completado: {len(self.trades)} trades, {results['total_return']:.2f}% retorno")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en backtesting: {e}")
            return {'error': str(e)}
    
    async def _get_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Obtener datos históricos (simulados para el ejemplo)"""
        try:
            # En implementación real, obtener datos de Binance o fuente de datos históricos
            # Por ahora, generar datos simulados
            
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            dates = pd.date_range(start, end, freq='D')
            
            # Generar precios simulados (random walk con tendencia)
            np.random.seed(42)  # Para resultados reproducibles
            returns = np.random.normal(0.001, 0.02, len(dates))  # 0.1% retorno promedio, 2% volatilidad
            
            # Precio inicial
            initial_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
            
            prices = [initial_price]
            for ret in returns[1:]:
                prices.append(prices[-1] * (1 + ret))
            
            # Crear DataFrame con OHLCV
            df = pd.DataFrame({
                'open': prices,
                'high': [p * (1 + np.random.uniform(0, 0.02)) for p in prices],
                'low': [p * (1 - np.random.uniform(0, 0.02)) for p in prices],
                'close': prices,
                'volume': np.random.uniform(1000, 10000, len(dates))
            }, index=dates)
            
            # Asegurar que high >= max(open, close) y low <= min(open, close)
            df['high'] = np.maximum(df['high'], np.maximum(df['open'], df['close']))
            df['low'] = np.minimum(df['low'], np.minimum(df['open'], df['close']))
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
            return pd.DataFrame()
    
    async def _calculate_signals(self, data: pd.DataFrame) -> Dict:
        """Calcular señales técnicas para el backtesting"""
        try:
            # Usar el analizador de mercado para calcular indicadores
            # Simular análisis técnico
            
            close_prices = data['close']
            
            # RSI
            rsi = self._calculate_rsi(close_prices, 14)
            current_rsi = rsi.iloc[-1] if not rsi.empty else 50
            
            # Medias móviles
            sma_20 = close_prices.rolling(20).mean()
            sma_50 = close_prices.rolling(50).mean()
            
            current_price = close_prices.iloc[-1]
            current_sma_20 = sma_20.iloc[-1] if not sma_20.empty else current_price
            current_sma_50 = sma_50.iloc[-1] if not sma_50.empty else current_price
            
            # MACD
            macd_line, signal_line = self._calculate_macd(close_prices)
            current_macd = macd_line.iloc[-1] if not macd_line.empty else 0
            current_signal = signal_line.iloc[-1] if not signal_line.empty else 0
            
            return {
                'rsi': current_rsi,
                'price': current_price,
                'sma_20': current_sma_20,
                'sma_50': current_sma_50,
                'macd': current_macd,
                'macd_signal': current_signal,
                'price_above_sma20': current_price > current_sma_20,
                'price_above_sma50': current_price > current_sma_50,
                'sma20_above_sma50': current_sma_20 > current_sma_50,
                'macd_bullish': current_macd > current_signal
            }
            
        except Exception as e:
            logger.error(f"Error calculando señales: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcular RSI"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except Exception as e:
            logger.error(f"Error calculando RSI: {e}")
            return pd.Series()
    
    def _calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
        """Calcular MACD"""
        try:
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()
            return macd_line, signal_line
        except Exception as e:
            logger.error(f"Error calculando MACD: {e}")
            return pd.Series(), pd.Series()
    
    async def _make_trading_decision(self, signals: Dict, current_position: int) -> Dict:
        """Tomar decisión de trading basada en señales"""
        try:
            action = 'HOLD'
            confidence = 0
            reasons = []
            
            # Estrategia simple basada en múltiples indicadores
            buy_signals = 0
            sell_signals = 0
            
            # RSI
            rsi = signals.get('rsi', 50)
            if rsi < 30:
                buy_signals += 2
                reasons.append("RSI oversold")
            elif rsi > 70:
                sell_signals += 2
                reasons.append("RSI overbought")
            
            # Medias móviles
            if signals.get('price_above_sma20', False):
                buy_signals += 1
                reasons.append("Price above SMA20")
            else:
                sell_signals += 1
                reasons.append("Price below SMA20")
            
            if signals.get('sma20_above_sma50', False):
                buy_signals += 1
                reasons.append("SMA20 above SMA50")
            else:
                sell_signals += 1
                reasons.append("SMA20 below SMA50")
            
            # MACD
            if signals.get('macd_bullish', False):
                buy_signals += 1
                reasons.append("MACD bullish")
            else:
                sell_signals += 1
                reasons.append("MACD bearish")
            
            # Determinar acción
            if buy_signals >= 3 and current_position == 0:
                action = 'BUY'
                confidence = min(100, buy_signals * 20)
            elif sell_signals >= 3 and current_position == 1:
                action = 'SELL'
                confidence = min(100, sell_signals * 20)
            
            return {
                'action': action,
                'confidence': confidence,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'reasons': reasons
            }
            
        except Exception as e:
            logger.error(f"Error tomando decisión de trading: {e}")
            return {'action': 'HOLD', 'confidence': 0}
    
    async def _calculate_performance_metrics(self, symbol: str) -> Dict:
        """Calcular métricas de rendimiento del backtesting"""
        try:
            if not self.trades or not self.portfolio_values:
                return {'error': 'No hay datos suficientes para calcular métricas'}
            
            # Convertir a DataFrames
            trades_df = pd.DataFrame(self.trades)
            portfolio_df = pd.DataFrame(self.portfolio_values)
            
            # Métricas básicas
            total_trades = len(trades_df)
            winning_trades = len(trades_df[trades_df['pnl_pct'] > 0])
            losing_trades = len(trades_df[trades_df['pnl_pct'] < 0])
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Retorno total
            final_capital = portfolio_df['value'].iloc[-1]
            total_return = (final_capital / self.initial_capital - 1) * 100
            
            # Métricas de riesgo
            returns = portfolio_df['value'].pct_change().dropna()
            
            if len(returns) > 0:
                volatility = returns.std() * np.sqrt(252) * 100  # Anualizada
                sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252)) if returns.std() > 0 else 0
                
                # Drawdown máximo
                portfolio_df['peak'] = portfolio_df['value'].cummax()
                portfolio_df['drawdown'] = (portfolio_df['value'] / portfolio_df['peak'] - 1) * 100
                max_drawdown = portfolio_df['drawdown'].min()
            else:
                volatility = 0
                sharpe_ratio = 0
                max_drawdown = 0
            
            # Métricas de trades
            if total_trades > 0:
                avg_win = trades_df[trades_df['pnl_pct'] > 0]['pnl_pct'].mean() if winning_trades > 0 else 0
                avg_loss = trades_df[trades_df['pnl_pct'] < 0]['pnl_pct'].mean() if losing_trades > 0 else 0
                best_trade = trades_df['pnl_pct'].max()
                worst_trade = trades_df['pnl_pct'].min()
                avg_hold_days = trades_df['hold_days'].mean()
                
                profit_factor = abs(avg_win * winning_trades / (avg_loss * losing_trades)) if avg_loss != 0 and losing_trades > 0 else float('inf')
            else:
                avg_win = avg_loss = best_trade = worst_trade = avg_hold_days = profit_factor = 0
            
            # Calcular retorno buy & hold para comparación
            if len(portfolio_df) > 1:
                buy_hold_return = (portfolio_df['price'].iloc[-1] / portfolio_df['price'].iloc[0] - 1) * 100
            else:
                buy_hold_return = 0
            
            return {
                'symbol': symbol,
                'initial_capital': self.initial_capital,
                'final_capital': final_capital,
                'total_return': total_return,
                'buy_hold_return': buy_hold_return,
                'excess_return': total_return - buy_hold_return,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'avg_hold_days': avg_hold_days,
                'profit_factor': profit_factor,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'trades_data': trades_df.to_dict('records'),
                'portfolio_data': portfolio_df.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de rendimiento: {e}")
            return {'error': str(e)}
    
    async def run_multi_symbol_backtest(self, symbols: List[str], start_date: str, 
                                       end_date: str) -> Dict:
        """Ejecutar backtesting para múltiples símbolos"""
        try:
            results = {}
            
            for symbol in symbols:
                logger.info(f"Ejecutando backtesting para {symbol}")
                result = await self.run_backtest(symbol, start_date, end_date)
                results[symbol] = result
                
                # Pausa pequeña entre símbolos
                await asyncio.sleep(1)
            
            # Calcular estadísticas agregadas
            aggregate_stats = self._calculate_aggregate_stats(results)
            
            return {
                'individual_results': results,
                'aggregate_stats': aggregate_stats
            }
            
        except Exception as e:
            logger.error(f"Error en backtesting multi-símbolo: {e}")
            return {'error': str(e)}
    
    def _calculate_aggregate_stats(self, results: Dict) -> Dict:
        """Calcular estadísticas agregadas de múltiples backtests"""
        try:
            valid_results = {k: v for k, v in results.items() if 'error' not in v}
            
            if not valid_results:
                return {'error': 'No hay resultados válidos'}
            
            # Promedios
            avg_return = np.mean([r['total_return'] for r in valid_results.values()])
            avg_win_rate = np.mean([r['win_rate'] for r in valid_results.values()])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in valid_results.values()])
            avg_max_drawdown = np.mean([r['max_drawdown'] for r in valid_results.values()])
            
            # Mejores y peores
            best_performer = max(valid_results.items(), key=lambda x: x[1]['total_return'])
            worst_performer = min(valid_results.items(), key=lambda x: x[1]['total_return'])
            
            # Totales
            total_trades = sum([r['total_trades'] for r in valid_results.values()])
            total_winning = sum([r['winning_trades'] for r in valid_results.values()])
            
            return {
                'symbols_tested': len(valid_results),
                'avg_return': avg_return,
                'avg_win_rate': avg_win_rate,
                'avg_sharpe_ratio': avg_sharpe,
                'avg_max_drawdown': avg_max_drawdown,
                'best_performer': {
                    'symbol': best_performer[0],
                    'return': best_performer[1]['total_return']
                },
                'worst_performer': {
                    'symbol': worst_performer[0],
                    'return': worst_performer[1]['total_return']
                },
                'total_trades': total_trades,
                'overall_win_rate': (total_winning / total_trades * 100) if total_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculando estadísticas agregadas: {e}")
            return {'error': str(e)}
    
    def generate_report(self, results: Dict, save_path: str = 'backtest_report.html') -> str:
        """Generar reporte HTML del backtesting"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Reporte de Backtesting</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                    .metric {{ margin: 10px 0; }}
                    .positive {{ color: green; }}
                    .negative {{ color: red; }}
                    .neutral {{ color: black; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🤖 Reporte de Backtesting - Bot de Trading</h1>
                    <p>Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h2>📊 Resumen de Rendimiento</h2>
            """
            
            if 'error' not in results:
                symbol = results.get('symbol', 'N/A')
                total_return = results.get('total_return', 0)
                win_rate = results.get('win_rate', 0)
                sharpe_ratio = results.get('sharpe_ratio', 0)
                max_drawdown = results.get('max_drawdown', 0)
                
                return_class = 'positive' if total_return > 0 else 'negative'
                
                html_content += f"""
                <div class="metric">📈 <strong>Símbolo:</strong> {symbol}</div>
                <div class="metric">💰 <strong>Capital Inicial:</strong> ${results.get('initial_capital', 0):,.2f}</div>
                <div class="metric">💵 <strong>Capital Final:</strong> ${results.get('final_capital', 0):,.2f}</div>
                <div class="metric">📊 <strong>Retorno Total:</strong> <span class="{return_class}">{total_return:.2f}%</span></div>
                <div class="metric">🎯 <strong>Tasa de Acierto:</strong> {win_rate:.1f}%</div>
                <div class="metric">📉 <strong>Drawdown Máximo:</strong> <span class="negative">{max_drawdown:.2f}%</span></div>
                <div class="metric">⚡ <strong>Ratio de Sharpe:</strong> {sharpe_ratio:.2f}</div>
                <div class="metric">🔄 <strong>Total de Trades:</strong> {results.get('total_trades', 0)}</div>
                
                <h2>📋 Detalle de Trades</h2>
                <table>
                    <tr>
                        <th>Fecha Entrada</th>
                        <th>Fecha Salida</th>
                        <th>Precio Entrada</th>
                        <th>Precio Salida</th>
                        <th>P&L %</th>
                        <th>P&L $</th>
                        <th>Días</th>
                    </tr>
                """
                
                trades_data = results.get('trades_data', [])
                for trade in trades_data[-10:]:  # Últimos 10 trades
                    pnl_class = 'positive' if trade['pnl_pct'] > 0 else 'negative'
                    html_content += f"""
                    <tr>
                        <td>{trade['entry_date']}</td>
                        <td>{trade['exit_date']}</td>
                        <td>${trade['entry_price']:.2f}</td>
                        <td>${trade['exit_price']:.2f}</td>
                        <td class="{pnl_class}">{trade['pnl_pct']:.2f}%</td>
                        <td class="{pnl_class}">${trade['pnl_amount']:.2f}</td>
                        <td>{trade['hold_days']}</td>
                    </tr>
                    """
                
                html_content += "</table>"
            else:
                html_content += f"<p class='negative'>Error: {results['error']}</p>"
            
            html_content += """
                <h2>⚠️ Disclaimer</h2>
                <p>Este backtesting es solo para fines educativos. Los resultados pasados no garantizan rendimientos futuros. 
                El trading de criptomonedas conlleva riesgos significativos.</p>
            </body>
            </html>
            """
            
            # Guardar archivo
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Reporte guardado en: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Error generando reporte: {e}")
            return str(e)