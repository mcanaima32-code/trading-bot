import asyncio
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from scipy.optimize import minimize
from config.settings import settings
from src.binance_client import BinanceClient
from src.database import DatabaseManager

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.db = DatabaseManager()
        
        # Parámetros de optimización
        self.target_symbols = settings.TRADING_PAIRS
        self.rebalance_threshold = 0.05  # 5% desviación para rebalanceo
        self.max_position_weight = 0.3   # Máximo 30% en una posición
        self.min_position_weight = 0.05  # Mínimo 5% en una posición
        
        # Datos históricos para optimización
        self.price_data = {}
        self.correlation_matrix = None
        self.expected_returns = None
        self.covariance_matrix = None
        
    async def initialize(self):
        """Inicializar optimizador de portafolio"""
        await self.binance_client.initialize()
        logger.info("Optimizador de portafolio inicializado")
    
    async def get_current_portfolio(self) -> Dict:
        """Obtener composición actual del portafolio"""
        try:
            positions = await self.db.get_open_positions()
            balance = await self.binance_client.get_account_balance()
            
            # Calcular valor total del portafolio
            total_value = 0
            portfolio_composition = {}
            
            # Valor en USDT
            usdt_balance = balance.get('USDT', {}).get('total', 0)
            total_value += usdt_balance
            
            # Valor de posiciones abiertas
            for position in positions:
                symbol = position['symbol']
                quantity = position['quantity']
                current_price = await self.binance_client.get_current_price(symbol)
                
                position_value = quantity * current_price
                total_value += position_value
                
                asset = symbol.replace('USDT', '')
                portfolio_composition[asset] = {
                    'quantity': quantity,
                    'price': current_price,
                    'value': position_value,
                    'weight': 0  # Se calculará después
                }
            
            # Agregar USDT
            if usdt_balance > 0:
                portfolio_composition['USDT'] = {
                    'quantity': usdt_balance,
                    'price': 1.0,
                    'value': usdt_balance,
                    'weight': 0
                }
            
            # Calcular pesos
            for asset in portfolio_composition:
                portfolio_composition[asset]['weight'] = (
                    portfolio_composition[asset]['value'] / total_value
                ) if total_value > 0 else 0
            
            return {
                'total_value': total_value,
                'composition': portfolio_composition,
                'last_updated': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo portafolio actual: {e}")
            return {'error': str(e)}
    
    async def calculate_optimal_weights(self, risk_tolerance: float = 0.5) -> Dict:
        """Calcular pesos óptimos usando teoría moderna de portafolio"""
        try:
            # Obtener datos históricos
            await self._fetch_historical_data()
            
            if not self.price_data:
                return {'error': 'No se pudieron obtener datos históricos'}
            
            # Calcular retornos esperados y matriz de covarianza
            self._calculate_risk_return_metrics()
            
            # Optimización de Markowitz
            optimal_weights = self._optimize_portfolio(risk_tolerance)
            
            # Filtrar pesos muy pequeños
            filtered_weights = {
                asset: weight for asset, weight in optimal_weights.items()
                if weight >= self.min_position_weight
            }
            
            # Normalizar pesos filtrados
            total_weight = sum(filtered_weights.values())
            if total_weight > 0:
                filtered_weights = {
                    asset: weight / total_weight
                    for asset, weight in filtered_weights.items()
                }
            
            return {
                'optimal_weights': filtered_weights,
                'risk_tolerance': risk_tolerance,
                'expected_return': self._calculate_portfolio_return(filtered_weights),
                'expected_risk': self._calculate_portfolio_risk(filtered_weights),
                'sharpe_ratio': self._calculate_sharpe_ratio(filtered_weights)
            }
            
        except Exception as e:
            logger.error(f"Error calculando pesos óptimos: {e}")
            return {'error': str(e)}
    
    async def _fetch_historical_data(self, days: int = 90):
        """Obtener datos históricos para análisis"""
        try:
            self.price_data = {}
            
            for symbol in self.target_symbols:
                # En implementación real, obtener datos históricos de Binance
                # Por ahora, generar datos simulados
                dates = pd.date_range(
                    start=datetime.now() - timedelta(days=days),
                    end=datetime.now(),
                    freq='D'
                )
                
                # Simular precios con random walk
                np.random.seed(hash(symbol) % 2**32)  # Seed basado en símbolo
                returns = np.random.normal(0.001, 0.02, len(dates))
                
                initial_price = 50000 if 'BTC' in symbol else 3000 if 'ETH' in symbol else 100
                prices = [initial_price]
                
                for ret in returns[1:]:
                    prices.append(prices[-1] * (1 + ret))
                
                self.price_data[symbol] = pd.Series(prices, index=dates)
            
            logger.info(f"Datos históricos obtenidos para {len(self.price_data)} símbolos")
            
        except Exception as e:
            logger.error(f"Error obteniendo datos históricos: {e}")
    
    def _calculate_risk_return_metrics(self):
        """Calcular métricas de riesgo y retorno"""
        try:
            if not self.price_data:
                return
            
            # Crear DataFrame con precios
            price_df = pd.DataFrame(self.price_data)
            
            # Calcular retornos diarios
            returns_df = price_df.pct_change().dropna()
            
            # Retornos esperados (anualizados)
            self.expected_returns = returns_df.mean() * 252
            
            # Matriz de covarianza (anualizada)
            self.covariance_matrix = returns_df.cov() * 252
            
            # Matriz de correlación
            self.correlation_matrix = returns_df.corr()
            
            logger.info("Métricas de riesgo y retorno calculadas")
            
        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
    
    def _optimize_portfolio(self, risk_tolerance: float) -> Dict:
        """Optimizar portafolio usando programación cuadrática"""
        try:
            if self.expected_returns is None or self.covariance_matrix is None:
                return {}
            
            n_assets = len(self.expected_returns)
            assets = list(self.expected_returns.index)
            
            # Función objetivo: maximizar utilidad (retorno - penalización por riesgo)
            def objective(weights):
                portfolio_return = np.dot(weights, self.expected_returns)
                portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(self.covariance_matrix, weights)))
                
                # Utilidad = retorno - (aversión al riesgo * riesgo^2)
                utility = portfolio_return - (risk_tolerance * portfolio_risk ** 2)
                return -utility  # Minimizar el negativo = maximizar
            
            # Restricciones
            constraints = [
                {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Suma = 1
            ]
            
            # Límites para cada peso
            bounds = tuple(
                (self.min_position_weight, self.max_position_weight)
                for _ in range(n_assets)
            )
            
            # Pesos iniciales (equiponderados)
            initial_weights = np.array([1.0 / n_assets] * n_assets)
            
            # Optimización
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                optimal_weights = dict(zip(assets, result.x))
                return optimal_weights
            else:
                logger.warning("Optimización no convergió, usando pesos equiponderados")
                return dict(zip(assets, initial_weights))
                
        except Exception as e:
            logger.error(f"Error en optimización: {e}")
            return {}
    
    def _calculate_portfolio_return(self, weights: Dict) -> float:
        """Calcular retorno esperado del portafolio"""
        try:
            if not weights or self.expected_returns is None:
                return 0
            
            portfolio_return = 0
            for asset, weight in weights.items():
                if asset in self.expected_returns.index:
                    portfolio_return += weight * self.expected_returns[asset]
            
            return portfolio_return
            
        except Exception as e:
            logger.error(f"Error calculando retorno del portafolio: {e}")
            return 0
    
    def _calculate_portfolio_risk(self, weights: Dict) -> float:
        """Calcular riesgo (volatilidad) del portafolio"""
        try:
            if not weights or self.covariance_matrix is None:
                return 0
            
            # Convertir pesos a array en el orden correcto
            weight_array = np.array([
                weights.get(asset, 0) for asset in self.covariance_matrix.index
            ])
            
            # Calcular varianza del portafolio
            portfolio_variance = np.dot(weight_array.T, np.dot(self.covariance_matrix, weight_array))
            
            # Retornar volatilidad (raíz cuadrada de la varianza)
            return np.sqrt(portfolio_variance)
            
        except Exception as e:
            logger.error(f"Error calculando riesgo del portafolio: {e}")
            return 0
    
    def _calculate_sharpe_ratio(self, weights: Dict, risk_free_rate: float = 0.02) -> float:
        """Calcular ratio de Sharpe del portafolio"""
        try:
            portfolio_return = self._calculate_portfolio_return(weights)
            portfolio_risk = self._calculate_portfolio_risk(weights)
            
            if portfolio_risk == 0:
                return 0
            
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_risk
            return sharpe_ratio
            
        except Exception as e:
            logger.error(f"Error calculando Sharpe ratio: {e}")
            return 0
    
    async def suggest_rebalancing(self, target_weights: Dict) -> Dict:
        """Sugerir operaciones de rebalanceo"""
        try:
            current_portfolio = await self.get_current_portfolio()
            
            if 'error' in current_portfolio:
                return current_portfolio
            
            current_composition = current_portfolio['composition']
            total_value = current_portfolio['total_value']
            
            rebalancing_actions = []
            
            # Calcular desviaciones y acciones necesarias
            for asset, target_weight in target_weights.items():
                current_weight = current_composition.get(asset, {}).get('weight', 0)
                weight_difference = target_weight - current_weight
                
                # Si la desviación es significativa
                if abs(weight_difference) > self.rebalance_threshold:
                    target_value = target_weight * total_value
                    current_value = current_composition.get(asset, {}).get('value', 0)
                    value_difference = target_value - current_value
                    
                    if value_difference > 0:
                        # Necesita comprar
                        action = {
                            'asset': asset,
                            'action': 'BUY',
                            'current_weight': current_weight,
                            'target_weight': target_weight,
                            'value_difference': value_difference,
                            'priority': abs(weight_difference)
                        }
                    else:
                        # Necesita vender
                        action = {
                            'asset': asset,
                            'action': 'SELL',
                            'current_weight': current_weight,
                            'target_weight': target_weight,
                            'value_difference': abs(value_difference),
                            'priority': abs(weight_difference)
                        }
                    
                    rebalancing_actions.append(action)
            
            # Ordenar por prioridad (mayor desviación primero)
            rebalancing_actions.sort(key=lambda x: x['priority'], reverse=True)
            
            return {
                'rebalancing_needed': len(rebalancing_actions) > 0,
                'actions': rebalancing_actions,
                'current_portfolio': current_portfolio,
                'target_weights': target_weights
            }
            
        except Exception as e:
            logger.error(f"Error sugiriendo rebalanceo: {e}")
            return {'error': str(e)}
    
    async def execute_rebalancing(self, rebalancing_plan: Dict) -> Dict:
        """Ejecutar plan de rebalanceo"""
        try:
            if not rebalancing_plan.get('rebalancing_needed', False):
                return {'message': 'No se necesita rebalanceo'}
            
            actions = rebalancing_plan['actions']
            executed_actions = []
            failed_actions = []
            
            # Ejecutar ventas primero para liberar capital
            sell_actions = [a for a in actions if a['action'] == 'SELL']
            buy_actions = [a for a in actions if a['action'] == 'BUY']
            
            # Ejecutar ventas
            for action in sell_actions:
                try:
                    asset = action['asset']
                    symbol = f"{asset}USDT" if asset != 'USDT' else None
                    
                    if symbol:
                        # Obtener cantidad actual
                        position = await self.binance_client.get_position(symbol)
                        quantity_to_sell = position.get('quantity', 0) * (
                            action['value_difference'] / 
                            (position.get('quantity', 1) * await self.binance_client.get_current_price(symbol))
                        )
                        
                        if quantity_to_sell > 0:
                            result = await self.binance_client.place_sell_order(symbol, quantity_to_sell)
                            
                            if result.get('success'):
                                executed_actions.append({
                                    'asset': asset,
                                    'action': 'SELL',
                                    'quantity': quantity_to_sell,
                                    'result': result
                                })
                            else:
                                failed_actions.append({
                                    'asset': asset,
                                    'action': 'SELL',
                                    'error': result.get('error', 'Unknown error')
                                })
                
                except Exception as e:
                    failed_actions.append({
                        'asset': action['asset'],
                        'action': 'SELL',
                        'error': str(e)
                    })
            
            # Pequeña pausa entre ventas y compras
            await asyncio.sleep(2)
            
            # Ejecutar compras
            for action in buy_actions:
                try:
                    asset = action['asset']
                    symbol = f"{asset}USDT" if asset != 'USDT' else None
                    
                    if symbol:
                        value_to_buy = action['value_difference']
                        
                        if value_to_buy > 10:  # Mínimo $10
                            result = await self.binance_client.place_buy_order(symbol, value_to_buy)
                            
                            if result.get('success'):
                                executed_actions.append({
                                    'asset': asset,
                                    'action': 'BUY',
                                    'value': value_to_buy,
                                    'result': result
                                })
                            else:
                                failed_actions.append({
                                    'asset': asset,
                                    'action': 'BUY',
                                    'error': result.get('error', 'Unknown error')
                                })
                
                except Exception as e:
                    failed_actions.append({
                        'asset': action['asset'],
                        'action': 'BUY',
                        'error': str(e)
                    })
            
            return {
                'executed_actions': executed_actions,
                'failed_actions': failed_actions,
                'total_executed': len(executed_actions),
                'total_failed': len(failed_actions),
                'success_rate': len(executed_actions) / len(actions) if actions else 0
            }
            
        except Exception as e:
            logger.error(f"Error ejecutando rebalanceo: {e}")
            return {'error': str(e)}
    
    async def get_diversification_metrics(self) -> Dict:
        """Calcular métricas de diversificación del portafolio"""
        try:
            current_portfolio = await self.get_current_portfolio()
            
            if 'error' in current_portfolio:
                return current_portfolio
            
            composition = current_portfolio['composition']
            weights = [pos['weight'] for pos in composition.values()]
            
            # Índice de Herfindahl (concentración)
            herfindahl_index = sum(w**2 for w in weights)
            
            # Número efectivo de posiciones
            effective_positions = 1 / herfindahl_index if herfindahl_index > 0 else 0
            
            # Diversification ratio (si tenemos matriz de correlación)
            diversification_ratio = 1.0
            if self.correlation_matrix is not None:
                # Calcular diversification ratio simplificado
                avg_correlation = self.correlation_matrix.values.mean()
                diversification_ratio = 1 - avg_correlation
            
            # Clasificar nivel de diversificación
            if herfindahl_index < 0.2:
                diversification_level = 'ALTA'
            elif herfindahl_index < 0.4:
                diversification_level = 'MEDIA'
            else:
                diversification_level = 'BAJA'
            
            return {
                'herfindahl_index': herfindahl_index,
                'effective_positions': effective_positions,
                'diversification_ratio': diversification_ratio,
                'diversification_level': diversification_level,
                'total_positions': len([w for w in weights if w > 0.01]),  # >1%
                'largest_position_weight': max(weights) if weights else 0,
                'portfolio_composition': composition
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas de diversificación: {e}")
            return {'error': str(e)}
    
    async def generate_portfolio_report(self) -> Dict:
        """Generar reporte completo del portafolio"""
        try:
            # Obtener datos actuales
            current_portfolio = await self.get_current_portfolio()
            diversification_metrics = await self.get_diversification_metrics()
            
            # Calcular pesos óptimos
            optimal_allocation = await self.calculate_optimal_weights()
            
            # Sugerir rebalanceo si es necesario
            rebalancing_suggestion = {}
            if 'optimal_weights' in optimal_allocation:
                rebalancing_suggestion = await self.suggest_rebalancing(
                    optimal_allocation['optimal_weights']
                )
            
            return {
                'timestamp': datetime.now(),
                'current_portfolio': current_portfolio,
                'diversification_metrics': diversification_metrics,
                'optimal_allocation': optimal_allocation,
                'rebalancing_suggestion': rebalancing_suggestion,
                'recommendations': self._generate_recommendations(
                    diversification_metrics, rebalancing_suggestion
                )
            }
            
        except Exception as e:
            logger.error(f"Error generando reporte de portafolio: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, diversification_metrics: Dict, 
                                rebalancing_suggestion: Dict) -> List[str]:
        """Generar recomendaciones basadas en análisis"""
        recommendations = []
        
        try:
            # Recomendaciones de diversificación
            diversification_level = diversification_metrics.get('diversification_level', 'UNKNOWN')
            
            if diversification_level == 'BAJA':
                recommendations.append("🔄 Aumentar diversificación - portafolio muy concentrado")
            
            largest_weight = diversification_metrics.get('largest_position_weight', 0)
            if largest_weight > 0.5:
                recommendations.append("⚠️ Reducir posición dominante - muy alta concentración")
            
            # Recomendaciones de rebalanceo
            if rebalancing_suggestion.get('rebalancing_needed', False):
                num_actions = len(rebalancing_suggestion.get('actions', []))
                recommendations.append(f"🔄 Rebalanceo recomendado - {num_actions} ajustes necesarios")
            
            # Recomendaciones generales
            effective_positions = diversification_metrics.get('effective_positions', 0)
            if effective_positions < 3:
                recommendations.append("📈 Considerar agregar más activos al portafolio")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones: {e}")
            return ["Error generando recomendaciones"]