import sqlite3
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
from config.settings import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_path = settings.DATABASE_URL.replace('sqlite:///', '')
        self._init_database()
    
    def _init_database(self):
        """Inicializar base de datos y crear tablas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Tabla de trades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total REAL NOT NULL,
                    timestamp INTEGER NOT NULL,
                    status TEXT DEFAULT 'COMPLETED',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de análisis
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analysis_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    analysis_data TEXT NOT NULL,
                    llm_advice TEXT,
                    timestamp INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de configuración
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de estadísticas diarias
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    profitable_trades INTEGER DEFAULT 0,
                    total_profit_loss REAL DEFAULT 0,
                    total_volume REAL DEFAULT 0,
                    best_trade REAL DEFAULT 0,
                    worst_trade REAL DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Tabla de posiciones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    quantity REAL NOT NULL,
                    avg_entry_price REAL NOT NULL,
                    current_price REAL DEFAULT 0,
                    unrealized_pnl REAL DEFAULT 0,
                    status TEXT DEFAULT 'OPEN',
                    opened_at DATETIME NOT NULL,
                    closed_at DATETIME,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Base de datos inicializada correctamente")
            
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
    
    async def save_trade(self, trade_data: Dict) -> bool:
        """Guardar un trade en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades 
                (order_id, symbol, side, quantity, price, total, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('order_id'),
                trade_data.get('symbol'),
                trade_data.get('side'),
                trade_data.get('quantity'),
                trade_data.get('price'),
                trade_data.get('total'),
                trade_data.get('timestamp', int(datetime.now().timestamp() * 1000))
            ))
            
            conn.commit()
            conn.close()
            
            # Actualizar estadísticas
            await self._update_daily_stats(trade_data)
            
            logger.info(f"Trade guardado: {trade_data.get('symbol')} {trade_data.get('side')}")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando trade: {e}")
            return False
    
    async def save_analysis(self, symbol: str, analysis_data: Dict, llm_advice: Dict = None) -> bool:
        """Guardar análisis en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO analysis_history 
                (symbol, analysis_data, llm_advice, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (
                symbol,
                json.dumps(analysis_data),
                json.dumps(llm_advice) if llm_advice else None,
                int(datetime.now().timestamp() * 1000)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error guardando análisis: {e}")
            return False
    
    async def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Obtener trades de la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if symbol:
                cursor.execute('''
                    SELECT * FROM trades 
                    WHERE symbol = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (symbol, limit))
            else:
                cursor.execute('''
                    SELECT * FROM trades 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            # Convertir a diccionarios
            trades = []
            columns = ['id', 'order_id', 'symbol', 'side', 'quantity', 'price', 'total', 'timestamp', 'status', 'created_at']
            
            for row in rows:
                trade = dict(zip(columns, row))
                trades.append(trade)
            
            return trades
            
        except Exception as e:
            logger.error(f"Error obteniendo trades: {e}")
            return []
    
    async def get_trading_stats(self, days: int = 7) -> Dict:
        """Obtener estadísticas de trading"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Fecha límite
            since_timestamp = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            # Estadísticas básicas
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN side = 'BUY' THEN total ELSE -total END) as net_flow,
                    AVG(total) as avg_trade_size,
                    MIN(total) as min_trade,
                    MAX(total) as max_trade
                FROM trades 
                WHERE timestamp >= ?
            ''', (since_timestamp,))
            
            stats = cursor.fetchone()
            
            # Trades por símbolo
            cursor.execute('''
                SELECT symbol, COUNT(*) as count, SUM(total) as volume
                FROM trades 
                WHERE timestamp >= ?
                GROUP BY symbol
                ORDER BY count DESC
            ''', (since_timestamp,))
            
            symbol_stats = cursor.fetchall()
            
            # Trades por día
            cursor.execute('''
                SELECT 
                    DATE(datetime(timestamp/1000, 'unixepoch')) as date,
                    COUNT(*) as trades,
                    SUM(total) as volume
                FROM trades 
                WHERE timestamp >= ?
                GROUP BY date
                ORDER BY date DESC
            ''', (since_timestamp,))
            
            daily_stats = cursor.fetchall()
            
            conn.close()
            
            return {
                'period_days': days,
                'total_trades': stats[0] if stats[0] else 0,
                'net_flow': stats[1] if stats[1] else 0,
                'avg_trade_size': stats[2] if stats[2] else 0,
                'min_trade': stats[3] if stats[3] else 0,
                'max_trade': stats[4] if stats[4] else 0,
                'symbol_stats': [
                    {'symbol': row[0], 'trades': row[1], 'volume': row[2]} 
                    for row in symbol_stats
                ],
                'daily_stats': [
                    {'date': row[0], 'trades': row[1], 'volume': row[2]} 
                    for row in daily_stats
                ]
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {}
    
    async def _update_daily_stats(self, trade_data: Dict):
        """Actualizar estadísticas diarias"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Obtener estadísticas actuales del día
            cursor.execute('SELECT * FROM daily_stats WHERE date = ?', (today,))
            current_stats = cursor.fetchone()
            
            if current_stats:
                # Actualizar estadísticas existentes
                cursor.execute('''
                    UPDATE daily_stats 
                    SET total_trades = total_trades + 1,
                        total_volume = total_volume + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE date = ?
                ''', (trade_data.get('total', 0), today))
            else:
                # Crear nuevas estadísticas
                cursor.execute('''
                    INSERT INTO daily_stats (date, total_trades, total_volume)
                    VALUES (?, 1, ?)
                ''', (today, trade_data.get('total', 0)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error actualizando estadísticas diarias: {e}")
    
    async def update_position(self, symbol: str, quantity: float, entry_price: float):
        """Actualizar o crear posición"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verificar si existe posición
            cursor.execute('SELECT * FROM positions WHERE symbol = ? AND status = "OPEN"', (symbol,))
            existing = cursor.fetchone()
            
            if existing:
                # Actualizar posición existente
                old_quantity = existing[2]
                old_avg_price = existing[3]
                
                # Calcular nuevo promedio
                total_cost = (old_quantity * old_avg_price) + (quantity * entry_price)
                new_quantity = old_quantity + quantity
                new_avg_price = total_cost / new_quantity if new_quantity != 0 else 0
                
                if new_quantity == 0:
                    # Cerrar posición
                    cursor.execute('''
                        UPDATE positions 
                        SET status = "CLOSED", closed_at = CURRENT_TIMESTAMP
                        WHERE symbol = ? AND status = "OPEN"
                    ''', (symbol,))
                else:
                    # Actualizar posición
                    cursor.execute('''
                        UPDATE positions 
                        SET quantity = ?, avg_entry_price = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE symbol = ? AND status = "OPEN"
                    ''', (new_quantity, new_avg_price, symbol))
            else:
                # Crear nueva posición
                cursor.execute('''
                    INSERT INTO positions (symbol, quantity, avg_entry_price, opened_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (symbol, quantity, entry_price))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando posición: {e}")
            return False
    
    async def get_open_positions(self) -> List[Dict]:
        """Obtener posiciones abiertas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM positions 
                WHERE status = "OPEN" AND quantity > 0
                ORDER BY opened_at DESC
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            positions = []
            columns = ['id', 'symbol', 'quantity', 'avg_entry_price', 'current_price', 
                      'unrealized_pnl', 'status', 'opened_at', 'closed_at', 'updated_at']
            
            for row in rows:
                position = dict(zip(columns, row))
                positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error obteniendo posiciones: {e}")
            return []
    
    async def calculate_portfolio_performance(self) -> Dict:
        """Calcular rendimiento del portafolio"""
        try:
            stats = await self.get_trading_stats(30)  # Últimos 30 días
            
            total_trades = stats.get('total_trades', 0)
            if total_trades == 0:
                return {
                    'total_return': 0,
                    'win_rate': 0,
                    'avg_return_per_trade': 0,
                    'sharpe_ratio': 0,
                    'max_drawdown': 0,
                    'total_trades': 0
                }
            
            # Calcular métricas básicas
            # Nota: Para un cálculo más preciso, necesitaríamos rastrear el P&L de cada trade
            net_flow = stats.get('net_flow', 0)
            avg_trade_size = stats.get('avg_trade_size', 0)
            
            # Estimación básica de rendimiento
            estimated_return = net_flow / (avg_trade_size * total_trades) if avg_trade_size > 0 else 0
            
            return {
                'total_return': estimated_return,
                'win_rate': 0.5,  # Placeholder - necesita cálculo real
                'avg_return_per_trade': estimated_return / total_trades if total_trades > 0 else 0,
                'total_trades': total_trades,
                'total_volume': stats.get('net_flow', 0),
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error calculando rendimiento: {e}")
            return {}
    
    async def get_config(self, key: str) -> Optional[str]:
        """Obtener valor de configuración"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT value FROM bot_config WHERE key = ?', (key,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.error(f"Error obteniendo configuración: {e}")
            return None
    
    async def set_config(self, key: str, value: str) -> bool:
        """Establecer valor de configuración"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO bot_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Error estableciendo configuración: {e}")
            return False
    
    async def cleanup_old_data(self, days_to_keep: int = 90):
        """Limpiar datos antiguos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cutoff_timestamp = int((datetime.now() - timedelta(days=days_to_keep)).timestamp() * 1000)
            
            # Limpiar análisis antiguos
            cursor.execute('DELETE FROM analysis_history WHERE timestamp < ?', (cutoff_timestamp,))
            
            # Limpiar estadísticas diarias antiguas
            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')
            cursor.execute('DELETE FROM daily_stats WHERE date < ?', (cutoff_date,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Datos antiguos limpiados (>{days_to_keep} días)")
            return True
            
        except Exception as e:
            logger.error(f"Error limpiando datos: {e}")
            return False