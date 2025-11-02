"""
Unit tests for AlertManager
Tests alert creation, deduplication, and dispatch
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from backend.alerting.alert_manager import AlertManager
from backend.database.models import AlertSeverity


@pytest.mark.unit
class TestAlertManager:
    """Test Alert Management System"""
    
    def test_initialization(self):
        """Test AlertManager initialization"""
        manager = AlertManager()
        
        assert manager.email_handler is not None
        assert manager.telegram_handler is not None
        assert isinstance(manager.recent_alerts_cache, dict)
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_and_send_alert_success(
        self, mock_db_context, sample_node, mock_email_handler, mock_telegram_handler
    ):
        """Test successful alert creation and sending"""
        # Setup mock database
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        # Create manager with mocked handlers
        manager = AlertManager()
        manager.email_handler = mock_email_handler
        manager.telegram_handler = mock_telegram_handler
        
        # Create alert
        alert = await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.CRITICAL,
            title="High CPU Usage",
            message="CPU usage exceeded 85%",
            metric_type="cpu",
            metric_value=87.5,
            threshold_value=85.0,
            channels=['both']
        )
        
        # Verify alert was created and handlers were called
        mock_email_handler.send_alert.assert_called_once()
        mock_telegram_handler.send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_duplicate_prevention(
        self, mock_db_context, sample_node
    ):
        """Test duplicate alert prevention"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        
        # First alert
        alert1 = await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            channels=['email']
        )
        
        # Duplicate alert (same node and title within 1 hour)
        alert2 = await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            channels=['email']
        )
        
        # Second alert should be None (skipped)
        assert alert2 is None
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_after_cache_expiry(
        self, mock_db_context, sample_node
    ):
        """Test alert creation after cache expiry"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = AsyncMock()
        manager.email_handler.send_alert = AsyncMock(return_value=True)
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_alert = AsyncMock(return_value=True)
        
        # Create first alert
        alert_key = f"{sample_node.id}:Test Alert"
        manager.recent_alerts_cache[alert_key] = datetime.utcnow() - timedelta(hours=2)
        
        # Should not be duplicate after 2 hours
        alert = await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            channels=['email']
        )
        
        assert alert is not None
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_node_not_found(self, mock_db_context):
        """Test alert creation when node doesn't exist"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None  # Node not found
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        
        alert = await manager.create_and_send_alert(
            node_id=999,  # Non-existent node
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message"
        )
        
        assert alert is None
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_email_only(
        self, mock_db_context, sample_node, mock_email_handler, mock_telegram_handler
    ):
        """Test alert sending via email only"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = mock_email_handler
        manager.telegram_handler = mock_telegram_handler
        
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            channels=['email']
        )
        
        mock_email_handler.send_alert.assert_called_once()
        mock_telegram_handler.send_alert.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_telegram_only(
        self, mock_db_context, sample_node, mock_email_handler, mock_telegram_handler
    ):
        """Test alert sending via Telegram only"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = mock_email_handler
        manager.telegram_handler = mock_telegram_handler
        
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.CRITICAL,
            title="Test Alert",
            message="Test message",
            channels=['telegram']
        )
        
        mock_email_handler.send_alert.assert_not_called()
        mock_telegram_handler.send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_with_metrics_and_actions(
        self, mock_db_context, sample_node
    ):
        """Test alert creation with current metrics and actions taken"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = AsyncMock()
        manager.email_handler.send_alert = AsyncMock(return_value=True)
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_alert = AsyncMock(return_value=True)
        
        current_metrics = {
            'cpu_percent': 87.5,
            'memory_percent': 75.2,
            'disk_percent': 60.0
        }
        
        actions_taken = [
            {'description': 'Restarted service', 'status': 'success'},
            {'description': 'Cleared cache', 'status': 'success'}
        ]
        
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.CRITICAL,
            title="High CPU Usage",
            message="CPU exceeded threshold",
            current_metrics=current_metrics,
            actions_taken=actions_taken,
            channels=['both']
        )
        
        # Verify handlers were called with correct data
        call_args = manager.email_handler.send_alert.call_args[0][0]
        assert call_args['current_metrics'] == current_metrics
        assert call_args['actions_taken'] == actions_taken
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_create_alert_handler_failure(
        self, mock_db_context, sample_node
    ):
        """Test alert creation when handlers fail"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = AsyncMock()
        manager.email_handler.send_alert = AsyncMock(return_value=False)  # Failure
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_alert = AsyncMock(return_value=True)
        
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            channels=['both']
        )
        
        # Should still complete even if email fails
        manager.email_handler.send_alert.assert_called_once()
        manager.telegram_handler.send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_resolve_alert_success(self, mock_db_context, sample_alert):
        """Test successful alert resolution"""
        mock_db = Mock()
        sample_alert.is_resolved = False
        sample_alert.resolved_at = None
        mock_db.query().filter().first.side_effect = [sample_alert, sample_alert.node]
        mock_db.commit = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_resolution = AsyncMock(return_value=True)
        
        result = await manager.resolve_alert(sample_alert.id, send_notification=True)
        
        assert result is True
        assert sample_alert.is_resolved is True
        assert sample_alert.resolved_at is not None
        manager.telegram_handler.send_resolution.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_resolve_alert_not_found(self, mock_db_context):
        """Test resolving non-existent alert"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = None
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        
        result = await manager.resolve_alert(999)  # Non-existent alert
        
        assert result is False
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_resolve_alert_without_notification(self, mock_db_context, sample_alert):
        """Test alert resolution without sending notification"""
        mock_db = Mock()
        sample_alert.is_resolved = False
        mock_db.query().filter().first.return_value = sample_alert
        mock_db.commit = Mock()
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_resolution = AsyncMock(return_value=True)
        
        result = await manager.resolve_alert(sample_alert.id, send_notification=False)
        
        assert result is True
        manager.telegram_handler.send_resolution.assert_not_called()
    
    def test_is_duplicate_alert_within_hour(self):
        """Test duplicate detection within 1 hour"""
        manager = AlertManager()
        alert_key = "1:Test Alert"
        
        manager.recent_alerts_cache[alert_key] = datetime.utcnow() - timedelta(minutes=30)
        
        assert manager._is_duplicate_alert(alert_key) is True
    
    def test_is_duplicate_alert_after_hour(self):
        """Test duplicate detection after 1 hour"""
        manager = AlertManager()
        alert_key = "1:Test Alert"
        
        manager.recent_alerts_cache[alert_key] = datetime.utcnow() - timedelta(hours=2)
        
        assert manager._is_duplicate_alert(alert_key) is False
        # Old entry should be removed
        assert alert_key not in manager.recent_alerts_cache
    
    def test_is_duplicate_alert_not_cached(self):
        """Test duplicate detection for new alert"""
        manager = AlertManager()
        alert_key = "1:New Alert"
        
        assert manager._is_duplicate_alert(alert_key) is False
    
    def test_cleanup_cache(self):
        """Test cache cleanup removes old entries"""
        manager = AlertManager()
        
        # Add entries with different ages
        manager.recent_alerts_cache = {
            "1:Old Alert": datetime.utcnow() - timedelta(hours=3),
            "2:Recent Alert": datetime.utcnow() - timedelta(minutes=30),
            "3:Very Old Alert": datetime.utcnow() - timedelta(hours=5)
        }
        
        manager.cleanup_cache()
        
        # Only recent alert should remain
        assert "1:Old Alert" not in manager.recent_alerts_cache
        assert "2:Recent Alert" in manager.recent_alerts_cache
        assert "3:Very Old Alert" not in manager.recent_alerts_cache
    
    @pytest.mark.asyncio
    @patch('backend.alerting.alert_manager.get_db_context')
    async def test_alert_severity_levels(
        self, mock_db_context, sample_node
    ):
        """Test different alert severity levels"""
        mock_db = Mock()
        mock_db.query().filter().first.return_value = sample_node
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock(side_effect=lambda obj: setattr(obj, 'id', 1))
        mock_db_context.return_value.__enter__.return_value = mock_db
        mock_db_context.return_value.__exit__.return_value = None
        
        manager = AlertManager()
        manager.email_handler = AsyncMock()
        manager.email_handler.send_alert = AsyncMock(return_value=True)
        manager.telegram_handler = AsyncMock()
        manager.telegram_handler.send_alert = AsyncMock(return_value=True)
        
        # Test CRITICAL
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.CRITICAL,
            title="Critical Alert",
            message="Critical issue"
        )
        
        # Test WARNING
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.WARNING,
            title="Warning Alert",
            message="Warning issue"
        )
        
        # Test INFO
        await manager.create_and_send_alert(
            node_id=sample_node.id,
            severity=AlertSeverity.INFO,
            title="Info Alert",
            message="Info message"
        )
        
        # All should be sent
        assert manager.email_handler.send_alert.call_count == 3
