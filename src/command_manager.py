import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import re
from src.database import DatabaseManager
from src.binance_client import BinanceClient
from src.market_analyzer import MarketAnalyzer
from src.llm_advisor import LLMAdvisor

logger = logging.getLogger(__name__)

class CommandManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.binance_client = BinanceClient()
        self.market_analyzer = MarketAnalyzer()
        self.llm_advisor = LLMAdvisor()
        
        # Comandos personalizados cargados
        self.custom_commands = {}
        
        # Variables disponibles para comandos
        self.command_variables = {
            'balance': self._get_balance,
            'price': self._get_price,
            'analyze': self._analyze_symbol,
            'buy': self._execute_buy,
            'sell': self._execute_sell,
            'positions': self._get_positions,
            'stats': self._get_stats,
            'alert': self._send_alert
        }
        
        # Plantillas predefinidas
        self.command_templates = {
            'quick_buy': {
                'name': 'Compra Rápida',
                'description': 'Comprar una cantidad fija de una criptomoneda',
                'pattern': r'comprar (\w+) (\d+\.?\d*)',
                'action': 'buy_fixed_amount',
                'parameters': ['symbol', 'amount']
            },
            'stop_loss': {
                'name': 'Stop Loss',
                'description': 'Vender si el precio baja X%',
                'pattern': r'stop (\w+) (\d+\.?\d*)%',
                'action': 'stop_loss_order',
                'parameters': ['symbol', 'percentage']
            },
            'price_alert': {
                'name': 'Alerta de Precio',
                'description': 'Notificar cuando el precio alcance un valor',
                'pattern': r'alerta (\w+) (\d+\.?\d*)',
                'action': 'price_alert',
                'parameters': ['symbol', 'target_price']
            },
            'portfolio_status': {
                'name': 'Estado del Portfolio',
                'description': 'Mostrar resumen completo del portfolio',
                'pattern': r'portfolio|portafolio',
                'action': 'show_portfolio',
                'parameters': []
            }
        }

    async def initialize(self):
        """Inicializar el gestor de comandos"""
        await self._create_commands_table()
        await self._load_custom_commands()
        logger.info("Gestor de comandos inicializado")

    async def _create_commands_table(self):
        """Crear tabla para comandos personalizados"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS custom_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    pattern TEXT NOT NULL,
                    action TEXT NOT NULL,
                    parameters TEXT,
                    response_template TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error creando tabla de comandos: {e}")

    async def _load_custom_commands(self):
        """Cargar comandos personalizados desde la base de datos"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM custom_commands WHERE is_active = 1')
            rows = cursor.fetchall()
            conn.close()
            
            for row in rows:
                command_data = {
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'pattern': row[3],
                    'action': row[4],
                    'parameters': json.loads(row[5]) if row[5] else [],
                    'response_template': row[6],
                    'is_active': row[7]
                }
                self.custom_commands[row[1]] = command_data
                
            logger.info(f"Cargados {len(self.custom_commands)} comandos personalizados")
            
        except Exception as e:
            logger.error(f"Error cargando comandos: {e}")

    async def create_command(self, command_data: Dict) -> Dict:
        """Crear un nuevo comando personalizado"""
        try:
            # Validar datos
            required_fields = ['name', 'pattern', 'action']
            for field in required_fields:
                if not command_data.get(field):
                    return {'success': False, 'error': f'Campo requerido: {field}'}
            
            # Validar patrón regex
            try:
                re.compile(command_data['pattern'])
            except re.error as e:
                return {'success': False, 'error': f'Patrón regex inválido: {e}'}
            
            # Guardar en base de datos
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO custom_commands 
                (name, description, pattern, action, parameters, response_template)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                command_data['name'],
                command_data.get('description', ''),
                command_data['pattern'],
                command_data['action'],
                json.dumps(command_data.get('parameters', [])),
                command_data.get('response_template', '')
            ))
            
            conn.commit()
            command_id = cursor.lastrowid
            conn.close()
            
            # Agregar al cache
            command_data['id'] = command_id
            self.custom_commands[command_data['name']] = command_data
            
            return {'success': True, 'command_id': command_id}
            
        except Exception as e:
            logger.error(f"Error creando comando: {e}")
            return {'success': False, 'error': str(e)}

    async def update_command(self, command_id: int, command_data: Dict) -> Dict:
        """Actualizar un comando existente"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE custom_commands 
                SET name = ?, description = ?, pattern = ?, action = ?, 
                    parameters = ?, response_template = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                command_data['name'],
                command_data.get('description', ''),
                command_data['pattern'],
                command_data['action'],
                json.dumps(command_data.get('parameters', [])),
                command_data.get('response_template', ''),
                command_id
            ))
            
            conn.commit()
            conn.close()
            
            # Actualizar cache
            await self._load_custom_commands()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error actualizando comando: {e}")
            return {'success': False, 'error': str(e)}

    async def delete_command(self, command_id: int) -> Dict:
        """Eliminar un comando"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('UPDATE custom_commands SET is_active = 0 WHERE id = ?', (command_id,))
            conn.commit()
            conn.close()
            
            # Actualizar cache
            await self._load_custom_commands()
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error eliminando comando: {e}")
            return {'success': False, 'error': str(e)}

    async def get_all_commands(self) -> List[Dict]:
        """Obtener todos los comandos disponibles"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM custom_commands ORDER BY created_at DESC')
            rows = cursor.fetchall()
            conn.close()
            
            commands = []
            for row in rows:
                commands.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'pattern': row[3],
                    'action': row[4],
                    'parameters': json.loads(row[5]) if row[5] else [],
                    'response_template': row[6],
                    'is_active': bool(row[7]),
                    'created_at': row[8]
                })
            
            return commands
            
        except Exception as e:
            logger.error(f"Error obteniendo comandos: {e}")
            return []

    async def match_command(self, text: str) -> Optional[Dict]:
        """Encontrar comando que coincida con el texto"""
        for command_name, command_data in self.custom_commands.items():
            pattern = command_data['pattern']
            match = re.search(pattern, text.lower())
            
            if match:
                # Extraer parámetros
                params = {}
                if command_data.get('parameters'):
                    groups = match.groups()
                    for i, param_name in enumerate(command_data['parameters']):
                        if i < len(groups):
                            params[param_name] = groups[i]
                
                return {
                    'command': command_data,
                    'parameters': params,
                    'match': match.group(0)
                }
        
        return None

    async def execute_command(self, command_match: Dict) -> Dict:
        """Ejecutar un comando personalizado"""
        try:
            command = command_match['command']
            parameters = command_match['parameters']
            action = command['action']
            
            # Ejecutar acción según el tipo
            if action == 'buy_fixed_amount':
                return await self._execute_buy_fixed(parameters)
            elif action == 'stop_loss_order':
                return await self._execute_stop_loss(parameters)
            elif action == 'price_alert':
                return await self._create_price_alert(parameters)
            elif action == 'show_portfolio':
                return await self._show_portfolio()
            elif action == 'custom_analysis':
                return await self._custom_analysis(parameters)
            else:
                return {'success': False, 'error': f'Acción no reconocida: {action}'}
                
        except Exception as e:
            logger.error(f"Error ejecutando comando: {e}")
            return {'success': False, 'error': str(e)}

    # Funciones de variables disponibles
    async def _get_balance(self) -> Dict:
        """Obtener balance de la cuenta"""
        return await self.binance_client.get_account_balance()

    async def _get_price(self, symbol: str) -> float:
        """Obtener precio actual"""
        return await self.binance_client.get_current_price(symbol)

    async def _analyze_symbol(self, symbol: str) -> Dict:
        """Analizar símbolo"""
        return await self.market_analyzer.technical_analysis(symbol)

    async def _execute_buy(self, symbol: str, amount: float) -> Dict:
        """Ejecutar compra"""
        return await self.binance_client.place_buy_order(symbol, amount)

    async def _execute_sell(self, symbol: str, quantity: float) -> Dict:
        """Ejecutar venta"""
        return await self.binance_client.place_sell_order(symbol, quantity)

    async def _get_positions(self) -> List[Dict]:
        """Obtener posiciones abiertas"""
        return await self.binance_client.get_open_positions()

    async def _get_stats(self) -> Dict:
        """Obtener estadísticas"""
        return await self.db.get_trading_stats()

    async def _send_alert(self, message: str) -> Dict:
        """Enviar alerta"""
        # Implementar sistema de alertas
        return {'success': True, 'message': f'Alerta: {message}'}

    # Funciones de acciones específicas
    async def _execute_buy_fixed(self, params: Dict) -> Dict:
        """Ejecutar compra con cantidad fija"""
        symbol = params.get('symbol', '').upper() + 'USDT'
        amount = float(params.get('amount', 0))
        
        if amount <= 0:
            return {'success': False, 'error': 'Cantidad inválida'}
        
        result = await self.binance_client.place_buy_order(symbol, amount)
        
        if result['success']:
            return {
                'success': True,
                'message': f"✅ Compra ejecutada: {result['quantity']} {symbol} por ${result['total']:.2f}"
            }
        else:
            return {'success': False, 'error': result['error']}

    async def _execute_stop_loss(self, params: Dict) -> Dict:
        """Ejecutar orden de stop loss"""
        symbol = params.get('symbol', '').upper() + 'USDT'
        percentage = float(params.get('percentage', 0))
        
        # Obtener posición actual
        position = await self.binance_client.get_position(symbol)
        
        if position['quantity'] == 0:
            return {'success': False, 'error': f'No tienes posición en {symbol}'}
        
        # Calcular precio de stop loss
        current_price = await self.binance_client.get_current_price(symbol)
        stop_price = current_price * (1 - percentage / 100)
        
        # Guardar orden en base de datos para monitoreo
        await self._save_stop_order(symbol, stop_price, position['quantity'])
        
        return {
            'success': True,
            'message': f"🛡️ Stop Loss configurado para {symbol} en ${stop_price:.4f} (-{percentage}%)"
        }

    async def _create_price_alert(self, params: Dict) -> Dict:
        """Crear alerta de precio"""
        symbol = params.get('symbol', '').upper() + 'USDT'
        target_price = float(params.get('target_price', 0))
        
        # Guardar alerta en base de datos
        await self._save_price_alert(symbol, target_price)
        
        return {
            'success': True,
            'message': f"🔔 Alerta configurada: {symbol} cuando alcance ${target_price:.4f}"
        }

    async def _show_portfolio(self) -> Dict:
        """Mostrar resumen del portfolio"""
        try:
            balance = await self.binance_client.get_account_balance()
            positions = await self.binance_client.get_open_positions()
            stats = await self.db.get_trading_stats(7)
            
            total_value = 0
            for pos in positions:
                total_value += pos['current_value']
            
            portfolio_summary = f"""
📊 **Resumen del Portfolio**

💰 **Balance:**
• USDT: {balance.get('USDT', {}).get('total', 0):.2f}
• Valor total posiciones: ${total_value:.2f}

📈 **Posiciones Abiertas:** {len(positions)}
{chr(10).join([f"• {pos['symbol']}: {pos['quantity']:.4f} (${pos['current_value']:.2f})" for pos in positions[:5]])}

📊 **Estadísticas (7 días):**
• Total trades: {stats.get('total_trades', 0)}
• Volumen: ${stats.get('net_flow', 0):.2f}
• Trade promedio: ${stats.get('avg_trade_size', 0):.2f}
            """
            
            return {'success': True, 'message': portfolio_summary}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def _custom_analysis(self, params: Dict) -> Dict:
        """Análisis personalizado"""
        symbol = params.get('symbol', '').upper() + 'USDT'
        
        # Realizar análisis completo
        market_data = await self.market_analyzer.get_market_data(symbol)
        technical_analysis = await self.market_analyzer.technical_analysis(symbol)
        ai_advice = await self.llm_advisor.get_trading_advice(symbol, market_data, technical_analysis)
        
        analysis_summary = f"""
🔍 **Análisis de {symbol}**

💰 Precio: ${market_data.get('price', 0):.4f}
📈 Cambio 24h: {market_data.get('change_24h', 0):.2f}%
🔧 Score técnico: {technical_analysis.get('score', 0):.1f}/10

🤖 **Recomendación IA:** {ai_advice.get('recommendation', 'N/A')}
🎯 Confianza: {ai_advice.get('confidence', 0)}%
💡 {ai_advice.get('reasoning', 'Sin análisis disponible')}
        """
        
        return {'success': True, 'message': analysis_summary}

    async def _save_stop_order(self, symbol: str, stop_price: float, quantity: float):
        """Guardar orden de stop loss para monitoreo"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stop_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    stop_price REAL NOT NULL,
                    quantity REAL NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO stop_orders (symbol, stop_price, quantity)
                VALUES (?, ?, ?)
            ''', (symbol, stop_price, quantity))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando stop order: {e}")

    async def _save_price_alert(self, symbol: str, target_price: float):
        """Guardar alerta de precio"""
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    status TEXT DEFAULT 'ACTIVE',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO price_alerts (symbol, target_price)
                VALUES (?, ?)
            ''', (symbol, target_price))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error guardando alerta: {e}")

    def get_command_templates(self) -> Dict:
        """Obtener plantillas de comandos predefinidas"""
        return self.command_templates

    async def import_template(self, template_name: str) -> Dict:
        """Importar una plantilla como comando personalizado"""
        if template_name not in self.command_templates:
            return {'success': False, 'error': 'Plantilla no encontrada'}
        
        template = self.command_templates[template_name]
        command_data = {
            'name': template['name'],
            'description': template['description'],
            'pattern': template['pattern'],
            'action': template['action'],
            'parameters': template['parameters']
        }
        
        return await self.create_command(command_data)