"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import sys
from datetime import datetime
from unittest.mock import Mock, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database.models import Base, User, Node, Container, Alert, Action, UserRole, AlertSeverity, ActionStatus
from backend.config.settings import Settings


@pytest.fixture(scope="session")
def test_settings():
    """Create test settings"""
    return Settings(
        openai_api_key="test-key",
        mysql_user="test_user",
        mysql_password="test_password",
        mysql_database="test_db",
        smtp_user="test@example.com",
        smtp_password="test_password",
        alert_from_email="alerts@example.com",
        telegram_bot_token="test-token",
        telegram_chat_id="12345",
        jwt_secret_key="test-secret-key",
        influx_token="test-influx-token",
        debug=True,
        environment="test"
    )


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite database engine for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine):
    """Create database session for testing"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_node(test_db_session):
    """Create a sample node for testing"""
    node = Node(
        name="test-node-1",
        ip_address="192.168.1.100",
        node_type="slave",
        is_active=True,
        last_heartbeat=datetime.utcnow(),
        os_type="Ubuntu",
        os_version="22.04"
    )
    test_db_session.add(node)
    test_db_session.commit()
    test_db_session.refresh(node)
    return node


@pytest.fixture(scope="function")
def sample_user(test_db_session):
    """Create a sample user for testing"""
    user = User(
        username="test_user",
        email="test@example.com",
        hashed_password="hashed_password_123",
        role=UserRole.OPERATOR,
        is_active=True
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def sample_container(test_db_session, sample_node):
    """Create a sample container for testing"""
    container = Container(
        node_id=sample_node.id,
        container_id="abc123def456",
        name="test-container",
        image="nginx:latest",
        status="running",
        ports={"80/tcp": 8080},
        is_monitored=True
    )
    test_db_session.add(container)
    test_db_session.commit()
    test_db_session.refresh(container)
    return container


@pytest.fixture(scope="function")
def sample_alert(test_db_session, sample_node):
    """Create a sample alert for testing"""
    alert = Alert(
        node_id=sample_node.id,
        severity=AlertSeverity.WARNING,
        title="High CPU Usage",
        message="CPU usage exceeded 85%",
        metric_type="cpu",
        metric_value=87.5,
        threshold_value=85.0,
        is_resolved=False
    )
    test_db_session.add(alert)
    test_db_session.commit()
    test_db_session.refresh(alert)
    return alert


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing"""
    return {
        "node_id": 1,
        "node_name": "test-node-1",
        "node_ip": "192.168.1.100",
        "os_type": "Ubuntu",
        "environment": "production",
        "system_metrics": {
            "cpu_percent": 75.5,
            "memory_percent": 68.2,
            "disk_percent": 45.0,
            "memory_used_mb": 3400,
            "disk_used_gb": 120
        }
    }


@pytest.fixture
def sample_historical_data():
    """Sample historical metrics data"""
    return [
        {"cpu_percent": 50.0, "memory_percent": 60.0, "disk_percent": 40.0},
        {"cpu_percent": 55.0, "memory_percent": 62.0, "disk_percent": 41.0},
        {"cpu_percent": 58.0, "memory_percent": 65.0, "disk_percent": 42.0},
    ]


@pytest.fixture
def sample_ml_predictions():
    """Sample ML predictions"""
    return {
        "is_anomaly": True,
        "anomaly_score": 0.85,
        "confidence": 0.92,
        "isolation_forest_score": -0.45,
        "lstm_score": 18.5,
        "prediction": {
            "cpu_percent": 65.0,
            "memory_percent": 70.0,
            "disk_percent": 45.0
        }
    }


@pytest.fixture
def mock_crew():
    """Mock CrewAI Crew object"""
    mock = Mock()
    mock.kickoff = Mock(return_value="Mock crew result")
    return mock


@pytest.fixture
def mock_observer_agent():
    """Mock Observer Agent"""
    mock = Mock()
    mock.agent = Mock()
    mock.create_observation_task = Mock()
    mock.create_trend_analysis_task = Mock()
    return mock


@pytest.fixture
def mock_analyzer_agent():
    """Mock Analyzer Agent"""
    mock = Mock()
    mock.agent = Mock()
    mock.create_anomaly_detection_task = Mock()
    return mock


@pytest.fixture
def mock_executor_agent():
    """Mock Executor Agent"""
    mock = Mock()
    mock.agent = Mock()
    mock.create_action_planning_task = Mock()
    return mock


@pytest.fixture
def mock_alerter_agent():
    """Mock Alerter Agent"""
    mock = Mock()
    mock.agent = Mock()
    mock.create_alert_decision_task = Mock()
    mock.create_message_formatting_task = Mock()
    return mock


@pytest.fixture
def mock_email_handler():
    """Mock Email Handler"""
    mock = AsyncMock()
    mock.send_alert = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_telegram_handler():
    """Mock Telegram Handler"""
    mock = AsyncMock()
    mock.send_alert = AsyncMock(return_value=True)
    mock.send_resolution = AsyncMock(return_value=True)
    return mock
