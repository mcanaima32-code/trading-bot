import asyncio
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import os
from typing import Dict, Any

from src.risk_manager import RiskManager, RiskLimits
from src.command_manager import CommandManager
from src.binance_client import BinanceClient
from src.market_analyzer import MarketAnalyzer
from src.database import DatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)

class WebInterface:
    def __init__(self):
        self.app = Flask(__name__, 
                        template_folder='../templates',
                        static_folder='../static')
        CORS(self.app)
        
        # Componentes del bot
        self.risk_manager = RiskManager()
        self.command_manager = CommandManager()
        self.binance_client = BinanceClient()
        self.market_analyzer = MarketAnalyzer()
        self.db = DatabaseManager()
        
        # Estado de la interfaz
        self.bot_status = {
            'running': False,
            'auto_trading': False,
            'last_update': datetime.now()
        }
        
        self._setup_routes()

    def _setup_routes(self):
        """Configurar rutas de la aplicación web"""
        
        @self.app.route('/')
        def dashboard():
            """Dashboard principal"""
            return render_template('dashboard.html')
        
        @self.app.route('/risk-config')
        def risk_config():
            """Página de configuración de riesgo"""
            return render_template('risk_config.html')
        
        @self.app.route('/commands')
        def commands():
            """Página de comandos personalizados"""
            return render_template('commands.html')
        
        @self.app.route('/analytics')
        def analytics():
            """Página de análisis y métricas"""
            return render_template('analytics.html')
        
        # API Routes
        @self.app.route('/api/status')
        def api_status():
            """Estado general del bot"""
            return jsonify(self._get_bot_status())
        
        @self.app.route('/api/risk/dashboard')
        def api_risk_dashboard():
            """Dashboard de riesgo"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                dashboard_data = loop.run_until_complete(self.risk_manager.get_risk_dashboard())
                loop.close()
                return jsonify(dashboard_data)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/risk/limits', methods=['GET', 'POST'])
        def api_risk_limits():
            """Obtener/actualizar límites de riesgo"""
            if request.method == 'GET':
                return jsonify(self.risk_manager.risk_limits.to_dict())
            
            elif request.method == 'POST':
                try:
                    new_limits = request.json
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self.risk_manager.update_risk_limits(new_limits))
                    loop.close()
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/risk/reset-emergency', methods=['POST'])
        def api_reset_emergency():
            """Resetear emergency stop"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.risk_manager.reset_emergency_stop())
                loop.close()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/commands', methods=['GET'])
        def api_get_commands():
            """Obtener todos los comandos"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                commands = loop.run_until_complete(self.command_manager.get_all_commands())
                templates = self.command_manager.get_command_templates()
                loop.close()
                return jsonify({
                    'commands': commands,
                    'templates': templates
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/commands', methods=['POST'])
        def api_create_command():
            """Crear nuevo comando"""
            try:
                command_data = request.json
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.command_manager.create_command(command_data))
                loop.close()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/commands/<int:command_id>', methods=['PUT', 'DELETE'])
        def api_manage_command(command_id):
            """Actualizar o eliminar comando"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if request.method == 'PUT':
                    command_data = request.json
                    result = loop.run_until_complete(self.command_manager.update_command(command_id, command_data))
                elif request.method == 'DELETE':
                    result = loop.run_until_complete(self.command_manager.delete_command(command_id))
                
                loop.close()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/commands/import-template', methods=['POST'])
        def api_import_template():
            """Importar plantilla como comando"""
            try:
                template_name = request.json.get('template_name')
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(self.command_manager.import_template(template_name))
                loop.close()
                return jsonify(result)
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/market/analysis')
        def api_market_analysis():
            """Análisis de mercado"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                analysis_results = []
                for symbol in settings.TRADING_PAIRS[:5]:
                    market_data = loop.run_until_complete(self.market_analyzer.get_market_data(symbol))
                    technical_analysis = loop.run_until_complete(self.market_analyzer.technical_analysis(symbol))
                    
                    analysis_results.append({
                        'symbol': symbol,
                        'price': market_data.get('price', 0),
                        'change_24h': market_data.get('change_24h', 0),
                        'volume_24h': market_data.get('volume_24h', 0),
                        'technical_score': technical_analysis.get('score', 0),
                        'trend': technical_analysis.get('trend', 'NEUTRAL'),
                        'indicators': technical_analysis.get('indicators', {})
                    })
                
                loop.close()
                return jsonify(analysis_results)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/portfolio')
        def api_portfolio():
            """Estado del portfolio"""
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                balance = loop.run_until_complete(self.binance_client.get_account_balance())
                positions = loop.run_until_complete(self.binance_client.get_open_positions())
                stats = loop.run_until_complete(self.db.get_trading_stats(7))
                
                loop.close()
                
                return jsonify({
                    'balance': balance,
                    'positions': positions,
                    'stats': stats
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/trades')
        def api_trades():
            """Historial de trades"""
            try:
                limit = request.args.get('limit', 50, type=int)
                symbol = request.args.get('symbol', None)
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                trades = loop.run_until_complete(self.db.get_trades(symbol, limit))
                loop.close()
                
                return jsonify(trades)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/bot/toggle', methods=['POST'])
        def api_toggle_bot():
            """Activar/desactivar bot"""
            try:
                action = request.json.get('action')  # 'start' or 'stop'
                
                if action == 'start':
                    self.bot_status['running'] = True
                    self.bot_status['auto_trading'] = True
                elif action == 'stop':
                    self.bot_status['running'] = False
                    self.bot_status['auto_trading'] = False
                
                self.bot_status['last_update'] = datetime.now()
                
                return jsonify({
                    'success': True,
                    'status': self.bot_status
                })
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @self.app.route('/api/execute-trade', methods=['POST'])
        def api_execute_trade():
            """Ejecutar trade manual"""
            try:
                trade_data = request.json
                symbol = trade_data.get('symbol')
                side = trade_data.get('side')  # 'BUY' or 'SELL'
                amount = float(trade_data.get('amount', 0))
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Verificar riesgo
                risk_check = loop.run_until_complete(
                    self.risk_manager.check_trade_allowed(symbol, side, amount)
                )
                
                if risk_check[0].value not in ['ALLOW', 'WARN']:
                    loop.close()
                    return jsonify({
                        'success': False,
                        'error': f'Trade bloqueado: {risk_check[1]}'
                    })
                
                # Ejecutar trade
                if side == 'BUY':
                    result = loop.run_until_complete(
                        self.binance_client.place_buy_order(symbol, amount)
                    )
                else:
                    # Para venta, necesitamos la cantidad en lugar del monto
                    position = loop.run_until_complete(self.binance_client.get_position(symbol))
                    result = loop.run_until_complete(
                        self.binance_client.place_sell_order(symbol, position['quantity'])
                    )
                
                # Guardar en base de datos
                if result.get('success'):
                    loop.run_until_complete(self.db.save_trade(result))
                
                loop.close()
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500

    def _get_bot_status(self) -> Dict[str, Any]:
        """Obtener estado actual del bot"""
        return {
            'running': self.bot_status['running'],
            'auto_trading': self.bot_status['auto_trading'],
            'last_update': self.bot_status['last_update'].isoformat(),
            'risk_level': self.risk_manager.risk_metrics.risk_level.value,
            'trading_paused': self.risk_manager.trading_paused,
            'emergency_stop': self.risk_manager.emergency_stop
        }

    async def initialize(self):
        """Inicializar componentes"""
        try:
            await self.risk_manager.initialize()
            await self.command_manager.initialize()
            await self.binance_client.initialize()
            logger.info("Interfaz web inicializada")
        except Exception as e:
            logger.error(f"Error inicializando interfaz web: {e}")

    def run(self, host='0.0.0.0', port=5000, debug=False):
        """Ejecutar servidor web"""
        try:
            # Inicializar componentes en un hilo separado
            def init_components():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.initialize())
                loop.close()
            
            init_thread = threading.Thread(target=init_components)
            init_thread.daemon = True
            init_thread.start()
            init_thread.join(timeout=30)
            
            logger.info(f"Iniciando servidor web en http://{host}:{port}")
            self.app.run(host=host, port=port, debug=debug, threaded=True)
            
        except Exception as e:
            logger.error(f"Error ejecutando servidor web: {e}")

# Función para usar en Google Colab
def start_web_interface_colab():
    """Iniciar interfaz web optimizada para Google Colab"""
    try:
        # Instalar ngrok si no está disponible
        try:
            from pyngrok import ngrok
        except ImportError:
            import subprocess
            import sys
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
            from pyngrok import ngrok
        
        # Crear interfaz web
        web_interface = WebInterface()
        
        # Iniciar servidor en un hilo separado
        def run_server():
            web_interface.run(host='0.0.0.0', port=5000, debug=False)
        
        server_thread = threading.Thread(target=run_server)
        server_thread.daemon = True
        server_thread.start()
        
        # Esperar un momento para que el servidor inicie
        import time
        time.sleep(3)
        
        # Crear túnel ngrok
        public_url = ngrok.connect(5000)
        
        print("🚀 Bot de Trading - Interfaz Web Iniciada")
        print("=" * 50)
        print(f"🌐 URL Pública: {public_url}")
        print(f"🔧 URL Local: http://localhost:5000")
        print("=" * 50)
        print("📊 Funciones disponibles:")
        print("• Dashboard principal: /")
        print("• Configuración de riesgo: /risk-config")
        print("• Comandos personalizados: /commands")
        print("• Análisis y métricas: /analytics")
        print("=" * 50)
        
        return web_interface, public_url
        
    except Exception as e:
        logger.error(f"Error iniciando interfaz web para Colab: {e}")
        return None, None

if __name__ == "__main__":
    # Para desarrollo local
    web_interface = WebInterface()
    web_interface.run(debug=True)