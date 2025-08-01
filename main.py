#!/usr/bin/env python3
"""
Bot de Trading de Criptomonedas
Controlado por Telegram con análisis IA
Objetivo: 30% ganancia semanal
"""

import asyncio
import logging
import schedule
import time
from datetime import datetime
from threading import Thread
from config.settings import settings
from src.telegram_bot import TradingBot
from src.trading_strategy import TradingStrategy

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBotManager:
    def __init__(self):
        self.telegram_bot = TradingBot()
        self.trading_strategy = TradingStrategy()
        self.running = False
        
    async def initialize(self):
        """Inicializar todos los componentes"""
        try:
            logger.info("Inicializando bot de trading...")
            
            # Validar configuración
            if not settings.validate():
                logger.error("Configuración incompleta. Revisa el archivo .env")
                return False
            
            # Inicializar estrategia de trading
            await self.trading_strategy.initialize()
            
            logger.info("Bot de trading inicializado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando bot: {e}")
            return False
    
    async def run_trading_cycle(self):
        """Ejecutar ciclo de trading automático"""
        try:
            logger.info("Ejecutando ciclo de trading...")
            
            # Ejecutar estrategia de trading
            results = await self.trading_strategy.run_trading_cycle()
            
            # Log de resultados
            logger.info(f"Ciclo completado: {results.get('trades_executed', 0)} trades ejecutados")
            
            if results.get('errors'):
                for error in results['errors']:
                    logger.error(f"Error en ciclo: {error}")
            
            # Enviar resumen por Telegram si hay actividad
            if results.get('trades_executed', 0) > 0 or results.get('actions_taken'):
                await self.send_trading_summary(results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error en ciclo de trading: {e}")
            return {'error': str(e)}
    
    async def send_trading_summary(self, results: dict):
        """Enviar resumen de trading por Telegram"""
        try:
            if not settings.TELEGRAM_CHAT_ID:
                return
            
            performance = await self.trading_strategy.get_performance_summary()
            
            message = f"""
📊 **Resumen de Trading**

🔄 Trades ejecutados: {results.get('trades_executed', 0)}
📈 Oportunidades encontradas: {results.get('opportunities_found', 0)}
👁️ Posiciones monitoreadas: {results.get('positions_monitored', 0)}

💰 **Rendimiento:**
• P&L diario: ${performance.get('daily_pnl', 0):.2f}
• P&L semanal: ${performance.get('weekly_pnl', 0):.2f}
• Progreso objetivo: {performance.get('weekly_progress_pct', 0):.1f}%
• Posiciones activas: {performance.get('active_positions', 0)}

⚡ **Acciones tomadas:**
            """
            
            for action in results.get('actions_taken', []):
                symbol = action.get('symbol', 'N/A')
                action_type = action.get('type', 'N/A')
                action_name = action.get('action', 'N/A')
                
                if action_type == 'STOP_LOSS':
                    message += f"🛑 Stop Loss: {symbol}\n"
                elif action_type == 'TAKE_PROFIT':
                    message += f"🎯 Take Profit: {symbol}\n"
                elif action_type == 'NEW_TRADE':
                    message += f"✨ Nuevo trade: {action_name} {symbol}\n"
            
            # Enviar mensaje (implementar en telegram_bot.py)
            # await self.telegram_bot.send_message(settings.TELEGRAM_CHAT_ID, message)
            
        except Exception as e:
            logger.error(f"Error enviando resumen: {e}")
    
    def schedule_trading(self):
        """Programar ejecución automática de trading"""
        # Ejecutar cada 15 minutos durante horas de mercado
        schedule.every(15).minutes.do(lambda: asyncio.run(self.run_trading_cycle()))
        
        # Resumen diario a las 8:00 AM
        schedule.every().day.at("08:00").do(lambda: asyncio.run(self.send_daily_summary()))
        
        # Limpieza de datos cada domingo a las 2:00 AM
        schedule.every().sunday.at("02:00").do(lambda: asyncio.run(self.cleanup_data()))
        
        logger.info("Trading programado cada 15 minutos")
    
    async def send_daily_summary(self):
        """Enviar resumen diario"""
        try:
            performance = await self.trading_strategy.get_performance_summary()
            
            message = f"""
🌅 **Resumen Diario**

📊 **Estadísticas del día:**
• Trades realizados: {performance.get('trades_today', 0)}
• P&L diario: ${performance.get('daily_pnl', 0):.2f}
• Posiciones activas: {performance.get('active_positions', 0)}

📈 **Progreso semanal:**
• P&L semanal: ${performance.get('weekly_pnl', 0):.2f}
• Objetivo: ${performance.get('weekly_target', 0):.2f}
• Progreso: {performance.get('weekly_progress_pct', 0):.1f}%

🎯 **Objetivo:** 30% ganancia semanal
            """
            
            logger.info("Resumen diario generado")
            
        except Exception as e:
            logger.error(f"Error enviando resumen diario: {e}")
    
    async def cleanup_data(self):
        """Limpiar datos antiguos"""
        try:
            await self.trading_strategy.db.cleanup_old_data(90)
            logger.info("Limpieza de datos completada")
        except Exception as e:
            logger.error(f"Error en limpieza de datos: {e}")
    
    def run_scheduler(self):
        """Ejecutar programador en hilo separado"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    async def start(self):
        """Iniciar el bot completo"""
        try:
            # Inicializar
            if not await self.initialize():
                return
            
            self.running = True
            
            # Programar trading automático
            self.schedule_trading()
            
            # Iniciar programador en hilo separado
            scheduler_thread = Thread(target=self.run_scheduler, daemon=True)
            scheduler_thread.start()
            
            logger.info("Iniciando bot de Telegram...")
            
            # Ejecutar bot de Telegram (bloquea el hilo principal)
            self.telegram_bot.run()
            
        except KeyboardInterrupt:
            logger.info("Deteniendo bot...")
            self.running = False
        except Exception as e:
            logger.error(f"Error ejecutando bot: {e}")
            self.running = False

async def main():
    """Función principal"""
    try:
        # Banner de inicio
        print("""
╔══════════════════════════════════════════════════════════════╗
║                    BOT DE TRADING CRYPTO                     ║
║                                                              ║
║  🤖 Control por Telegram                                     ║
║  📊 Análisis técnico automático                              ║
║  🧠 Asesoramiento con IA                                     ║
║  🎯 Objetivo: 30% ganancia semanal                           ║
║  ⚡ Gestión de riesgo inteligente                            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        # Verificar configuración
        if not settings.validate():
            print("❌ Error: Configuración incompleta")
            print("1. Copia .env.example a .env")
            print("2. Completa las credenciales necesarias")
            print("3. Ejecuta el bot nuevamente")
            return
        
        print("✅ Configuración válida")
        print(f"🔗 Binance Testnet: {'Sí' if settings.BINANCE_TESTNET else 'No'}")
        print(f"🎯 Objetivo semanal: {settings.TARGET_WEEKLY_RETURN*100}%")
        print(f"🛡️ Riesgo máximo por trade: {settings.MAX_RISK_PER_TRADE*100}%")
        print()
        
        # Crear y ejecutar bot
        bot_manager = TradingBotManager()
        await bot_manager.start()
        
    except Exception as e:
        logger.error(f"Error en función principal: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot detenido por el usuario")
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        logger.error(f"Error fatal: {e}")