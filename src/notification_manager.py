import asyncio
import logging
import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import requests
from config.settings import settings

logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self):
        self.telegram_notifications = True
        self.email_notifications = False
        self.webhook_notifications = False
        
        # Configuración de email (opcional)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_user = ""
        self.email_password = ""
        self.email_recipients = []
        
        # Webhook URLs (Discord, Slack, etc.)
        self.webhook_urls = []
        
        # Filtros de notificaciones
        self.notification_levels = {
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        self.min_notification_level = 2  # Solo WARNING y superiores
        
    async def send_trade_notification(self, trade_result: Dict, trade_type: str):
        """Enviar notificación de trade ejecutado"""
        try:
            if not trade_result.get('success', False):
                return
            
            symbol = trade_result.get('symbol', 'N/A')
            action = trade_result.get('action', trade_type)
            quantity = trade_result.get('quantity', 0)
            price = trade_result.get('price', 0)
            total = trade_result.get('total', 0)
            
            # Emoji según el tipo de trade
            emoji_map = {
                'BUY': '🟢',
                'SELL': '🔴',
                'STOP_LOSS': '🛑',
                'TAKE_PROFIT': '🎯'
            }
            
            emoji = emoji_map.get(action, '🔄')
            
            message = f"""
{emoji} **Trade Ejecutado**

📊 **Símbolo:** {symbol}
⚡ **Acción:** {action}
📈 **Cantidad:** {quantity:.6f}
💰 **Precio:** ${price:.4f}
💵 **Total:** ${total:.2f}
🕐 **Hora:** {datetime.now().strftime('%H:%M:%S')}
            """
            
            if 'pnl' in trade_result:
                pnl = trade_result['pnl']
                pnl_pct = trade_result.get('pnl_pct', 0)
                pnl_emoji = '📈' if pnl > 0 else '📉'
                message += f"\n{pnl_emoji} **P&L:** ${pnl:.2f} ({pnl_pct:.2f}%)"
            
            await self._send_notification(message, 'INFO')
            
        except Exception as e:
            logger.error(f"Error enviando notificación de trade: {e}")
    
    async def send_risk_alert(self, risk_data: Dict):
        """Enviar alerta de riesgo"""
        try:
            risk_level = risk_data.get('risk_level', 'UNKNOWN')
            
            # Determinar nivel de notificación
            notification_level = 'WARNING' if risk_level == 'MEDIUM' else 'ERROR' if risk_level == 'HIGH' else 'INFO'
            
            # Emoji según nivel de riesgo
            risk_emojis = {
                'LOW': '🟢',
                'MEDIUM': '🟡',
                'HIGH': '🔴',
                'CRITICAL': '🚨'
            }
            
            emoji = risk_emojis.get(risk_level, '⚠️')
            
            message = f"""
{emoji} **Alerta de Riesgo - {risk_level}**

💰 **Exposición Actual:** ${risk_data.get('current_exposure', 0):.2f}
📊 **P&L Diario:** ${risk_data.get('daily_pnl', 0):.2f}
📈 **P&L Semanal:** ${risk_data.get('weekly_pnl', 0):.2f}
🔢 **Posiciones Activas:** {risk_data.get('active_positions', 0)}
📉 **VaR 95%:** ${risk_data.get('var_95', 0):.2f}
            """
            
            await self._send_notification(message, notification_level)
            
        except Exception as e:
            logger.error(f"Error enviando alerta de riesgo: {e}")
    
    async def send_market_alert(self, alert_data: Dict):
        """Enviar alerta de mercado"""
        try:
            alert_type = alert_data.get('type', 'GENERAL')
            symbol = alert_data.get('symbol', 'MARKET')
            message_text = alert_data.get('message', 'Alerta de mercado')
            
            # Emojis según tipo de alerta
            alert_emojis = {
                'PRICE_SPIKE': '🚀',
                'PRICE_DROP': '📉',
                'HIGH_VOLUME': '📊',
                'VOLATILITY': '⚡',
                'NEWS': '📰',
                'TECHNICAL': '🔧'
            }
            
            emoji = alert_emojis.get(alert_type, '📢')
            
            message = f"""
{emoji} **Alerta de Mercado**

🎯 **Símbolo:** {symbol}
📝 **Tipo:** {alert_type}
💬 **Mensaje:** {message_text}
🕐 **Hora:** {datetime.now().strftime('%H:%M:%S')}
            """
            
            # Agregar datos adicionales si están disponibles
            if 'price' in alert_data:
                message += f"\n💰 **Precio:** ${alert_data['price']:.4f}"
            
            if 'change_pct' in alert_data:
                change = alert_data['change_pct']
                change_emoji = '📈' if change > 0 else '📉'
                message += f"\n{change_emoji} **Cambio:** {change:.2f}%"
            
            await self._send_notification(message, 'WARNING')
            
        except Exception as e:
            logger.error(f"Error enviando alerta de mercado: {e}")
    
    async def send_system_alert(self, alert_type: str, message: str, level: str = 'WARNING'):
        """Enviar alerta del sistema"""
        try:
            # Emojis según tipo de alerta del sistema
            system_emojis = {
                'ERROR': '❌',
                'CONNECTION': '🔌',
                'API_LIMIT': '⏰',
                'BALANCE': '💰',
                'MAINTENANCE': '🔧',
                'STARTUP': '🚀',
                'SHUTDOWN': '🛑'
            }
            
            emoji = system_emojis.get(alert_type, '🤖')
            
            formatted_message = f"""
{emoji} **Alerta del Sistema**

🔧 **Tipo:** {alert_type}
📝 **Mensaje:** {message}
🕐 **Hora:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self._send_notification(formatted_message, level)
            
        except Exception as e:
            logger.error(f"Error enviando alerta del sistema: {e}")
    
    async def send_performance_report(self, performance_data: Dict):
        """Enviar reporte de rendimiento"""
        try:
            daily_pnl = performance_data.get('daily_pnl', 0)
            weekly_pnl = performance_data.get('weekly_pnl', 0)
            weekly_progress = performance_data.get('weekly_progress_pct', 0)
            trades_today = performance_data.get('trades_today', 0)
            
            # Emoji según rendimiento
            performance_emoji = '📈' if daily_pnl > 0 else '📉' if daily_pnl < 0 else '➖'
            
            message = f"""
📊 **Reporte de Rendimiento Diario**

{performance_emoji} **P&L Diario:** ${daily_pnl:.2f}
📈 **P&L Semanal:** ${weekly_pnl:.2f}
🎯 **Progreso Objetivo:** {weekly_progress:.1f}%
🔄 **Trades Hoy:** {trades_today}
📅 **Fecha:** {datetime.now().strftime('%Y-%m-%d')}

🎯 **Objetivo Semanal:** 30% ganancia
            """
            
            await self._send_notification(message, 'INFO')
            
        except Exception as e:
            logger.error(f"Error enviando reporte de rendimiento: {e}")
    
    async def _send_notification(self, message: str, level: str = 'INFO'):
        """Enviar notificación por todos los canales configurados"""
        try:
            # Verificar nivel mínimo
            if self.notification_levels.get(level, 1) < self.min_notification_level:
                return
            
            # Telegram (principal)
            if self.telegram_notifications:
                await self._send_telegram_notification(message)
            
            # Email (opcional)
            if self.email_notifications and self.email_user:
                await self._send_email_notification(message, level)
            
            # Webhooks (Discord, Slack, etc.)
            if self.webhook_notifications and self.webhook_urls:
                await self._send_webhook_notifications(message, level)
                
        except Exception as e:
            logger.error(f"Error enviando notificación: {e}")
    
    async def _send_telegram_notification(self, message: str):
        """Enviar notificación por Telegram"""
        try:
            if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
                return
            
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            data = {
                'chat_id': settings.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Error enviando mensaje a Telegram: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error en notificación de Telegram: {e}")
    
    async def _send_email_notification(self, message: str, level: str):
        """Enviar notificación por email"""
        try:
            if not self.email_user or not self.email_recipients:
                return
            
            # Crear mensaje de email
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = f"[{level}] Bot de Trading - Notificación"
            
            # Convertir markdown a texto plano para email
            plain_message = message.replace('**', '').replace('*', '')
            msg.attach(MIMEText(plain_message, 'plain'))
            
            # Enviar email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
    
    async def _send_webhook_notifications(self, message: str, level: str):
        """Enviar notificaciones por webhooks"""
        try:
            # Convertir mensaje para webhooks
            webhook_message = {
                'text': message.replace('**', '').replace('*', ''),
                'level': level,
                'timestamp': datetime.now().isoformat()
            }
            
            for webhook_url in self.webhook_urls:
                try:
                    response = requests.post(
                        webhook_url,
                        json=webhook_message,
                        timeout=10
                    )
                    
                    if response.status_code not in [200, 204]:
                        logger.warning(f"Error en webhook {webhook_url}: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error enviando webhook a {webhook_url}: {e}")
                    
        except Exception as e:
            logger.error(f"Error en webhooks: {e}")
    
    def configure_email(self, smtp_server: str, smtp_port: int, user: str, 
                       password: str, recipients: List[str]):
        """Configurar notificaciones por email"""
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = user
        self.email_password = password
        self.email_recipients = recipients
        self.email_notifications = True
        logger.info("Notificaciones por email configuradas")
    
    def add_webhook(self, webhook_url: str):
        """Agregar webhook para notificaciones"""
        self.webhook_urls.append(webhook_url)
        self.webhook_notifications = True
        logger.info(f"Webhook agregado: {webhook_url}")
    
    def set_notification_level(self, level: str):
        """Establecer nivel mínimo de notificaciones"""
        if level in self.notification_levels:
            self.min_notification_level = self.notification_levels[level]
            logger.info(f"Nivel de notificación establecido a: {level}")
    
    async def test_notifications(self):
        """Probar todos los canales de notificación"""
        test_message = """
🧪 **Prueba de Notificaciones**

✅ Sistema de notificaciones funcionando correctamente
🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await self._send_notification(test_message, 'INFO')
        logger.info("Prueba de notificaciones enviada")
    
    async def send_emergency_alert(self, message: str):
        """Enviar alerta de emergencia (máxima prioridad)"""
        emergency_message = f"""
🚨 **ALERTA DE EMERGENCIA** 🚨

⚠️ {message}

🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🛑 Revisa el bot inmediatamente
        """
        
        # Forzar envío independientemente del nivel mínimo
        original_level = self.min_notification_level
        self.min_notification_level = 1
        
        await self._send_notification(emergency_message, 'CRITICAL')
        
        # Restaurar nivel original
        self.min_notification_level = original_level