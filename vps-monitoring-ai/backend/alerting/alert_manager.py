"""
Alert Manager - Orchestrates all alerting channels
"""
import asyncio
from typing import Dict, Any, List
from loguru import logger
from datetime import datetime, timedelta

from backend.alerting.email_handler import EmailHandler
from backend.alerting.telegram_handler import TelegramHandler
from backend.database.connection import get_db_context
from backend.database.models import Alert, AlertSeverity, Node


class AlertManager:
    """Manages alert lifecycle and multi-channel notifications"""
    
    def __init__(self):
        self.email_handler = EmailHandler()
        self.telegram_handler = TelegramHandler()
        self.recent_alerts_cache: Dict[str, datetime] = {}
    
    async def create_and_send_alert(
        self,
        node_id: int,
        severity: AlertSeverity,
        title: str,
        message: str,
        metric_type: str = None,
        metric_value: float = None,
        threshold_value: float = None,
        channels: List[str] = None,
        current_metrics: Dict[str, Any] = None,
        actions_taken: List[Dict[str, Any]] = None
    ) -> Alert:
        """
        Create alert and send via configured channels
        
        Args:
            node_id: ID of the node
            severity: Alert severity (CRITICAL, WARNING, INFO)
            title: Alert title
            message: Detailed message
            metric_type: Type of metric (cpu, memory, disk)
            metric_value: Current metric value
            threshold_value: Threshold that was exceeded
            channels: List of channels to use ['email', 'telegram', 'both']
            current_metrics: Current system metrics
            actions_taken: List of actions that were taken
        
        Returns:
            Created Alert object
        """
        # Check for duplicate alerts
        alert_key = f"{node_id}:{title}"
        if self._is_duplicate_alert(alert_key):
            logger.info(f"Skipping duplicate alert: {title}")
            return None
        
        # Create alert in database
        with get_db_context() as db:
            # Get node info
            node = db.query(Node).filter(Node.id == node_id).first()
            if not node:
                logger.error(f"Node {node_id} not found")
                return None
            
            # Create alert
            alert = Alert(
                node_id=node_id,
                severity=severity,
                title=title,
                message=message,
                metric_type=metric_type,
                metric_value=metric_value,
                threshold_value=threshold_value,
                is_resolved=False,
                notified_email=False,
                notified_telegram=False,
                created_at=datetime.utcnow()
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            alert_id = alert.id
        
        # Prepare alert data for notifications
        alert_data = {
            'alert_id': alert_id,
            'node_id': node_id,
            'node_name': node.name,
            'node_ip': node.ip_address,
            'severity': severity.value,
            'title': title,
            'message': message,
            'metric_type': metric_type,
            'metric_value': metric_value,
            'threshold_value': threshold_value,
            'current_metrics': current_metrics or {},
            'actions_taken': actions_taken or [],
        }
        
        # Determine channels
        if channels is None or 'both' in channels:
            channels = ['email', 'telegram']
        
        # Send notifications
        email_success = False
        telegram_success = False
        
        if 'email' in channels:
            email_success = await self.email_handler.send_alert(alert_data)
        
        if 'telegram' in channels:
            telegram_success = await self.telegram_handler.send_alert(alert_data)
        
        # Update alert notification status
        with get_db_context() as db:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                alert.notified_email = email_success
                alert.notified_telegram = telegram_success
                db.commit()
        
        # Cache alert to prevent duplicates
        self.recent_alerts_cache[alert_key] = datetime.utcnow()
        
        logger.info(
            f"Alert created and sent: {title} "
            f"(Email: {email_success}, Telegram: {telegram_success})"
        )
        
        return alert
    
    async def resolve_alert(
        self,
        alert_id: int,
        send_notification: bool = True
    ) -> bool:
        """
        Mark alert as resolved and optionally send notification
        
        Args:
            alert_id: ID of the alert
            send_notification: Whether to send resolution notification
        
        Returns:
            True if successful
        """
        with get_db_context() as db:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if not alert:
                logger.error(f"Alert {alert_id} not found")
                return False
            
            alert.is_resolved = True
            alert.resolved_at = datetime.utcnow()
            db.commit()
            
            # Send resolution notification
            if send_notification:
                node = db.query(Node).filter(Node.id == alert.node_id).first()
                
                duration_minutes = 0
                if alert.resolved_at and alert.created_at:
                    duration = alert.resolved_at - alert.created_at
                    duration_minutes = int(duration.total_seconds() / 60)
                
                resolution_data = {
                    'alert_id': alert.id,
                    'node_id': alert.node_id,
                    'node_name': node.name if node else 'Unknown',
                    'title': alert.title,
                    'duration_minutes': duration_minutes,
                }
                
                await self.telegram_handler.send_resolution(resolution_data)
        
        logger.info(f"Alert {alert_id} marked as resolved")
        return True
    
    def _is_duplicate_alert(self, alert_key: str) -> bool:
        """Check if alert is duplicate (sent within last hour)"""
        if alert_key in self.recent_alerts_cache:
            last_sent = self.recent_alerts_cache[alert_key]
            if datetime.utcnow() - last_sent < timedelta(hours=1):
                return True
            else:
                # Remove old entry
                del self.recent_alerts_cache[alert_key]
        return False
    
    async def send_daily_summary(self):
        """Send daily summary of alerts and actions"""
        # TODO: Implement daily summary
        pass
    
    def cleanup_cache(self):
        """Clean up old entries from cache"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, timestamp in self.recent_alerts_cache.items()
            if now - timestamp > timedelta(hours=2)
        ]
        for key in expired_keys:
            del self.recent_alerts_cache[key]
