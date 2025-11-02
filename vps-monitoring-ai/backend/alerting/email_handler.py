"""
Email Alerting Handler
Sends formatted email alerts via SMTP
"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any
from loguru import logger
from datetime import datetime

from backend.config.settings import settings


class EmailHandler:
    """Handles email notifications"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.from_email = settings.alert_from_email
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> bool:
        """
        Send alert via email
        
        Args:
            alert_data: Dictionary containing alert information
        
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Prepare email
            message = MIMEMultipart('alternative')
            message['Subject'] = self._format_subject(alert_data)
            message['From'] = self.from_email
            message['To'] = alert_data.get('recipients', self.smtp_user)
            
            # Create HTML body
            html_body = self._format_html_body(alert_data)
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                use_tls=True
            )
            
            logger.info(f"Email alert sent successfully to {message['To']}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _format_subject(self, alert_data: Dict[str, Any]) -> str:
        """Format email subject line"""
        severity = alert_data.get('severity', 'WARNING').upper()
        node_name = alert_data.get('node_name', 'Unknown')
        title = alert_data.get('title', 'System Alert')
        
        return f"[{severity}] {node_name} - {title}"
    
    def _format_html_body(self, alert_data: Dict[str, Any]) -> str:
        """Format HTML email body"""
        severity = alert_data.get('severity', 'warning')
        severity_color = {
            'critical': '#dc2626',
            'warning': '#f59e0b',
            'info': '#3b82f6'
        }.get(severity.lower(), '#f59e0b')
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPS Monitoring Alert</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <div style="background-color: {severity_color}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
        <h1 style="margin: 0; font-size: 24px;">⚠️ VPS Monitoring Alert</h1>
        <p style="margin: 5px 0 0 0; opacity: 0.9;">{severity.upper()}</p>
    </div>
    
    <div style="background-color: #f9fafb; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        
        <h2 style="margin-top: 0; color: #111827;">{alert_data.get('title', 'System Alert')}</h2>
        
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">📊 Summary</h3>
            <p style="margin: 10px 0;"><strong>Node:</strong> {alert_data.get('node_name', 'Unknown')}</p>
            <p style="margin: 10px 0;"><strong>IP:</strong> {alert_data.get('node_ip', 'N/A')}</p>
            <p style="margin: 10px 0;"><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
        </div>
        
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">📝 Details</h3>
            <p style="margin: 10px 0;">{alert_data.get('message', 'No details available')}</p>
        </div>
        
        {self._format_metrics_section(alert_data)}
        
        {self._format_actions_section(alert_data)}
        
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">🔗 Quick Actions</h3>
            <p style="margin: 10px 0;">
                <a href="{self._get_dashboard_url(alert_data)}" style="display: inline-block; background-color: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; margin-right: 10px;">View Dashboard</a>
                <a href="{self._get_node_url(alert_data)}" style="display: inline-block; background-color: #6b7280; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px;">View Node</a>
            </p>
        </div>
        
    </div>
    
    <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
        <p>VPS Monitoring AI System</p>
        <p>This is an automated alert. Do not reply to this email.</p>
    </div>
    
</body>
</html>
"""
        return html
    
    def _format_metrics_section(self, alert_data: Dict[str, Any]) -> str:
        """Format metrics section"""
        current_metrics = alert_data.get('current_metrics', {})
        if not current_metrics:
            return ""
        
        cpu = current_metrics.get('cpu_percent', 0)
        memory = current_metrics.get('memory_percent', 0)
        disk = current_metrics.get('disk_percent', 0)
        
        def get_metric_color(value: float, warning: int, critical: int) -> str:
            if value >= critical:
                return '#dc2626'
            elif value >= warning:
                return '#f59e0b'
            return '#10b981'
        
        return f"""
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">📈 Current Metrics</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>CPU:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                        <span style="color: {get_metric_color(cpu, 70, 85)}; font-weight: bold;">{cpu:.1f}%</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb;"><strong>Memory:</strong></td>
                    <td style="padding: 8px 0; border-bottom: 1px solid #e5e7eb; text-align: right;">
                        <span style="color: {get_metric_color(memory, 75, 90)}; font-weight: bold;">{memory:.1f}%</span>
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Disk:</strong></td>
                    <td style="padding: 8px 0; text-align: right;">
                        <span style="color: {get_metric_color(disk, 80, 95)}; font-weight: bold;">{disk:.1f}%</span>
                    </td>
                </tr>
            </table>
        </div>
        """
    
    def _format_actions_section(self, alert_data: Dict[str, Any]) -> str:
        """Format actions taken section"""
        actions = alert_data.get('actions_taken', [])
        if not actions:
            return """
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">🔧 Actions Taken</h3>
            <p style="margin: 10px 0; color: #6b7280;">No automated actions taken yet.</p>
        </div>
            """
        
        actions_html = ""
        for action in actions:
            status_icon = "✅" if action.get('status') == 'success' else "❌"
            actions_html += f"<li style='margin: 5px 0;'>{status_icon} {action.get('description', 'Unknown action')}</li>"
        
        return f"""
        <div style="background-color: white; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
            <h3 style="margin-top: 0; color: #374151; font-size: 16px;">🔧 Actions Taken</h3>
            <ul style="margin: 10px 0; padding-left: 20px;">
                {actions_html}
            </ul>
        </div>
        """
    
    def _get_dashboard_url(self, alert_data: Dict[str, Any]) -> str:
        """Get dashboard URL"""
        # In production, use actual domain
        return "http://localhost:3000/dashboard"
    
    def _get_node_url(self, alert_data: Dict[str, Any]) -> str:
        """Get node details URL"""
        node_id = alert_data.get('node_id')
        return f"http://localhost:3000/nodes/{node_id}" if node_id else "#"
