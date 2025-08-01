import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from config.settings import settings
from src.binance_client import BinanceClient
from src.market_analyzer import MarketAnalyzer
from src.llm_advisor import LLMAdvisor
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class TradingStrategy:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.market_analyzer = MarketAnalyzer()
        self.llm_advisor = LLMAdvisor()
        self.db = DatabaseManager()
        
        # Parámetros de estrategia
        self.target_weekly_return = settings.TARGET_WEEKLY_RETURN  # 30%
        self.max_risk_per_trade = settings.MAX_RISK_PER_TRADE  # 2%
        self.stop_loss_pct = settings.STOP_LOSS_PERCENTAGE  # 5%
        self.take_profit_pct = settings.TAKE_PROFIT_PERCENTAGE  # 10%
        
        # Estado interno
        self.active_positions = {}
        self.daily_pnl = 0
        self.weekly_pnl = 0
        self.max_daily_trades = 10
        self.trades_today = 0
        
    async def initialize(self):
        """Inicializar estrategia"""
        await self.binance_client.initialize()
        await self._load_active_positions()
        await self._calculate_current_pnl()
        logger.info("Estrategia de trading inicializada")
    
    async def _load_active_positions(self):
        """Cargar posiciones activas"""
        try:
            positions = await self.db.get_open_positions()
            for pos in positions:
                self.active_positions[pos['symbol']] = pos
            logger.info(f"Cargadas {len(positions)} posiciones activas")
        except Exception as e:
            logger.error(f"Error cargando posiciones: {e}")
    
    async def _calculate_current_pnl(self):
        """Calcular P&L actual"""
        try:
            # P&L diario
            today = datetime.now().strftime('%Y-%m-%d')
            stats = await self.db.get_trading_stats(1)
            self.daily_pnl = stats.get('net_flow', 0)
            
            # P&L semanal
            weekly_stats = await self.db.get_trading_stats(7)
            self.weekly_pnl = weekly_stats.get('net_flow', 0)
            
            # Contar trades de hoy
            today_trades = await self.db.get_trades()
            today_timestamp = int(datetime.now().replace(hour=0, minute=0, second=0).timestamp() * 1000)
            self.trades_today = len([t for t in today_trades if t['timestamp'] >= today_timestamp])
            
        except Exception as e:
            logger.error(f"Error calculando P&L: {e}")
    
    async def scan_opportunities(self) -> List[Dict]:
        """Escanear oportunidades de trading"""
        try:
            opportunities = []
            
            # Analizar cada símbolo
            for symbol in settings.TRADING_PAIRS:
                try:
                    # Obtener datos de mercado
                    market_data = await self.market_analyzer.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Análisis técnico
                    technical_analysis = await self.market_analyzer.technical_analysis(symbol)
                    
                    # Consejo de IA
                    ai_advice = await self.llm_advisor.get_trading_advice(symbol, market_data, technical_analysis)
                    
                    # Evaluar oportunidad
                    opportunity_score = await self._evaluate_opportunity(symbol, market_data, technical_analysis, ai_advice)
                    
                    if opportunity_score['score'] >= 7.0:  # Umbral mínimo
                        opportunities.append({
                            'symbol': symbol,
                            'score': opportunity_score['score'],
                            'action': opportunity_score['action'],
                            'confidence': opportunity_score['confidence'],
                            'market_data': market_data,
                            'technical_analysis': technical_analysis,
                            'ai_advice': ai_advice,
                            'reasoning': opportunity_score['reasoning']
                        })
                
                except Exception as e:
                    logger.error(f"Error analizando {symbol}: {e}")
                    continue
            
            # Ordenar por score
            opportunities.sort(key=lambda x: x['score'], reverse=True)
            
            logger.info(f"Encontradas {len(opportunities)} oportunidades")
            return opportunities[:5]  # Top 5
            
        except Exception as e:
            logger.error(f"Error escaneando oportunidades: {e}")
            return []
    
    async def _evaluate_opportunity(self, symbol: str, market_data: Dict, technical_analysis: Dict, ai_advice: Dict) -> Dict:
        """Evaluar una oportunidad de trading"""
        try:
            score = 0
            reasoning = []
            
            # Score técnico (30% peso)
            tech_score = technical_analysis.get('score', 5)
            score += tech_score * 0.3
            reasoning.append(f"Score técnico: {tech_score:.1f}/10")
            
            # Confianza de IA (25% peso)
            ai_confidence = ai_advice.get('confidence', 50) / 100
            ai_recommendation = ai_advice.get('recommendation', 'HOLD')
            
            if ai_recommendation == 'BUY':
                score += ai_confidence * 2.5
                reasoning.append(f"IA recomienda COMPRAR ({ai_confidence*100:.0f}%)")
            elif ai_recommendation == 'SELL':
                score += ai_confidence * 2.5
                reasoning.append(f"IA recomienda VENDER ({ai_confidence*100:.0f}%)")
            
            # Volumen (15% peso)
            volume_24h = market_data.get('volume_24h', 0)
            if volume_24h > 1000000:  # Alto volumen
                score += 1.5
                reasoning.append("Alto volumen de trading")
            elif volume_24h > 100000:  # Volumen medio
                score += 0.75
                reasoning.append("Volumen medio de trading")
            
            # Volatilidad (15% peso)
            change_24h = abs(market_data.get('change_24h', 0))
            if 2 <= change_24h <= 8:  # Volatilidad óptima
                score += 1.5
                reasoning.append(f"Volatilidad óptima: {change_24h:.1f}%")
            elif change_24h > 8:  # Alta volatilidad
                score += 0.5
                reasoning.append(f"Alta volatilidad: {change_24h:.1f}%")
            
            # Relación riesgo/recompensa (15% peso)
            entry_price = ai_advice.get('entry_price', market_data.get('price', 0))
            stop_loss = ai_advice.get('stop_loss', 0)
            take_profit = ai_advice.get('take_profit', 0)
            
            if entry_price > 0 and stop_loss > 0 and take_profit > 0:
                rr_analysis = await self.llm_advisor.analyze_risk_reward(symbol, entry_price, stop_loss, take_profit)
                rr_ratio = rr_analysis.get('risk_reward_ratio', 0)
                
                if rr_ratio >= 2:
                    score += 1.5
                    reasoning.append(f"Excelente R/R: {rr_ratio:.1f}")
                elif rr_ratio >= 1.5:
                    score += 0.75
                    reasoning.append(f"Buena R/R: {rr_ratio:.1f}")
            
            # Penalizaciones
            # Ya tenemos posición abierta
            if symbol in self.active_positions:
                score -= 2
                reasoning.append("Ya hay posición abierta")
            
            # Límite de trades diarios alcanzado
            if self.trades_today >= self.max_daily_trades:
                score -= 3
                reasoning.append("Límite diario de trades alcanzado")
            
            # P&L diario negativo muy alto
            if self.daily_pnl < -1000:  # Pérdida de más de $1000 hoy
                score -= 2
                reasoning.append("P&L diario muy negativo")
            
            # Determinar acción
            action = 'HOLD'
            confidence = min(100, max(0, score * 10))
            
            if ai_recommendation == 'BUY' and score >= 7:
                action = 'BUY'
            elif ai_recommendation == 'SELL' and score >= 7:
                action = 'SELL'
            
            return {
                'score': min(10, max(0, score)),
                'action': action,
                'confidence': confidence,
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"Error evaluando oportunidad para {symbol}: {e}")
            return {'score': 0, 'action': 'HOLD', 'confidence': 0, 'reasoning': [f"Error: {str(e)}"]}
    
    async def execute_trade(self, opportunity: Dict) -> Dict:
        """Ejecutar un trade basado en una oportunidad"""
        try:
            symbol = opportunity['symbol']
            action = opportunity['action']
            ai_advice = opportunity['ai_advice']
            
            if action == 'BUY':
                return await self._execute_buy(symbol, ai_advice, opportunity)
            elif action == 'SELL':
                return await self._execute_sell(symbol, ai_advice, opportunity)
            else:
                return {'success': False, 'error': 'Acción no válida'}
                
        except Exception as e:
            logger.error(f"Error ejecutando trade: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_buy(self, symbol: str, ai_advice: Dict, opportunity: Dict) -> Dict:
        """Ejecutar orden de compra"""
        try:
            # Calcular cantidad basada en riesgo
            balance = await self.binance_client.get_account_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            
            # Cantidad máxima basada en riesgo por trade
            max_trade_amount = usdt_balance * self.max_risk_per_trade
            
            # Ajustar basada en confianza
            confidence_factor = opportunity['confidence'] / 100
            trade_amount = max_trade_amount * confidence_factor
            
            # Mínimo de $10 para que sea viable
            if trade_amount < 10:
                return {'success': False, 'error': 'Cantidad insuficiente para trade'}
            
            # Ejecutar orden
            result = await self.binance_client.place_buy_order(symbol, trade_amount)
            
            if result['success']:
                # Guardar en base de datos
                await self.db.save_trade(result)
                
                # Actualizar posición
                await self.db.update_position(symbol, result['quantity'], result['price'])
                
                # Configurar stop loss y take profit
                await self._set_stop_loss_take_profit(symbol, result['price'], 'BUY', ai_advice)
                
                # Actualizar estado
                self.active_positions[symbol] = {
                    'symbol': symbol,
                    'quantity': result['quantity'],
                    'entry_price': result['price'],
                    'side': 'BUY'
                }
                
                self.trades_today += 1
                
                logger.info(f"Compra ejecutada: {symbol} - {result['quantity']} @ ${result['price']}")
                
                return {
                    'success': True,
                    'action': 'BUY',
                    'symbol': symbol,
                    'quantity': result['quantity'],
                    'price': result['price'],
                    'total': result['total']
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error ejecutando compra de {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _execute_sell(self, symbol: str, ai_advice: Dict, opportunity: Dict) -> Dict:
        """Ejecutar orden de venta"""
        try:
            # Verificar que tenemos posición
            if symbol not in self.active_positions:
                return {'success': False, 'error': 'No hay posición para vender'}
            
            position = self.active_positions[symbol]
            quantity = position['quantity']
            
            # Ejecutar orden
            result = await self.binance_client.place_sell_order(symbol, quantity)
            
            if result['success']:
                # Calcular P&L
                entry_price = position['entry_price']
                exit_price = result['price']
                pnl = (exit_price - entry_price) * quantity
                pnl_pct = (exit_price / entry_price - 1) * 100
                
                # Guardar en base de datos
                await self.db.save_trade(result)
                
                # Cerrar posición
                await self.db.update_position(symbol, -quantity, exit_price)
                
                # Remover de posiciones activas
                del self.active_positions[symbol]
                
                self.trades_today += 1
                self.daily_pnl += pnl
                self.weekly_pnl += pnl
                
                logger.info(f"Venta ejecutada: {symbol} - P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
                
                return {
                    'success': True,
                    'action': 'SELL',
                    'symbol': symbol,
                    'quantity': result['quantity'],
                    'price': result['price'],
                    'total': result['total'],
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                }
            else:
                return result
                
        except Exception as e:
            logger.error(f"Error ejecutando venta de {symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _set_stop_loss_take_profit(self, symbol: str, entry_price: float, side: str, ai_advice: Dict):
        """Configurar stop loss y take profit"""
        try:
            # Usar precios sugeridos por IA o calcular automáticamente
            if side == 'BUY':
                stop_loss = ai_advice.get('stop_loss', entry_price * (1 - self.stop_loss_pct))
                take_profit = ai_advice.get('take_profit', entry_price * (1 + self.take_profit_pct))
            else:
                stop_loss = ai_advice.get('stop_loss', entry_price * (1 + self.stop_loss_pct))
                take_profit = ai_advice.get('take_profit', entry_price * (1 - self.take_profit_pct))
            
            # Guardar en configuración para monitoreo
            await self.db.set_config(f"{symbol}_stop_loss", str(stop_loss))
            await self.db.set_config(f"{symbol}_take_profit", str(take_profit))
            
            logger.info(f"Stop Loss/Take Profit configurado para {symbol}: SL=${stop_loss:.4f}, TP=${take_profit:.4f}")
            
        except Exception as e:
            logger.error(f"Error configurando SL/TP para {symbol}: {e}")
    
    async def monitor_positions(self) -> List[Dict]:
        """Monitorear posiciones activas"""
        try:
            actions_needed = []
            
            for symbol, position in self.active_positions.items():
                try:
                    # Obtener precio actual
                    current_price = await self.binance_client.get_current_price(symbol)
                    if current_price == 0:
                        continue
                    
                    # Obtener stop loss y take profit
                    stop_loss = float(await self.db.get_config(f"{symbol}_stop_loss") or 0)
                    take_profit = float(await self.db.get_config(f"{symbol}_take_profit") or 0)
                    
                    entry_price = position['entry_price']
                    side = position['side']
                    
                    # Calcular P&L actual
                    if side == 'BUY':
                        pnl_pct = (current_price / entry_price - 1) * 100
                        
                        # Verificar stop loss
                        if stop_loss > 0 and current_price <= stop_loss:
                            actions_needed.append({
                                'action': 'SELL',
                                'symbol': symbol,
                                'reason': 'STOP_LOSS',
                                'current_price': current_price,
                                'pnl_pct': pnl_pct
                            })
                        
                        # Verificar take profit
                        elif take_profit > 0 and current_price >= take_profit:
                            actions_needed.append({
                                'action': 'SELL',
                                'symbol': symbol,
                                'reason': 'TAKE_PROFIT',
                                'current_price': current_price,
                                'pnl_pct': pnl_pct
                            })
                    
                    # Actualizar precio actual en posición
                    position['current_price'] = current_price
                    position['pnl_pct'] = pnl_pct
                    
                except Exception as e:
                    logger.error(f"Error monitoreando {symbol}: {e}")
                    continue
            
            return actions_needed
            
        except Exception as e:
            logger.error(f"Error monitoreando posiciones: {e}")
            return []
    
    async def should_trade_today(self) -> bool:
        """Determinar si debemos hacer trading hoy"""
        try:
            # Verificar límites
            if self.trades_today >= self.max_daily_trades:
                return False
            
            # Verificar P&L diario
            if self.daily_pnl < -2000:  # Pérdida máxima diaria $2000
                logger.warning("Límite de pérdida diaria alcanzado")
                return False
            
            # Verificar si ya alcanzamos objetivo semanal
            weekly_target = 1000 * self.target_weekly_return  # Asumiendo $1000 base
            if self.weekly_pnl >= weekly_target:
                logger.info("Objetivo semanal alcanzado")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando si debe hacer trading: {e}")
            return False
    
    async def get_performance_summary(self) -> Dict:
        """Obtener resumen de rendimiento"""
        try:
            stats = await self.db.get_trading_stats(7)
            portfolio_performance = await self.db.calculate_portfolio_performance()
            
            # Calcular progreso hacia objetivo semanal
            weekly_target = 1000 * self.target_weekly_return  # Base de $1000
            weekly_progress = (self.weekly_pnl / weekly_target * 100) if weekly_target > 0 else 0
            
            return {
                'daily_pnl': self.daily_pnl,
                'weekly_pnl': self.weekly_pnl,
                'weekly_target': weekly_target,
                'weekly_progress_pct': weekly_progress,
                'trades_today': self.trades_today,
                'active_positions': len(self.active_positions),
                'total_trades_week': stats.get('total_trades', 0),
                'avg_trade_size': stats.get('avg_trade_size', 0),
                'portfolio_performance': portfolio_performance
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de rendimiento: {e}")
            return {}
    
    async def run_trading_cycle(self) -> Dict:
        """Ejecutar un ciclo completo de trading"""
        try:
            results = {
                'opportunities_found': 0,
                'trades_executed': 0,
                'positions_monitored': 0,
                'actions_taken': [],
                'errors': []
            }
            
            # Verificar si debemos hacer trading
            if not await self.should_trade_today():
                results['message'] = "Trading pausado por límites o objetivos alcanzados"
                return results
            
            # 1. Monitorear posiciones existentes
            monitoring_actions = await self.monitor_positions()
            results['positions_monitored'] = len(self.active_positions)
            
            # Ejecutar acciones de monitoreo (stop loss, take profit)
            for action in monitoring_actions:
                try:
                    if action['action'] == 'SELL':
                        # Crear oportunidad artificial para venta
                        sell_opportunity = {
                            'symbol': action['symbol'],
                            'action': 'SELL',
                            'ai_advice': {},
                            'confidence': 100
                        }
                        
                        result = await self.execute_trade(sell_opportunity)
                        if result['success']:
                            results['trades_executed'] += 1
                            results['actions_taken'].append({
                                'type': action['reason'],
                                'symbol': action['symbol'],
                                'result': result
                            })
                
                except Exception as e:
                    results['errors'].append(f"Error ejecutando {action['reason']} para {action['symbol']}: {str(e)}")
            
            # 2. Buscar nuevas oportunidades solo si hay espacio
            available_slots = self.max_daily_trades - self.trades_today
            if available_slots > 0:
                opportunities = await self.scan_opportunities()
                results['opportunities_found'] = len(opportunities)
                
                # Ejecutar las mejores oportunidades
                for opportunity in opportunities[:available_slots]:
                    try:
                        result = await self.execute_trade(opportunity)
                        if result['success']:
                            results['trades_executed'] += 1
                            results['actions_taken'].append({
                                'type': 'NEW_TRADE',
                                'symbol': opportunity['symbol'],
                                'action': opportunity['action'],
                                'result': result
                            })
                    
                    except Exception as e:
                        results['errors'].append(f"Error ejecutando trade para {opportunity['symbol']}: {str(e)}")
            
            # 3. Actualizar métricas
            await self._calculate_current_pnl()
            
            return results
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
            return {'error': str(e), 'trades_executed': 0}