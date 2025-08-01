#!/usr/bin/env python3
"""
Bot de Trading de Criptomonedas - Versión Google Colab
=====================================================

Bot completo de trading con:
- Controles avanzados de riesgo
- Comandos personalizables
- Interfaz web interactiva
- Integración con LLMs
- Análisis técnico automático
- Gestión de portfolio

Autor: AI Assistant
Fecha: 2024
"""

import asyncio
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_colab_environment():
    """Configurar entorno de Google Colab"""
    print("🔧 Configurando entorno de Google Colab...")
    
    # Instalar dependencias si no están disponibles
    required_packages = [
        'python-telegram-bot==20.7',
        'python-binance==1.0.19',
        'pandas==2.1.4',
        'numpy==1.24.3',
        'ta==0.10.2',
        'python-dotenv==1.0.0',
        'aiohttp==3.9.1',
        'flask==3.0.0',
        'flask-cors==4.0.0',
        'groq==0.4.1',
        'openai==1.6.1',
        'requests==2.31.0',
        'ccxt==4.2.25',
        'websocket-client==1.7.0',
        'plotly==5.17.0',
        'kaleido==0.2.1',
        'scipy==1.11.4',
        'yfinance==0.2.18',
        'discord-webhook==1.3.0',
        'slack-sdk==3.26.2',
        'pyngrok'
    ]
    
    try:
        import subprocess
        for package in required_packages:
            try:
                __import__(package.split('==')[0].replace('-', '_'))
            except ImportError:
                print(f"📦 Instalando {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        
        print("✅ Dependencias instaladas correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def create_env_file():
    """Crear archivo .env con configuración de ejemplo"""
    env_content = """# Configuración del Bot de Trading
# Copia este archivo a .env y completa con tus credenciales

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Binance API (Testnet recomendado para pruebas)
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_SECRET_KEY=your_binance_secret_key_here
BINANCE_TESTNET=True

# LLM Configuration (elige uno)
# Groq (gratuito con límites)
GROQ_API_KEY=your_groq_api_key_here

# OpenAI (opcional, de pago)
OPENAI_API_KEY=your_openai_api_key_here

# Ollama (local, gratuito)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Trading Configuration
TARGET_WEEKLY_RETURN=0.30
MAX_RISK_PER_TRADE=0.02
STOP_LOSS_PERCENTAGE=0.05
TAKE_PROFIT_PERCENTAGE=0.10

# Database
DATABASE_URL=sqlite:///trading_bot.db
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("📝 Archivo .env creado. Por favor configura tus credenciales.")
        return False
    return True

def validate_configuration():
    """Validar configuración del bot"""
    from config.settings import settings
    
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'BINANCE_API_KEY',
        'BINANCE_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Variables de configuración faltantes:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Edita el archivo .env con tus credenciales")
        return False
    
    print("✅ Configuración válida")
    return True

class TradingBotManager:
    """Gestor principal del bot de trading"""
    
    def __init__(self):
        self.telegram_bot = None
        self.web_interface = None
        self.risk_manager = None
        self.command_manager = None
        self.running = False
        
    async def initialize(self):
        """Inicializar todos los componentes del bot"""
        try:
            print("🚀 Inicializando componentes del bot...")
            
            # Importar componentes
            from src.telegram_bot import TradingBot
            from src.web_interface import WebInterface
            from src.risk_manager import RiskManager
            from src.command_manager import CommandManager
            
            # Inicializar componentes
            self.telegram_bot = TradingBot()
            self.web_interface = WebInterface()
            self.risk_manager = RiskManager()
            self.command_manager = CommandManager()
            
            # Inicializar componentes async
            await self.risk_manager.initialize()
            await self.command_manager.initialize()
            await self.web_interface.initialize()
            
            print("✅ Componentes inicializados correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error inicializando componentes: {e}")
            print(f"❌ Error: {e}")
            return False
    
    def start_telegram_bot(self):
        """Iniciar bot de Telegram en hilo separado"""
        def run_telegram():
            try:
                print("📱 Iniciando bot de Telegram...")
                self.telegram_bot.run()
            except Exception as e:
                logger.error(f"Error en bot de Telegram: {e}")
        
        telegram_thread = threading.Thread(target=run_telegram, daemon=True)
        telegram_thread.start()
        return telegram_thread
    
    def start_web_interface(self):
        """Iniciar interfaz web con ngrok"""
        try:
            from src.web_interface import start_web_interface_colab
            web_interface, public_url = start_web_interface_colab()
            self.web_interface = web_interface
            return public_url
        except Exception as e:
            logger.error(f"Error iniciando interfaz web: {e}")
            return None
    
    async def run_trading_loop(self):
        """Loop principal de trading"""
        print("💹 Iniciando loop de trading...")
        
        while self.running:
            try:
                # Verificar condiciones de riesgo
                risk_check = await self.risk_manager.check_trade_allowed("BTCUSDT", "BUY", 100)
                
                if risk_check[0].value == "EMERGENCY_STOP":
                    print("🚨 Emergency stop activado - pausando trading")
                    await asyncio.sleep(300)  # 5 minutos
                    continue
                
                # Aquí iría la lógica de trading automático
                # Por ahora solo monitoreamos
                await asyncio.sleep(60)  # 1 minuto
                
            except Exception as e:
                logger.error(f"Error en loop de trading: {e}")
                await asyncio.sleep(30)
    
    def start(self):
        """Iniciar el bot completo"""
        self.running = True
        
        # Inicializar componentes
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        if not loop.run_until_complete(self.initialize()):
            return False
        
        # Iniciar bot de Telegram
        telegram_thread = self.start_telegram_bot()
        
        # Iniciar interfaz web
        public_url = self.start_web_interface()
        
        if public_url:
            print(f"🌐 Interfaz web disponible en: {public_url}")
        
        # Iniciar loop de trading
        try:
            loop.run_until_complete(self.run_trading_loop())
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo bot...")
            self.stop()
        finally:
            loop.close()
        
        return True
    
    def stop(self):
        """Detener el bot"""
        self.running = False
        print("✅ Bot detenido")

def print_welcome_message():
    """Mostrar mensaje de bienvenida"""
    print("""
╔══════════════════════════════════════════════════════════════╗
║                     🤖 TRADING BOT                          ║
║                  Bot de Trading Avanzado                     ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  🚀 Características:                                         ║
║  • Control avanzado de riesgo con límites dinámicos         ║
║  • Comandos personalizables via Telegram                    ║
║  • Interfaz web interactiva                                 ║
║  • Integración con múltiples LLMs (Groq, OpenAI, Ollama)   ║
║  • Análisis técnico automático                              ║
║  • Gestión inteligente de portfolio                         ║
║  • Circuit breakers y emergency stop                        ║
║  • Métricas avanzadas (VaR, Sharpe, Drawdown)              ║
║                                                              ║
║  ⚠️  IMPORTANTE:                                             ║
║  • Configura tus credenciales en el archivo .env            ║
║  • Usa testnet de Binance para pruebas                      ║
║  • Nunca inviertas más de lo que puedes permitirte perder   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

def print_configuration_guide():
    """Mostrar guía de configuración"""
    print("""
📋 GUÍA DE CONFIGURACIÓN:

1️⃣ Telegram Bot:
   • Crea un bot con @BotFather en Telegram
   • Obtén el token del bot
   • Obtén tu chat ID enviando un mensaje al bot

2️⃣ Binance API:
   • Ve a tu cuenta de Binance > API Management
   • Crea una nueva API Key
   • ⚠️ IMPORTANTE: Usa Testnet para pruebas
   • Testnet: https://testnet.binance.vision/

3️⃣ LLM (Opcional):
   • Groq: Obtén API key gratuita en groq.com
   • OpenAI: API key de pago en openai.com
   • Ollama: Instala localmente (gratuito)

4️⃣ Configuración de Riesgo:
   • Pérdida máxima diaria: 2-5% (recomendado)
   • Ganancia objetivo: 10-30%
   • Máximo por posición: 5-10%
   • Stop loss: 3-5%

5️⃣ Archivos importantes:
   • .env: Configuración y credenciales
   • trading_bot.log: Logs del bot
   • trading_bot.db: Base de datos SQLite
    """)

def main():
    """Función principal"""
    print_welcome_message()
    
    # Configurar entorno
    if not setup_colab_environment():
        print("❌ Error configurando entorno")
        return
    
    # Crear archivo .env si no existe
    if not create_env_file():
        print_configuration_guide()
        print("\n⏸️  Configura tus credenciales y ejecuta nuevamente")
        return
    
    # Validar configuración
    if not validate_configuration():
        print_configuration_guide()
        return
    
    # Crear y ejecutar bot
    print("🎯 Iniciando Trading Bot...")
    bot_manager = TradingBotManager()
    
    try:
        bot_manager.start()
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego!")
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        print(f"💥 Error crítico: {e}")

def start_bot_interactive():
    """Función interactiva para Google Colab"""
    print("🚀 Iniciando Bot de Trading Interactivo...")
    
    # Configurar entorno
    setup_colab_environment()
    
    # Crear gestor del bot
    bot_manager = TradingBotManager()
    
    # Inicializar en modo interactivo
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Inicializar componentes
        success = loop.run_until_complete(bot_manager.initialize())
        if not success:
            print("❌ Error inicializando bot")
            return None
        
        # Solo iniciar interfaz web para Colab
        public_url = bot_manager.start_web_interface()
        
        if public_url:
            print(f"""
✅ Bot iniciado exitosamente!

🌐 Interfaz Web: {public_url}
📊 Dashboard: {public_url}/
⚙️ Configuración: {public_url}/risk-config
🤖 Comandos: {public_url}/commands
📈 Análisis: {public_url}/analytics

💡 Usa la interfaz web para:
• Configurar límites de riesgo
• Crear comandos personalizados
• Monitorear el portfolio
• Ejecutar trades manuales
• Ver análisis de mercado

⚠️ Recuerda configurar tus credenciales en la interfaz web
            """)
            
            return bot_manager, public_url
        else:
            print("❌ Error iniciando interfaz web")
            return None
            
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Error: {e}")
        return None
    finally:
        # No cerrar el loop para mantener la interfaz activa
        pass

# Para uso en Google Colab
def colab_start():
    """Función simple para iniciar en Colab"""
    return start_bot_interactive()

if __name__ == "__main__":
    main()