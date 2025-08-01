import asyncio
import logging
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional, Tuple, Any
import json
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
from src.database import DatabaseManager
from src.binance_client import BinanceClient
from config.settings import settings

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TradeAction(Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"
    EMERGENCY_STOP = "EMERGENCY_STOP"

@dataclass
class RiskLimits:
    """Configuración de límites de riesgo"""
    # Límites diarios
    max_daily_loss_pct: float = 5.0  # Pérdida máxima diaria en %
    max_daily_gain_pct: float = 15.0  # Ganancia máxima diaria en % (para tomar ganancias)
    max_daily_trades: int = 20  # Número máximo de trades por día
    max_daily_volume: float = 1000.0  # Volumen máximo diario en USDT
    
    # Límites por trade
    max_position_size_pct: float = 10.0  # Tamaño máximo de posición en % del capital
    max_risk_per_trade_pct: float = 2.0  # Riesgo máximo por trade en %
    min_risk_reward_ratio: float = 1.5  # Ratio mínimo riesgo/recompensa
    
    # Límites de exposición
    max_total_exposure_pct: float = 50.0  # Exposición máxima total en %
    max_correlation_exposure: float = 30.0  # Exposición máxima a activos correlacionados
    max_positions_per_asset: int = 3  # Máximo de posiciones por activo
    
    # Límites de drawdown
    max_drawdown_pct: float = 10.0  # Drawdown máximo permitido
    max_consecutive_losses: int = 5  # Máximo de pérdidas consecutivas
    
    # Horarios de trading
    trading_start_hour: int = 6  # Hora de inicio (UTC)
    trading_end_hour: int = 22  # Hora de fin (UTC)
    weekend_trading: bool = True  # Permitir trading en fines de semana
    
    # Circuit breakers
    volatility_threshold: float = 20.0  # Umbral de volatilidad para pausar trading
    market_crash_threshold: float = -15.0  # Caída del mercado para emergency stop
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'RiskLimits':
        return cls(**data)

@dataclass
class RiskMetrics:
    """Métricas actuales de riesgo"""
    current_daily_pnl: float = 0.0
    current_daily_pnl_pct: float = 0.0
    daily_trades_count: int = 0
    daily_volume: float = 0.0
    total_exposure_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    consecutive_losses: int = 0
    var_1d: float = 0.0  # Value at Risk 1 día
    sharpe_ratio: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    last_updated: datetime = None

class RiskManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.binance_client = BinanceClient()
        
        # Configuración de riesgo actual
        self.risk_limits = RiskLimits()
        self.risk_metrics = RiskMetrics()
        
        # Estado interno
        self.trading_paused = False
        self.emergency_stop = False
        self.last_risk_check = datetime.now()
        
        # Historial para cálculos
        self.daily_pnl_history = []
        self.trade_history = []
        
        # Alertas enviadas (para evitar spam)
        self.alerts_sent = set()

    async def initialize(self):
        """Inicializar el gestor de riesgo"""
        await self._create_risk_tables()
        await self._load_risk_configuration()
        await self._calculate_current_metrics()
        logger.info("Gestor de riesgo inicializado")

    async def _create_risk_tables(self):
        """Crear tablas para gestión de riesgo"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Tabla de configuración de riesgo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_name TEXT UNIQUE NOT NULL,
                    config_data TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de métricas de riesgo diarias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_risk_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    starting_balance REAL NOT NULL,
                    ending_balance REAL NOT NULL,
                    daily_pnl REAL NOT NULL,
                    daily_pnl_pct REAL NOT NULL,
                    max_drawdown REAL NOT NULL,
                    trades_count INTEGER NOT NULL,
                    volume REAL NOT NULL,
                    var_1d REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de alertas de riesgo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metric_value REAL,
                    threshold_value REAL,
                    action_taken TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de circuit breakers
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS circuit_breakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger_type TEXT NOT NULL,
                    trigger_value REAL NOT NULL,
                    threshold REAL NOT NULL,
                    action TEXT NOT NULL,
                    duration_minutes INTEGER,
                    triggered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME,
                    status TEXT DEFAULT 'ACTIVE'
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creando tablas de riesgo: {e}")

    async def _load_risk_configuration(self):
        """Cargar configuración de riesgo desde la base de datos"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT config_data FROM risk_config 
                WHERE config_name = 'default' AND is_active = 1
            ''')
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                config_data = json.loads(result[0])
                self.risk_limits = RiskLimits.from_dict(config_data)
            else:
                # Guardar configuración por defecto
                await self.save_risk_configuration('default', self.risk_limits)
                
        except Exception as e:
            logger.error(f"Error cargando configuración de riesgo: {e}")

    async def save_risk_configuration(self, config_name: str, risk_limits: RiskLimits) -> bool:
        """Guardar configuración de riesgo"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO risk_config (config_name, config_data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (config_name, json.dumps(risk_limits.to_dict())))
            
            conn.commit()
            conn.close()
            
            # Actualizar configuración actual si es la por defecto
            if config_name == 'default':
                self.risk_limits = risk_limits
                
            logger.info(f"Configuración de riesgo '{config_name}' guardada")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando configuración de riesgo: {e}")
            return False

    async def _calculate_current_metrics(self):
        """Calcular métricas actuales de riesgo"""
        try:
            # Obtener balance actual
            balance = await self.binance_client.get_account_balance()
            current_balance = balance.get('USDT', {}).get('total', 0)
            
            # Obtener estadísticas del día
            today = datetime.now().strftime('%Y-%m-%d')
            stats = await self.db.get_trading_stats(1)
            
            # Calcular P&L diario
            daily_pnl = stats.get('net_flow', 0)
            daily_pnl_pct = (daily_pnl / current_balance * 100) if current_balance > 0 else 0
            
            # Obtener posiciones abiertas
            positions = await self.binance_client.get_open_positions()
            total_exposure = sum(pos['current_value'] for pos in positions)
            exposure_pct = (total_exposure / current_balance * 100) if current_balance > 0 else 0
            
            # Calcular drawdown
            drawdown = await self._calculate_current_drawdown()
            
            # Contar pérdidas consecutivas
            consecutive_losses = await self._count_consecutive_losses()
            
            # Calcular VaR (Value at Risk)
            var_1d = await self._calculate_var()
            
            # Determinar nivel de riesgo
            risk_level = self._determine_risk_level(daily_pnl_pct, exposure_pct, drawdown)
            
            # Actualizar métricas
            self.risk_metrics = RiskMetrics(
                current_daily_pnl=daily_pnl,
                current_daily_pnl_pct=daily_pnl_pct,
                daily_trades_count=stats.get('total_trades', 0),
                daily_volume=abs(stats.get('net_flow', 0)),
                total_exposure_pct=exposure_pct,
                current_drawdown_pct=drawdown,
                consecutive_losses=consecutive_losses,
                var_1d=var_1d,
                risk_level=risk_level,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error calculando métricas de riesgo: {e}")

    async def _calculate_current_drawdown(self) -> float:
        """Calcular drawdown actual"""
        try:
            # Obtener historial de balance de los últimos 30 días
            stats = await self.db.get_trading_stats(30)
            daily_stats = stats.get('daily_stats', [])
            
            if not daily_stats:
                return 0.0
            
            # Calcular balance acumulado
            balances = []
            cumulative_pnl = 0
            
            for day_stat in reversed(daily_stats):  # Más reciente primero
                cumulative_pnl += day_stat.get('volume', 0)
                balances.append(cumulative_pnl)
            
            if not balances:
                return 0.0
            
            # Calcular drawdown máximo
            peak = balances[0]
            max_drawdown = 0
            
            for balance in balances:
                if balance > peak:
                    peak = balance
                drawdown = (peak - balance) / peak * 100 if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            return max_drawdown
            
        except Exception as e:
            logger.error(f"Error calculando drawdown: {e}")
            return 0.0

    async def _count_consecutive_losses(self) -> int:
        """Contar pérdidas consecutivas"""
        try:
            trades = await self.db.get_trades(limit=20)
            consecutive_losses = 0
            
            for trade in trades:
                # Determinar si fue pérdida (simplificado)
                if trade['side'] == 'SELL':
                    # Aquí necesitaríamos comparar con el precio de compra
                    # Por simplicidad, asumimos pérdida si el volumen es menor al promedio
                    pass
                else:
                    break
            
            return consecutive_losses
            
        except Exception as e:
            logger.error(f"Error contando pérdidas consecutivas: {e}")
            return 0

    async def _calculate_var(self) -> float:
        """Calcular Value at Risk (VaR) a 1 día con confianza del 95%"""
        try:
            # Obtener retornos diarios de los últimos 30 días
            stats = await self.db.get_trading_stats(30)
            daily_stats = stats.get('daily_stats', [])
            
            if len(daily_stats) < 5:
                return 0.0
            
            returns = []
            for i in range(1, len(daily_stats)):
                prev_volume = daily_stats[i-1].get('volume', 0)
                curr_volume = daily_stats[i].get('volume', 0)
                if prev_volume > 0:
                    daily_return = (curr_volume - prev_volume) / prev_volume
                    returns.append(daily_return)
            
            if not returns:
                return 0.0
            
            # Calcular VaR al 95% de confianza
            returns_array = np.array(returns)
            var_95 = np.percentile(returns_array, 5) * 100  # 5% peor caso
            
            return abs(var_95)
            
        except Exception as e:
            logger.error(f"Error calculando VaR: {e}")
            return 0.0

    def _determine_risk_level(self, daily_pnl_pct: float, exposure_pct: float, drawdown: float) -> RiskLevel:
        """Determinar nivel de riesgo actual"""
        # Factores de riesgo
        risk_factors = 0
        
        # P&L diario
        if abs(daily_pnl_pct) > self.risk_limits.max_daily_loss_pct * 0.8:
            risk_factors += 2
        elif abs(daily_pnl_pct) > self.risk_limits.max_daily_loss_pct * 0.5:
            risk_factors += 1
        
        # Exposición
        if exposure_pct > self.risk_limits.max_total_exposure_pct * 0.8:
            risk_factors += 2
        elif exposure_pct > self.risk_limits.max_total_exposure_pct * 0.5:
            risk_factors += 1
        
        # Drawdown
        if drawdown > self.risk_limits.max_drawdown_pct * 0.8:
            risk_factors += 2
        elif drawdown > self.risk_limits.max_drawdown_pct * 0.5:
            risk_factors += 1
        
        # Determinar nivel
        if risk_factors >= 4:
            return RiskLevel.CRITICAL
        elif risk_factors >= 3:
            return RiskLevel.HIGH
        elif risk_factors >= 1:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    async def check_trade_allowed(self, symbol: str, side: str, amount: float) -> Tuple[TradeAction, str]:
        """Verificar si un trade está permitido según los límites de riesgo"""
        try:
            await self._calculate_current_metrics()
            
            # Verificar emergency stop
            if self.emergency_stop:
                return TradeAction.EMERGENCY_STOP, "Trading detenido por emergency stop"
            
            # Verificar si trading está pausado
            if self.trading_paused:
                return TradeAction.BLOCK, "Trading pausado por límites de riesgo"
            
            # Verificar horario de trading
            current_hour = datetime.now().hour
            if not (self.risk_limits.trading_start_hour <= current_hour <= self.risk_limits.trading_end_hour):
                if not self.risk_limits.weekend_trading and datetime.now().weekday() >= 5:
                    return TradeAction.BLOCK, "Trading fuera de horario permitido"
            
            # Verificar límites diarios
            if self.risk_metrics.current_daily_pnl_pct <= -self.risk_limits.max_daily_loss_pct:
                await self._trigger_circuit_breaker("daily_loss_limit", self.risk_metrics.current_daily_pnl_pct)
                return TradeAction.EMERGENCY_STOP, f"Límite de pérdida diaria alcanzado: {self.risk_metrics.current_daily_pnl_pct:.2f}%"
            
            if self.risk_metrics.current_daily_pnl_pct >= self.risk_limits.max_daily_gain_pct:
                return TradeAction.WARN, f"Límite de ganancia diaria alcanzado: {self.risk_metrics.current_daily_pnl_pct:.2f}%"
            
            # Verificar número de trades diarios
            if self.risk_metrics.daily_trades_count >= self.risk_limits.max_daily_trades:
                return TradeAction.BLOCK, f"Límite de trades diarios alcanzado: {self.risk_metrics.daily_trades_count}"
            
            # Verificar volumen diario
            if self.risk_metrics.daily_volume >= self.risk_limits.max_daily_volume:
                return TradeAction.BLOCK, f"Límite de volumen diario alcanzado: ${self.risk_metrics.daily_volume:.2f}"
            
            # Verificar tamaño de posición
            balance = await self.binance_client.get_account_balance()
            current_balance = balance.get('USDT', {}).get('total', 0)
            position_size_pct = (amount / current_balance * 100) if current_balance > 0 else 0
            
            if position_size_pct > self.risk_limits.max_position_size_pct:
                return TradeAction.BLOCK, f"Tamaño de posición excede el límite: {position_size_pct:.2f}%"
            
            # Verificar exposición total
            if side == 'BUY' and self.risk_metrics.total_exposure_pct + position_size_pct > self.risk_limits.max_total_exposure_pct:
                return TradeAction.BLOCK, f"Exposición total excedería el límite: {self.risk_metrics.total_exposure_pct + position_size_pct:.2f}%"
            
            # Verificar drawdown
            if self.risk_metrics.current_drawdown_pct > self.risk_limits.max_drawdown_pct:
                await self._trigger_circuit_breaker("max_drawdown", self.risk_metrics.current_drawdown_pct)
                return TradeAction.EMERGENCY_STOP, f"Drawdown máximo excedido: {self.risk_metrics.current_drawdown_pct:.2f}%"
            
            # Verificar pérdidas consecutivas
            if self.risk_metrics.consecutive_losses >= self.risk_limits.max_consecutive_losses:
                return TradeAction.WARN, f"Múltiples pérdidas consecutivas: {self.risk_metrics.consecutive_losses}"
            
            # Verificar nivel de riesgo
            if self.risk_metrics.risk_level == RiskLevel.CRITICAL:
                return TradeAction.BLOCK, "Nivel de riesgo crítico - trading bloqueado"
            elif self.risk_metrics.risk_level == RiskLevel.HIGH:
                return TradeAction.WARN, "Nivel de riesgo alto - proceder con precaución"
            
            return TradeAction.ALLOW, "Trade permitido"
            
        except Exception as e:
            logger.error(f"Error verificando trade: {e}")
            return TradeAction.BLOCK, f"Error en verificación de riesgo: {str(e)}"

    async def _trigger_circuit_breaker(self, trigger_type: str, trigger_value: float):
        """Activar circuit breaker"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            # Determinar acción y duración
            if trigger_type == "daily_loss_limit":
                action = "PAUSE_TRADING"
                duration = 60  # 1 hora
                threshold = self.risk_limits.max_daily_loss_pct
            elif trigger_type == "max_drawdown":
                action = "EMERGENCY_STOP"
                duration = 1440  # 24 horas
                threshold = self.risk_limits.max_drawdown_pct
            else:
                action = "PAUSE_TRADING"
                duration = 30
                threshold = 0
            
            # Guardar circuit breaker
            cursor.execute('''
                INSERT INTO circuit_breakers 
                (trigger_type, trigger_value, threshold, action, duration_minutes)
                VALUES (?, ?, ?, ?, ?)
            ''', (trigger_type, trigger_value, threshold, action, duration))
            
            conn.commit()
            conn.close()
            
            # Aplicar acción
            if action == "EMERGENCY_STOP":
                self.emergency_stop = True
                await self._send_risk_alert("CRITICAL", f"Emergency stop activado: {trigger_type}", trigger_value, threshold)
            elif action == "PAUSE_TRADING":
                self.trading_paused = True
                await self._send_risk_alert("HIGH", f"Trading pausado: {trigger_type}", trigger_value, threshold)
            
            logger.warning(f"Circuit breaker activado: {trigger_type} = {trigger_value}")
            
        except Exception as e:
            logger.error(f"Error activando circuit breaker: {e}")

    async def _send_risk_alert(self, severity: str, message: str, metric_value: float, threshold_value: float):
        """Enviar alerta de riesgo"""
        try:
            # Evitar spam de alertas
            alert_key = f"{severity}_{message}"
            if alert_key in self.alerts_sent:
                return
            
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_alerts 
                (alert_type, severity, message, metric_value, threshold_value, action_taken)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ("RISK_LIMIT", severity, message, metric_value, threshold_value, "NOTIFICATION_SENT"))
            
            conn.commit()
            conn.close()
            
            self.alerts_sent.add(alert_key)
            logger.warning(f"Alerta de riesgo: {severity} - {message}")
            
        except Exception as e:
            logger.error(f"Error enviando alerta: {e}")

    async def update_risk_limits(self, new_limits: Dict) -> Dict:
        """Actualizar límites de riesgo dinámicamente"""
        try:
            # Validar límites
            validation_result = self._validate_risk_limits(new_limits)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Actualizar configuración
            updated_limits = RiskLimits.from_dict({**self.risk_limits.to_dict(), **new_limits})
            
            # Guardar en base de datos
            success = await self.save_risk_configuration('default', updated_limits)
            
            if success:
                self.risk_limits = updated_limits
                logger.info(f"Límites de riesgo actualizados: {new_limits}")
                return {'success': True, 'message': 'Límites actualizados correctamente'}
            else:
                return {'success': False, 'error': 'Error guardando configuración'}
                
        except Exception as e:
            logger.error(f"Error actualizando límites: {e}")
            return {'success': False, 'error': str(e)}

    def _validate_risk_limits(self, limits: Dict) -> Dict:
        """Validar que los límites sean razonables"""
        errors = []
        
        # Validar límites diarios
        if 'max_daily_loss_pct' in limits:
            if not (0 < limits['max_daily_loss_pct'] <= 50):
                errors.append("Pérdida diaria máxima debe estar entre 0.1% y 50%")
        
        if 'max_daily_gain_pct' in limits:
            if not (1 <= limits['max_daily_gain_pct'] <= 100):
                errors.append("Ganancia diaria máxima debe estar entre 1% y 100%")
        
        # Validar límites de posición
        if 'max_position_size_pct' in limits:
            if not (0.1 <= limits['max_position_size_pct'] <= 50):
                errors.append("Tamaño máximo de posición debe estar entre 0.1% y 50%")
        
        # Validar exposición
        if 'max_total_exposure_pct' in limits:
            if not (1 <= limits['max_total_exposure_pct'] <= 100):
                errors.append("Exposición total máxima debe estar entre 1% y 100%")
        
        # Validar horarios
        if 'trading_start_hour' in limits:
            if not (0 <= limits['trading_start_hour'] <= 23):
                errors.append("Hora de inicio debe estar entre 0 y 23")
        
        if 'trading_end_hour' in limits:
            if not (0 <= limits['trading_end_hour'] <= 23):
                errors.append("Hora de fin debe estar entre 0 y 23")
        
        return {
            'valid': len(errors) == 0,
            'error': '; '.join(errors) if errors else None
        }

    async def get_risk_dashboard(self) -> Dict:
        """Obtener datos para el dashboard de riesgo"""
        await self._calculate_current_metrics()
        
        return {
            'risk_limits': self.risk_limits.to_dict(),
            'risk_metrics': {
                'current_daily_pnl': self.risk_metrics.current_daily_pnl,
                'current_daily_pnl_pct': self.risk_metrics.current_daily_pnl_pct,
                'daily_trades_count': self.risk_metrics.daily_trades_count,
                'daily_volume': self.risk_metrics.daily_volume,
                'total_exposure_pct': self.risk_metrics.total_exposure_pct,
                'current_drawdown_pct': self.risk_metrics.current_drawdown_pct,
                'consecutive_losses': self.risk_metrics.consecutive_losses,
                'var_1d': self.risk_metrics.var_1d,
                'risk_level': self.risk_metrics.risk_level.value,
                'last_updated': self.risk_metrics.last_updated.isoformat() if self.risk_metrics.last_updated else None
            },
            'status': {
                'trading_paused': self.trading_paused,
                'emergency_stop': self.emergency_stop,
                'active_circuit_breakers': await self._get_active_circuit_breakers()
            },
            'recent_alerts': await self._get_recent_alerts()
        }

    async def _get_active_circuit_breakers(self) -> List[Dict]:
        """Obtener circuit breakers activos"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM circuit_breakers 
                WHERE status = 'ACTIVE' 
                ORDER BY triggered_at DESC
                LIMIT 10
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            breakers = []
            for row in rows:
                breakers.append({
                    'id': row[0],
                    'trigger_type': row[1],
                    'trigger_value': row[2],
                    'threshold': row[3],
                    'action': row[4],
                    'duration_minutes': row[5],
                    'triggered_at': row[6]
                })
            
            return breakers
            
        except Exception as e:
            logger.error(f"Error obteniendo circuit breakers: {e}")
            return []

    async def _get_recent_alerts(self) -> List[Dict]:
        """Obtener alertas recientes"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM risk_alerts 
                ORDER BY created_at DESC
                LIMIT 20
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            alerts = []
            for row in rows:
                alerts.append({
                    'id': row[0],
                    'alert_type': row[1],
                    'severity': row[2],
                    'message': row[3],
                    'metric_value': row[4],
                    'threshold_value': row[5],
                    'action_taken': row[6],
                    'resolved': bool(row[7]),
                    'created_at': row[8]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return []

    async def reset_emergency_stop(self) -> Dict:
        """Resetear emergency stop manualmente"""
        try:
            self.emergency_stop = False
            self.trading_paused = False
            
            # Marcar circuit breakers como resueltos
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE circuit_breakers 
                SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP
                WHERE status = 'ACTIVE'
            ''')
            
            conn.commit()
            conn.close()
            
            logger.info("Emergency stop reseteado manualmente")
            return {'success': True, 'message': 'Emergency stop reseteado'}
            
        except Exception as e:
            logger.error(f"Error reseteando emergency stop: {e}")
            return {'success': False, 'error': str(e)}

    async def save_daily_metrics(self):
        """Guardar métricas diarias al final del día"""
        try:
            await self._calculate_current_metrics()
            
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            balance = await self.binance_client.get_account_balance()
            current_balance = balance.get('USDT', {}).get('total', 0)
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_risk_metrics 
                (date, starting_balance, ending_balance, daily_pnl, daily_pnl_pct, 
                 max_drawdown, trades_count, volume, var_1d, risk_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                today,
                current_balance - self.risk_metrics.current_daily_pnl,
                current_balance,
                self.risk_metrics.current_daily_pnl,
                self.risk_metrics.current_daily_pnl_pct,
                self.risk_metrics.current_drawdown_pct,
                self.risk_metrics.daily_trades_count,
                self.risk_metrics.daily_volume,
                self.risk_metrics.var_1d,
                self.risk_metrics.risk_level.value
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Métricas diarias guardadas para {today}")
            
        except Exception as e:
            logger.error(f"Error guardando métricas diarias: {e}")

    def get_risk_summary(self) -> str:
        """Obtener resumen de riesgo para mostrar en Telegram"""
        return f"""
🛡️ **Resumen de Riesgo**

📊 **Métricas Actuales:**
• P&L Diario: {self.risk_metrics.current_daily_pnl:.2f} USDT ({self.risk_metrics.current_daily_pnl_pct:.2f}%)
• Trades Hoy: {self.risk_metrics.daily_trades_count}/{self.risk_limits.max_daily_trades}
• Exposición Total: {self.risk_metrics.total_exposure_pct:.1f}%
• Drawdown: {self.risk_metrics.current_drawdown_pct:.2f}%
• Nivel de Riesgo: {self.risk_metrics.risk_level.value}

⚙️ **Límites Configurados:**
• Pérdida Máxima Diaria: {self.risk_limits.max_daily_loss_pct:.1f}%
• Ganancia Máxima Diaria: {self.risk_limits.max_daily_gain_pct:.1f}%
• Exposición Máxima: {self.risk_limits.max_total_exposure_pct:.1f}%

🚨 **Estado:**
• Trading Pausado: {'Sí' if self.trading_paused else 'No'}
• Emergency Stop: {'Sí' if self.emergency_stop else 'No'}
        """.strip()