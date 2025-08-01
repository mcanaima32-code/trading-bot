import asyncio
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config.settings import settings
from src.binance_client import BinanceClient
from src.market_analyzer import MarketAnalyzer
from src.llm_advisor import LLMAdvisor
from src.database import DatabaseManager

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.binance_client = BinanceClient()
        self.market_analyzer = MarketAnalyzer()
        self.llm_advisor = LLMAdvisor()
        self.db = DatabaseManager()
        self.trading_active = False
        
        # Comandos disponibles
        self.commands = {
            '/start': 'Iniciar el bot',
            '/status': 'Ver estado del bot y balance',
            '/analizar': 'Analizar mercado actual',
            '/comprar': 'Ejecutar orden de compra',
            '/vender': 'Ejecutar orden de venta',
            '/balance': 'Ver balance actual',
            '/posiciones': 'Ver posiciones abiertas',
            '/activar': 'Activar trading automático',
            '/desactivar': 'Desactivar trading automático',
            '/configurar': 'Configurar parámetros',
            '/historial': 'Ver historial de trades',
            '/ayuda': 'Mostrar comandos disponibles'
        }

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        welcome_message = """
🤖 **Bot de Trading Crypto**

¡Bienvenido! Este bot te ayuda a hacer trading en Binance con análisis IA.

**Características:**
• 📊 Análisis técnico automático
• 🤖 Asesoramiento con IA
• 💰 Objetivo: 30% ganancia semanal
• ⚡ Control por Telegram

Usa /ayuda para ver todos los comandos.
        """
        
        keyboard = [
            [InlineKeyboardButton("📊 Analizar Mercado", callback_data="analizar")],
            [InlineKeyboardButton("💰 Ver Balance", callback_data="balance")],
            [InlineKeyboardButton("⚙️ Configurar", callback_data="configurar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ayuda"""
        help_text = "**Comandos disponibles:**\n\n"
        for command, description in self.commands.items():
            help_text += f"{command} - {description}\n"
        
        help_text += "\n**Palabras clave:**\n"
        help_text += "• 'comprar [SYMBOL]' - Comprar criptomoneda\n"
        help_text += "• 'vender [SYMBOL]' - Vender criptomoneda\n"
        help_text += "• 'analizar [SYMBOL]' - Analizar criptomoneda específica\n"
        help_text += "• 'precio [SYMBOL]' - Ver precio actual\n"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /status"""
        try:
            # Obtener balance
            balance = await self.binance_client.get_account_balance()
            
            # Estado del bot
            status_emoji = "🟢" if self.trading_active else "🔴"
            status_text = "ACTIVO" if self.trading_active else "INACTIVO"
            
            message = f"""
📊 **Estado del Bot**

{status_emoji} Trading: {status_text}
💰 Balance USDT: {balance.get('USDT', 0):.2f}
📈 Posiciones abiertas: {len(await self.get_open_positions())}

**Configuración actual:**
• 🎯 Objetivo semanal: {settings.TARGET_WEEKLY_RETURN*100:.1f}%
• 🛡️ Riesgo máximo: {settings.MAX_RISK_PER_TRADE*100:.1f}%
• 🔻 Stop Loss: {settings.STOP_LOSS_PERCENTAGE*100:.1f}%
• 🔺 Take Profit: {settings.TAKE_PROFIT_PERCENTAGE*100:.1f}%
            """
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error al obtener estado: {str(e)}")

    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /analizar"""
        await update.message.reply_text("🔍 Analizando mercado...")
        
        try:
            # Analizar top 5 criptomonedas
            analysis_results = []
            
            for symbol in settings.TRADING_PAIRS[:5]:
                # Obtener datos de mercado
                market_data = await self.market_analyzer.get_market_data(symbol)
                
                # Análisis técnico
                technical_analysis = await self.market_analyzer.technical_analysis(symbol)
                
                # Consultar IA
                ai_advice = await self.llm_advisor.get_trading_advice(symbol, market_data, technical_analysis)
                
                analysis_results.append({
                    'symbol': symbol,
                    'price': market_data['price'],
                    'change_24h': market_data['change_24h'],
                    'technical_score': technical_analysis['score'],
                    'ai_recommendation': ai_advice['recommendation'],
                    'confidence': ai_advice['confidence']
                })
            
            # Formatear mensaje
            message = "📊 **Análisis de Mercado**\n\n"
            
            for result in analysis_results:
                emoji = "🟢" if result['change_24h'] > 0 else "🔴"
                message += f"{emoji} **{result['symbol']}**\n"
                message += f"💰 Precio: ${result['price']:.4f}\n"
                message += f"📈 24h: {result['change_24h']:.2f}%\n"
                message += f"🔧 Score técnico: {result['technical_score']:.1f}/10\n"
                message += f"🤖 IA: {result['ai_recommendation']} ({result['confidence']:.0f}%)\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error en análisis: {str(e)}")

    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /comprar"""
        if not context.args:
            await update.message.reply_text("❌ Especifica el símbolo: /comprar BTCUSDT")
            return
        
        symbol = context.args[0].upper()
        
        try:
            # Verificar si es seguro comprar
            analysis = await self.market_analyzer.should_buy(symbol)
            
            if analysis['should_buy']:
                # Ejecutar compra
                result = await self.binance_client.place_buy_order(symbol, analysis['suggested_amount'])
                
                if result['success']:
                    message = f"""
✅ **Orden de compra ejecutada**

💰 {symbol}
📊 Cantidad: {result['quantity']}
💵 Precio: ${result['price']}
💸 Total: ${result['total']}
                    """
                    
                    # Guardar en base de datos
                    await self.db.save_trade(result)
                    
                else:
                    message = f"❌ Error en la compra: {result['error']}"
            else:
                message = f"⚠️ No recomendado comprar {symbol} ahora\nRazón: {analysis['reason']}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def sell_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /vender"""
        if not context.args:
            await update.message.reply_text("❌ Especifica el símbolo: /vender BTCUSDT")
            return
        
        symbol = context.args[0].upper()
        
        try:
            # Verificar posición
            position = await self.binance_client.get_position(symbol)
            
            if position['quantity'] > 0:
                # Ejecutar venta
                result = await self.binance_client.place_sell_order(symbol, position['quantity'])
                
                if result['success']:
                    profit_loss = result['total'] - position['cost']
                    profit_percentage = (profit_loss / position['cost']) * 100
                    
                    emoji = "📈" if profit_loss > 0 else "📉"
                    
                    message = f"""
✅ **Orden de venta ejecutada**

{emoji} {symbol}
📊 Cantidad: {result['quantity']}
💵 Precio: ${result['price']}
💸 Total: ${result['total']}
💰 P&L: ${profit_loss:.2f} ({profit_percentage:.2f}%)
                    """
                    
                    # Guardar en base de datos
                    await self.db.save_trade(result)
                    
                else:
                    message = f"❌ Error en la venta: {result['error']}"
            else:
                message = f"❌ No tienes posición en {symbol}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def toggle_trading(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Activar/desactivar trading automático"""
        command = update.message.text.split()[0]
        
        if command == '/activar':
            self.trading_active = True
            message = "🟢 **Trading automático ACTIVADO**\n\nEl bot comenzará a buscar oportunidades de trading."
        else:
            self.trading_active = False
            message = "🔴 **Trading automático DESACTIVADO**\n\nEl bot dejará de hacer trades automáticos."
        
        await update.message.reply_text(message, parse_mode='Markdown')

    async def handle_text_messages(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar mensajes de texto con palabras clave"""
        text = update.message.text.lower()
        
        # Comprar
        if text.startswith('comprar '):
            symbol = text.split(' ')[1].upper() + 'USDT'
            await self.execute_buy_from_text(update, symbol)
        
        # Vender
        elif text.startswith('vender '):
            symbol = text.split(' ')[1].upper() + 'USDT'
            await self.execute_sell_from_text(update, symbol)
        
        # Analizar
        elif text.startswith('analizar '):
            symbol = text.split(' ')[1].upper() + 'USDT'
            await self.analyze_symbol(update, symbol)
        
        # Precio
        elif text.startswith('precio '):
            symbol = text.split(' ')[1].upper() + 'USDT'
            await self.get_price(update, symbol)
        
        else:
            await update.message.reply_text("❓ No entiendo ese comando. Usa /ayuda para ver los comandos disponibles.")

    async def execute_buy_from_text(self, update: Update, symbol: str):
        """Ejecutar compra desde mensaje de texto"""
        await update.message.reply_text(f"🔍 Analizando {symbol} para compra...")
        
        try:
            # Análisis rápido
            analysis = await self.market_analyzer.quick_analysis(symbol)
            
            if analysis['buy_signal']:
                result = await self.binance_client.place_buy_order(symbol, analysis['suggested_amount'])
                
                if result['success']:
                    message = f"✅ Compra ejecutada: {result['quantity']} {symbol} a ${result['price']}"
                else:
                    message = f"❌ Error: {result['error']}"
            else:
                message = f"⚠️ No es buen momento para comprar {symbol}"
            
            await update.message.reply_text(message)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def get_open_positions(self):
        """Obtener posiciones abiertas"""
        return await self.binance_client.get_open_positions()

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejar callbacks de botones inline"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "analizar":
            await self.analyze_command(update, context)
        elif query.data == "balance":
            await self.status_command(update, context)
        elif query.data == "configurar":
            await query.edit_message_text("⚙️ Configuración disponible por comandos. Usa /ayuda")

    def run(self):
        """Ejecutar el bot"""
        if not settings.validate():
            logger.error("Configuración incompleta. Revisa el archivo .env")
            return
        
        # Crear aplicación
        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Agregar handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("ayuda", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("analizar", self.analyze_command))
        application.add_handler(CommandHandler("comprar", self.buy_command))
        application.add_handler(CommandHandler("vender", self.sell_command))
        application.add_handler(CommandHandler("activar", self.toggle_trading))
        application.add_handler(CommandHandler("desactivar", self.toggle_trading))
        
        # Handler para mensajes de texto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_messages))
        
        # Handler para botones
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Iniciar bot
        logger.info("Bot iniciado...")
        application.run_polling()

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()