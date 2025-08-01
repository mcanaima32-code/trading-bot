import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import numpy as np
from config.settings import settings
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self):
        self.db = DatabaseManager()
        
        # Parámetros de riesgo
        self.max_portfolio_risk = 0.10  # 10% del capital total
        self.max_daily_loss = 0.05      # 5% pérdida máxima diaria
        self.max_weekly_loss = 0.15     # 15% pérdida máxima semanal
        self.max_positions = 5          # Máximo 5 posiciones simultáneas
        self.correlation_threshold = 0.7 # Evitar correlación alta
        
        # Estado interno
        self.daily_pnl = 0
        self.weekly_pnl = 0
        self.current_exposure = 0
        self.active_positions = {}
        
    async def initialize(self):
        """Inicializar gestor de riesgo"""
        await self._calculate_current_metrics()
        logger.info("Gestor de riesgo inicializado")
    
    async def _calculate_current_metrics(self):
        """Calcular métricas actuales de riesgo"""
        try:
            # P&L diario y semanal
            daily_stats = await self.db.get_trading_stats(1)
            weekly_stats = await self.db.get_trading_stats(7)
            
            self.daily_pnl = daily_stats.get('net_flow', 0)
            self.weekly_pnl = weekly_stats.get('net_flow', 0)
            
            # Exposición actual
            positions = await self.db.get_open_positions()
            self.current_exposure = sum(pos.get('current_value', 0) for pos in positions)
            
            # Posiciones activas
            self.active_positions = {pos['symbol']: pos for pos in positions}
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")
    
    async def evaluate_position_risk(self, symbol: str, trade_amount: float, 
                                   entry_price: float, stop_loss: float) -> Dict:
        """Evaluar riesgo de una nueva posición"""
        try:
            # Calcular riesgo de la posición
            risk_amount = abs(entry_price - stop_loss) * (trade_amount / entry_price)
            risk_percentage = risk_amount / trade_amount if trade_amount > 0 else 0
            
            # Verificar límites
            checks = {
                'position_size_ok': trade_amount <= (10000 * settings.MAX_RISK_PER_TRADE),
                'stop_loss_ok': risk_percentage <= settings.STOP_LOSS_PERCENTAGE * 1.5,
                'portfolio_risk_ok': (self.current_exposure + trade_amount) <= (10000 * self.max_portfolio_risk),
                'position_limit_ok': len(self.active_positions) < self.max_positions,
                'daily_loss_ok': self.daily_pnl > (-10000 * self.max_daily_loss),
                'weekly_loss_ok': self.weekly_pnl > (-10000 * self.max_weekly_loss),
                'correlation_ok': await self._check_correlation(symbol)
            }
            
            # Calcular score de riesgo
            risk_score = self._calculate_risk_score(
                risk_percentage, trade_amount, self.current_exposure
            )
            
            # Determinar si es aceptable
            all_checks_pass = all(checks.values())
            
            return {
                'approved': all_checks_pass and risk_score <= 7,
                'risk_score': risk_score,
                'risk_amount': risk_amount,
                'risk_percentage': risk_percentage,
                'checks': checks,
                'recommendations': self._generate_risk_recommendations(checks, risk_score)
            }
            
        except Exception as e:
            logger.error(f"Error evaluando riesgo de posición: {e}")
            return {
                'approved': False,
                'risk_score': 10,
                'error': str(e)
            }
    
    def _calculate_risk_score(self, risk_pct: float, trade_amount: float, 
                            current_exposure: float) -> float:
        """Calcular score de riesgo (0-10, menor es mejor)"""
        try:
            score = 0
            
            # Riesgo por stop loss
            if risk_pct > 0.08:  # >8%
                score += 3
            elif risk_pct > 0.05:  # >5%
                score += 2
            elif risk_pct > 0.03:  # >3%
                score += 1
            
            # Tamaño de posición
            if trade_amount > 1000:  # >$1000
                score += 2
            elif trade_amount > 500:  # >$500
                score += 1
            
            # Exposición total
            total_exposure = current_exposure + trade_amount
            if total_exposure > 5000:  # >$5000
                score += 2
            elif total_exposure > 2000:  # >$2000
                score += 1
            
            # P&L actual
            if self.daily_pnl < -500:  # Pérdida >$500 hoy
                score += 2
            elif self.daily_pnl < -200:  # Pérdida >$200 hoy
                score += 1
            
            return min(10, score)
            
        except Exception as e:
            logger.error(f"Error calculando risk score: {e}")
            return 10
    
    async def _check_correlation(self, symbol: str) -> bool:
        """Verificar correlación con posiciones existentes"""
        try:
            if len(self.active_positions) == 0:
                return True
            
            # Símbolos correlacionados (simplificado)
            crypto_groups = {
                'btc': ['BTCUSDT'],
                'eth': ['ETHUSDT'],
                'defi': ['LINKUSDT', 'UNIUSDT', 'AAVEUSDT'],
                'layer1': ['ADAUSDT', 'SOLUSDT', 'DOTUSDT', 'AVAXUSDT'],
                'exchange': ['BNBUSDT', 'CAKEUSDT']
            }
            
            # Encontrar grupo del símbolo
            symbol_group = None
            for group, symbols in crypto_groups.items():
                if symbol in symbols:
                    symbol_group = group
                    break
            
            if not symbol_group:
                return True  # Símbolo no clasificado, permitir
            
            # Verificar si ya tenemos posiciones en el mismo grupo
            for active_symbol in self.active_positions.keys():
                for group, symbols in crypto_groups.items():
                    if active_symbol in symbols and group == symbol_group:
                        return False  # Alta correlación detectada
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando correlación: {e}")
            return True  # En caso de error, permitir
    
    def _generate_risk_recommendations(self, checks: Dict, risk_score: float) -> List[str]:
        """Generar recomendaciones basadas en evaluación de riesgo"""
        recommendations = []
        
        if not checks.get('position_size_ok', True):
            recommendations.append("Reducir tamaño de posición")
        
        if not checks.get('stop_loss_ok', True):
            recommendations.append("Ajustar stop loss más cerca")
        
        if not checks.get('portfolio_risk_ok', True):
            recommendations.append("Reducir exposición total del portafolio")
        
        if not checks.get('position_limit_ok', True):
            recommendations.append("Cerrar algunas posiciones antes de abrir nuevas")
        
        if not checks.get('daily_loss_ok', True):
            recommendations.append("Pausar trading por pérdidas diarias")
        
        if not checks.get('weekly_loss_ok', True):
            recommendations.append("Revisar estrategia por pérdidas semanales")
        
        if not checks.get('correlation_ok', True):
            recommendations.append("Evitar símbolos correlacionados")
        
        if risk_score >= 8:
            recommendations.append("Riesgo muy alto - considerar no operar")
        elif risk_score >= 6:
            recommendations.append("Riesgo alto - reducir exposición")
        
        return recommendations
    
    async def calculate_optimal_position_size(self, symbol: str, entry_price: float, 
                                            stop_loss: float, confidence: float) -> float:
        """Calcular tamaño óptimo de posición usando Kelly Criterion modificado"""
        try:
            # Obtener balance disponible
            # En implementación real, obtener del cliente de Binance
            available_balance = 10000  # Placeholder
            
            # Calcular riesgo por unidad
            risk_per_unit = abs(entry_price - stop_loss)
            risk_percentage = risk_per_unit / entry_price
            
            # Kelly Criterion modificado
            win_rate = confidence / 100
            avg_win = settings.TAKE_PROFIT_PERCENTAGE
            avg_loss = risk_percentage
            
            # Kelly = (bp - q) / b
            # b = avg_win/avg_loss, p = win_rate, q = 1-win_rate
            if avg_loss > 0:
                b = avg_win / avg_loss
                kelly_fraction = (b * win_rate - (1 - win_rate)) / b
            else:
                kelly_fraction = 0
            
            # Limitar Kelly fraction para ser conservador
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Máximo 25%
            
            # Aplicar límites de riesgo
            max_risk_amount = available_balance * settings.MAX_RISK_PER_TRADE
            kelly_position_size = available_balance * kelly_fraction
            
            # Usar el menor entre Kelly y límite de riesgo
            optimal_size = min(kelly_position_size, max_risk_amount)
            
            # Verificar límites mínimos
            min_trade_size = 10  # $10 mínimo
            optimal_size = max(optimal_size, min_trade_size)
            
            return optimal_size
            
        except Exception as e:
            logger.error(f"Error calculando tamaño óptimo: {e}")
            return available_balance * settings.MAX_RISK_PER_TRADE
    
    async def should_close_position(self, symbol: str, current_price: float, 
                                  entry_price: float, position_age_hours: float) -> Dict:
        """Determinar si se debe cerrar una posición"""
        try:
            reasons = []
            should_close = False
            urgency = 'low'
            
            # Calcular P&L actual
            pnl_pct = (current_price / entry_price - 1) * 100
            
            # Reglas de cierre
            
            # 1. Stop loss alcanzado
            if pnl_pct <= -settings.STOP_LOSS_PERCENTAGE * 100:
                should_close = True
                urgency = 'high'
                reasons.append("Stop loss alcanzado")
            
            # 2. Take profit alcanzado
            elif pnl_pct >= settings.TAKE_PROFIT_PERCENTAGE * 100:
                should_close = True
                urgency = 'medium'
                reasons.append("Take profit alcanzado")
            
            # 3. Posición muy antigua (>48 horas)
            elif position_age_hours > 48:
                should_close = True
                urgency = 'low'
                reasons.append("Posición muy antigua")
            
            # 4. Pérdida diaria excesiva
            elif self.daily_pnl < -1000:  # >$1000 pérdida hoy
                should_close = True
                urgency = 'high'
                reasons.append("Límite de pérdida diaria")
            
            # 5. Trailing stop (si está en ganancia)
            elif pnl_pct > 5:  # Si está 5% en ganancia
                trailing_stop = entry_price * 1.03  # 3% trailing
                if current_price <= trailing_stop:
                    should_close = True
                    urgency = 'medium'
                    reasons.append("Trailing stop activado")
            
            return {
                'should_close': should_close,
                'urgency': urgency,
                'reasons': reasons,
                'current_pnl_pct': pnl_pct
            }
            
        except Exception as e:
            logger.error(f"Error evaluando cierre de posición: {e}")
            return {
                'should_close': False,
                'urgency': 'low',
                'reasons': [f"Error: {str(e)}"],
                'current_pnl_pct': 0
            }
    
    async def get_risk_report(self) -> Dict:
        """Generar reporte completo de riesgo"""
        try:
            await self._calculate_current_metrics()
            
            # Calcular métricas adicionales
            portfolio_performance = await self.db.calculate_portfolio_performance()
            
            # VaR (Value at Risk) simplificado
            var_95 = self.current_exposure * 0.05  # 5% VaR diario
            
            # Sharpe ratio estimado
            returns = portfolio_performance.get('total_return', 0)
            sharpe_ratio = returns / 0.02 if returns > 0 else 0  # Asumiendo 2% volatilidad
            
            # Estado general de riesgo
            risk_level = 'LOW'
            if self.current_exposure > 5000 or self.daily_pnl < -500:
                risk_level = 'HIGH'
            elif self.current_exposure > 2000 or self.daily_pnl < -200:
                risk_level = 'MEDIUM'
            
            return {
                'risk_level': risk_level,
                'current_exposure': self.current_exposure,
                'daily_pnl': self.daily_pnl,
                'weekly_pnl': self.weekly_pnl,
                'active_positions': len(self.active_positions),
                'var_95': var_95,
                'sharpe_ratio': sharpe_ratio,
                'portfolio_performance': portfolio_performance,
                'risk_limits': {
                    'max_portfolio_risk': self.max_portfolio_risk,
                    'max_daily_loss': self.max_daily_loss,
                    'max_weekly_loss': self.max_weekly_loss,
                    'max_positions': self.max_positions
                }
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de riesgo: {e}")
            return {'error': str(e)}
    
    async def emergency_stop(self) -> Dict:
        """Parada de emergencia - cerrar todas las posiciones"""
        try:
            logger.warning("🚨 PARADA DE EMERGENCIA ACTIVADA")
            
            positions_to_close = list(self.active_positions.keys())
            results = {
                'positions_closed': 0,
                'positions_failed': 0,
                'total_positions': len(positions_to_close),
                'errors': []
            }
            
            # En implementación real, cerrar todas las posiciones
            for symbol in positions_to_close:
                try:
                    # Simular cierre de posición
                    logger.info(f"Cerrando posición de emergencia: {symbol}")
                    results['positions_closed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error cerrando {symbol}: {e}")
                    results['positions_failed'] += 1
                    results['errors'].append(f"{symbol}: {str(e)}")
            
            # Guardar evento en base de datos
            await self.db.set_config('last_emergency_stop', str(datetime.now().timestamp()))
            
            return results
            
        except Exception as e:
            logger.error(f"Error en parada de emergencia: {e}")
            return {'error': str(e)}
    
    async def validate_market_conditions(self) -> Dict:
        """Validar condiciones generales del mercado"""
        try:
            # Obtener datos de mercado general
            # En implementación real, obtener del analizador de mercado
            
            conditions = {
                'market_open': True,  # Crypto mercado siempre abierto
                'high_volatility': False,
                'network_issues': False,
                'exchange_maintenance': False
            }
            
            # Verificar volatilidad extrema (placeholder)
            # if btc_volatility > 10%:
            #     conditions['high_volatility'] = True
            
            safe_to_trade = all([
                conditions['market_open'],
                not conditions['high_volatility'],
                not conditions['network_issues'],
                not conditions['exchange_maintenance']
            ])
            
            return {
                'safe_to_trade': safe_to_trade,
                'conditions': conditions,
                'recommendations': self._get_market_recommendations(conditions)
            }
            
        except Exception as e:
            logger.error(f"Error validando condiciones de mercado: {e}")
            return {
                'safe_to_trade': False,
                'error': str(e)
            }
    
    def _get_market_recommendations(self, conditions: Dict) -> List[str]:
        """Obtener recomendaciones basadas en condiciones de mercado"""
        recommendations = []
        
        if conditions.get('high_volatility'):
            recommendations.append("Reducir tamaños de posición por alta volatilidad")
        
        if conditions.get('network_issues'):
            recommendations.append("Evitar trading por problemas de red")
        
        if conditions.get('exchange_maintenance'):
            recommendations.append("Pausar trading por mantenimiento del exchange")
        
        return recommendations