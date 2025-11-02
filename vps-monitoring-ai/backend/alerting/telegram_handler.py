"""
Telegram Alerting Handler
Sends formatted alerts via Telegram Bot API
"""
import asyncio
from telegram import Bot
from telegram.error import TelegramError
from typing import Dict, Any
from loguru import logger
from datetime import datetime

from backend.config.settings import settings


class TelegramHandler:
    """Handles Telegram notifications"""
    
    def __init__(self):
        self.bot_token = settings.telegram_bot_token
        self.chat_id = settings.telegram_chat_id
        self.bot = Bot(token=self.bot_token) if self.bot_token else None
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert via Telegram
        
        Args:
            alert_data: Dictionary containing alert information
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            logger.warning("Telegram bot not configured")
            return False
        
        try:
            message = self._format_message(alert_data)
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            logger.info(f"Telegram alert sent successfully to chat {self.chat_id}")
            return True
        
        except TelegramError as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Telegram alert: {e}")
            return False
    
    def _format_message(self, alert_data: Dict[str, Any]) -> str:
        """Format Telegram message with emojis"""
        severity = alert_data.get('severity', 'warning').lower()
        
        # Emoji mapping
        severity_emoji = {
            'critical': '🔴',
            'warning': '⚠️',
            'info': '🔵'
        }
        
        emoji = severity_emoji.get(severity, '⚠️')
        
        # Build message
        message = f"{emoji} <b>{severity.upper()} ALERT</b>\n\n"
        
        # Title
        message += f"<b>{alert_data.get('title', 'System Alert')}</b>\n\n"
        
        # Node info
        message += f"📍 <b>Node:</b> {alert_data.get('node_name', 'Unknown')}\n"
        message += f"🌐 <b>IP:</b> {alert_data.get('node_ip', 'N/A')}\n"
        message += f"🕐 <b>Time:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}\n\n"
        
        # Details
        message += f"📝 <b>Details:</b>\n{alert_data.get('message', 'No details')}\n\n"
        
        # Metrics (if available)
        current_metrics = alert_data.get('current_metrics', {})
        if current_metrics:
            message += "📊 <b>Current Metrics:</b>\n"
            message += f"  • CPU: {current_metrics.get('cpu_percent', 0):.1f}%\n"
            message += f"  • Memory: {current_metrics.get('memory_percent', 0):.1f}%\n"
            message += f"  • Disk: {current_metrics.get('disk_percent', 0):.1f}%\n\n"
        
        # Actions taken
        actions = alert_data.get('actions_taken', [])
        if actions:
            message += "🔧 <b>Actions Taken:</b>\n"
            for action in actions:
                status_icon = "✅" if action.get('status') == 'success' else "❌"
                message += f"  {status_icon} {action.get('description', 'Unknown')}\n"
            message += "\n"
        
        # Dashboard link
        node_id = alert_data.get('node_id')
        if node_id:
            message += f"🔗 <a href='http://localhost:3000/nodes/{node_id}'>View Node Details</a>"
        
        return message
    
    async def send_resolution(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert resolution notification
        
        Args:
            alert_data: Dictionary containing resolution information
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.bot:
            return False
        
        try:
            message = (
                f"✅ <b>RESOLVED</b>\n\n"
                f"<b>{alert_data.get('title', 'Alert')}</b>\n\n"
                f"📍 <b>Node:</b> {alert_data.get('node_name', 'Unknown')}\n"
                f"🕐 <b>Resolved:</b> {datetime.utcnow().strftime('%H:%M:%S UTC')}\n"
                f"⏱️ <b>Duration:</b> {alert_data.get('duration_minutes', 0)} minutes\n\n"
                f"The issue has been resolved automatically."
            )
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info("Telegram resolution notification sent")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send Telegram resolution: {e}")
            return False
