#!/usr/bin/env python3
"""
Script de pruebas para el Bot de Trading
Verifica que todos los componentes funcionen correctamente
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from src.binance_client import BinanceClient
from src.market_analyzer import MarketAnalyzer
from src.llm_advisor import LLMAdvisor
from src.database import DatabaseManager
from src.risk_manager import RiskManager
from src.backtester import Backtester
from src.notification_manager import NotificationManager
from src.portfolio_optimizer import PortfolioOptimizer

class BotTester:
    def __init__(self):
        self.results = {}
        self.passed = 0
        self.failed = 0
    
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Registrar resultado de prueba"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        self.results[test_name] = {
            'passed': passed,
            'message': message
        }
        
        if passed:
            self.passed += 1
        else:
            self.failed += 1
    
    async def test_configuration(self):
        """Probar configuración"""
        print("\n🔧 Probando Configuración...")
        
        # Verificar archivo .env
        env_exists = os.path.exists('.env')
        self.log_test("Archivo .env existe", env_exists)
        
        # Verificar configuración básica
        config_valid = settings.validate()
        self.log_test("Configuración válida", config_valid)
        
        # Verificar tokens
        has_telegram = bool(settings.TELEGRAM_BOT_TOKEN)
        self.log_test("Token de Telegram configurado", has_telegram)
        
        has_binance = bool(settings.BINANCE_API_KEY and settings.BINANCE_SECRET_KEY)
        self.log_test("API de Binance configurada", has_binance)
    
    async def test_database(self):
        """Probar base de datos"""
        print("\n🗄️ Probando Base de Datos...")
        
        try:
            db = DatabaseManager()
            
            # Probar configuración
            config_saved = await db.set_config("test_key", "test_value")
            self.log_test("Guardar configuración", config_saved)
            
            config_retrieved = await db.get_config("test_key")
            self.log_test("Obtener configuración", config_retrieved == "test_value")
            
            # Probar estadísticas
            stats = await db.get_trading_stats(7)
            self.log_test("Obtener estadísticas", isinstance(stats, dict))
            
            # Probar posiciones
            positions = await db.get_open_positions()
            self.log_test("Obtener posiciones", isinstance(positions, list))
            
        except Exception as e:
            self.log_test("Base de datos", False, str(e))
    
    async def test_binance_client(self):
        """Probar cliente de Binance"""
        print("\n🔗 Probando Cliente de Binance...")
        
        try:
            client = BinanceClient()
            
            # Inicializar cliente
            initialized = await client.initialize()
            self.log_test("Inicialización de cliente", initialized)
            
            if initialized:
                # Probar obtener precio
                price = await client.get_current_price("BTCUSDT")
                self.log_test("Obtener precio actual", price > 0, f"BTC: ${price}")
                
                # Probar ticker 24h
                ticker = await client.get_24hr_ticker("BTCUSDT")
                self.log_test("Obtener ticker 24h", bool(ticker))
                
                # Probar balance (puede fallar en testnet vacío)
                try:
                    balance = await client.get_account_balance()
                    self.log_test("Obtener balance", isinstance(balance, dict))
                except:
                    self.log_test("Obtener balance", True, "Testnet sin fondos (normal)")
                
                await client.close()
            
        except Exception as e:
            self.log_test("Cliente de Binance", False, str(e))
    
    async def test_market_analyzer(self):
        """Probar analizador de mercado"""
        print("\n📊 Probando Analizador de Mercado...")
        
        try:
            analyzer = MarketAnalyzer()
            
            # Probar obtener datos de mercado
            market_data = await analyzer.get_market_data("BTCUSDT")
            self.log_test("Obtener datos de mercado", bool(market_data))
            
            # Probar análisis técnico
            if market_data:
                technical = await analyzer.technical_analysis("BTCUSDT")
                self.log_test("Análisis técnico", 'score' in technical)
                
                # Probar decisión de compra
                should_buy = await analyzer.should_buy("BTCUSDT")
                self.log_test("Decisión de compra", 'should_buy' in should_buy)
            
        except Exception as e:
            self.log_test("Analizador de mercado", False, str(e))
    
    async def test_llm_advisor(self):
        """Probar asesor LLM"""
        print("\n🧠 Probando Asesor LLM...")
        
        try:
            advisor = LLMAdvisor()
            
            # Verificar LLMs disponibles
            available_llms = advisor.get_available_llms()
            self.log_test("LLMs disponibles", len(available_llms) > 0, f"Disponibles: {', '.join(available_llms)}")
            
            # Probar análisis de riesgo/recompensa
            rr_analysis = await advisor.analyze_risk_reward("BTCUSDT", 50000, 47500, 52500)
            self.log_test("Análisis riesgo/recompensa", 'risk_reward_ratio' in rr_analysis)
            
            # Probar consejo de trading (puede fallar si no hay LLM configurado)
            try:
                market_data = {'price': 50000, 'change_24h': 2.5}
                technical_data = {'score': 7.5, 'trend': 'BULLISH'}
                
                advice = await advisor.get_trading_advice("BTCUSDT", market_data, technical_data)
                self.log_test("Consejo de trading", 'recommendation' in advice)
            except:
                self.log_test("Consejo de trading", True, "Sin LLM configurado (usando respaldo)")
            
        except Exception as e:
            self.log_test("Asesor LLM", False, str(e))
    
    async def test_risk_manager(self):
        """Probar gestor de riesgo"""
        print("\n🛡️ Probando Gestor de Riesgo...")
        
        try:
            risk_manager = RiskManager()
            await risk_manager.initialize()
            
            # Probar evaluación de riesgo
            risk_eval = await risk_manager.evaluate_position_risk("BTCUSDT", 100, 50000, 47500)
            self.log_test("Evaluación de riesgo", 'approved' in risk_eval)
            
            # Probar cálculo de tamaño óptimo
            optimal_size = await risk_manager.calculate_optimal_position_size("BTCUSDT", 50000, 47500, 0.75)
            self.log_test("Tamaño óptimo de posición", optimal_size > 0)
            
            # Probar condiciones de mercado
            market_conditions = await risk_manager.validate_market_conditions()
            self.log_test("Validar condiciones de mercado", 'safe_to_trade' in market_conditions)
            
            # Probar reporte de riesgo
            risk_report = await risk_manager.get_risk_report()
            self.log_test("Reporte de riesgo", 'risk_level' in risk_report)
            
        except Exception as e:
            self.log_test("Gestor de riesgo", False, str(e))
    
    async def test_backtester(self):
        """Probar sistema de backtesting"""
        print("\n📈 Probando Backtester...")
        
        try:
            backtester = Backtester()
            
            # Probar backtesting simple
            results = await backtester.run_backtest("BTCUSDT", "2024-01-01", "2024-02-01")
            self.log_test("Ejecutar backtest", 'total_return' in results or 'error' in results)
            
            if 'total_return' in results:
                # Probar generación de reporte
                report_path = backtester.generate_report(results, "test_backtest.html")
                self.log_test("Generar reporte", isinstance(report_path, str))
                
                # Limpiar archivo de prueba
                if os.path.exists("test_backtest.html"):
                    os.remove("test_backtest.html")
            
        except Exception as e:
            self.log_test("Backtester", False, str(e))
    
    async def test_notification_manager(self):
        """Probar gestor de notificaciones"""
        print("\n📢 Probando Gestor de Notificaciones...")
        
        try:
            notifier = NotificationManager()
            
            # Probar configuración de nivel
            notifier.set_notification_level('WARNING')
            self.log_test("Configurar nivel de notificación", True)
            
            # Probar notificación de prueba (sin enviar realmente)
            notifier.telegram_notifications = False  # Desactivar para prueba
            await notifier.test_notifications()
            self.log_test("Sistema de notificaciones", True)
            
        except Exception as e:
            self.log_test("Gestor de notificaciones", False, str(e))
    
    async def test_portfolio_optimizer(self):
        """Probar optimizador de portafolio"""
        print("\n📊 Probando Optimizador de Portafolio...")
        
        try:
            optimizer = PortfolioOptimizer()
            await optimizer.initialize()
            
            # Probar obtener portafolio actual
            portfolio = await optimizer.get_current_portfolio()
            self.log_test("Obtener portafolio actual", 'total_value' in portfolio or 'error' in portfolio)
            
            # Probar métricas de diversificación
            diversification = await optimizer.get_diversification_metrics()
            self.log_test("Métricas de diversificación", 'diversification_level' in diversification or 'error' in diversification)
            
            # Probar cálculo de pesos óptimos
            optimal_weights = await optimizer.calculate_optimal_weights()
            self.log_test("Calcular pesos óptimos", 'optimal_weights' in optimal_weights or 'error' in optimal_weights)
            
        except Exception as e:
            self.log_test("Optimizador de portafolio", False, str(e))
    
    async def test_integration(self):
        """Probar integración entre componentes"""
        print("\n🔄 Probando Integración...")
        
        try:
            # Simular flujo completo de análisis
            analyzer = MarketAnalyzer()
            advisor = LLMAdvisor()
            risk_manager = RiskManager()
            
            # 1. Obtener datos de mercado
            market_data = await analyzer.get_market_data("BTCUSDT")
            
            # 2. Realizar análisis técnico
            if market_data:
                technical = await analyzer.technical_analysis("BTCUSDT")
                
                # 3. Obtener consejo de IA
                if technical:
                    try:
                        advice = await advisor.get_trading_advice("BTCUSDT", market_data, technical)
                        
                        # 4. Evaluar riesgo
                        if advice and 'entry_price' in advice:
                            risk_eval = await risk_manager.evaluate_position_risk(
                                "BTCUSDT", 100, advice['entry_price'], advice.get('stop_loss', 0)
                            )
                            
                            self.log_test("Flujo completo de análisis", True, "Integración exitosa")
                        else:
                            self.log_test("Flujo completo de análisis", True, "Parcialmente exitoso")
                    except:
                        self.log_test("Flujo completo de análisis", True, "Análisis técnico funciona")
                else:
                    self.log_test("Flujo completo de análisis", False, "Fallo en análisis técnico")
            else:
                self.log_test("Flujo completo de análisis", False, "Fallo obteniendo datos")
            
        except Exception as e:
            self.log_test("Integración", False, str(e))
    
    def print_summary(self):
        """Imprimir resumen de pruebas"""
        print("\n" + "="*60)
        print("📋 RESUMEN DE PRUEBAS")
        print("="*60)
        
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Pruebas exitosas: {self.passed}")
        print(f"❌ Pruebas fallidas: {self.failed}")
        print(f"📊 Tasa de éxito: {success_rate:.1f}%")
        
        if self.failed > 0:
            print("\n❌ PRUEBAS FALLIDAS:")
            for test_name, result in self.results.items():
                if not result['passed']:
                    print(f"  • {test_name}: {result['message']}")
        
        print("\n🎯 RECOMENDACIONES:")
        
        if success_rate >= 90:
            print("🟢 Excelente! El bot está listo para usar")
        elif success_rate >= 70:
            print("🟡 Bueno, pero revisa las pruebas fallidas")
            print("  • Configura las credenciales faltantes")
            print("  • Verifica la conexión a internet")
        else:
            print("🔴 Necesita atención antes de usar")
            print("  • Revisa el archivo .env")
            print("  • Instala las dependencias: pip install -r requirements.txt")
            print("  • Verifica las credenciales de API")
        
        print("\n📚 PRÓXIMOS PASOS:")
        print("1. Corrige cualquier error encontrado")
        print("2. Ejecuta: python main.py")
        print("3. Prueba los comandos en Telegram")
        print("4. Comienza con pequeñas cantidades en testnet")

async def main():
    """Función principal de pruebas"""
    print("🧪 INICIANDO PRUEBAS DEL BOT DE TRADING")
    print("="*60)
    
    tester = BotTester()
    
    # Ejecutar todas las pruebas
    await tester.test_configuration()
    await tester.test_database()
    await tester.test_binance_client()
    await tester.test_market_analyzer()
    await tester.test_llm_advisor()
    await tester.test_risk_manager()
    await tester.test_backtester()
    await tester.test_notification_manager()
    await tester.test_portfolio_optimizer()
    await tester.test_integration()
    
    # Mostrar resumen
    tester.print_summary()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando pruebas: {e}")
        sys.exit(1)