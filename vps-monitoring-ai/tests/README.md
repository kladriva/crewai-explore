# VPS Monitoring AI - Unit Tests

This directory contains comprehensive unit tests for the VPS Monitoring AI system.

## Test Coverage

### 1. **CrewOrchestrator Tests** (`test_crew_orchestrator.py`)
- ✅ Agent initialization and coordination
- ✅ Complete workflow sequencing: Observe → Analyze → Execute → Alert
- ✅ End-to-end metrics processing
- ✅ Trend analysis with historical data
- ✅ Action decision logic
- ✅ Alert message formatting
- ✅ Error handling

### 2. **AnomalyDetector Tests** (`test_anomaly_detector.py`)
- ✅ Isolation Forest training with various data scenarios
- ✅ LSTM model training for time-series patterns
- ✅ Prediction with both models
- ✅ Edge cases: zero values, extreme values, negative values
- ✅ Insufficient data handling
- ✅ Model persistence and loading
- ✅ Error handling in predictions

### 3. **AlertManager Tests** (`test_alert_manager.py`)
- ✅ Alert creation and database storage
- ✅ Duplicate alert detection and prevention
- ✅ Multi-channel dispatch (Email & Telegram)
- ✅ Alert resolution workflow
- ✅ Cache management
- ✅ Different severity levels
- ✅ Handler failure recovery

### 4. **Backend API CRUD Tests** (`test_api_crud.py`)
- ✅ Node management (Create, Read, Update, Delete)
- ✅ Container management (Create, Read, Update, Delete)
- ✅ Data integrity and constraints
- ✅ Relationship integrity (Node-Container, Node-Alert, etc.)
- ✅ Metric retrieval operations
- ✅ Bulk operations
- ✅ Time-based queries

### 5. **Authentication & RBAC Tests** (`test_authentication.py`)
- ✅ User authentication with password hashing
- ✅ JWT token creation and validation
- ✅ Token expiration handling
- ✅ Role-based access control (Admin, Operator, Viewer)
- ✅ Permission checking
- ✅ User management operations
- ✅ Password security features

## Setup

### Prerequisites

Install test dependencies:

```bash
cd vps-monitoring-ai
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov pytest-mock
```

Additional test dependencies:
```bash
pip install pytest==7.4.3 pytest-asyncio==0.21.1 pytest-cov==4.1.0
```

### Environment Variables

Create a `.env.test` file for test settings:

```env
OPENAI_API_KEY=test-key
MYSQL_USER=test_user
MYSQL_PASSWORD=test_password
MYSQL_DATABASE=test_db
SMTP_USER=test@example.com
SMTP_PASSWORD=test_password
ALERT_FROM_EMAIL=alerts@example.com
TELEGRAM_BOT_TOKEN=test-token
TELEGRAM_CHAT_ID=12345
JWT_SECRET_KEY=test-secret-key-change-in-production
INFLUX_TOKEN=test-influx-token
```

## Running Tests

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test File

```bash
pytest tests/test_crew_orchestrator.py -v
pytest tests/test_anomaly_detector.py -v
pytest tests/test_alert_manager.py -v
pytest tests/test_api_crud.py -v
pytest tests/test_authentication.py -v
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit -v

# Run only async tests
pytest -m asyncio -v

# Run slow tests separately
pytest -m slow -v

# Exclude slow tests
pytest -m "not slow" -v
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=backend --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
xdg-open htmlcov/index.html  # Linux
```

### Run Specific Test Class

```bash
pytest tests/test_crew_orchestrator.py::TestCrewOrchestrator -v
pytest tests/test_anomaly_detector.py::TestAnomalyDetector -v
```

### Run Specific Test Method

```bash
pytest tests/test_crew_orchestrator.py::TestCrewOrchestrator::test_initialization -v
```

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── test_crew_orchestrator.py      # CrewAI orchestration tests
├── test_anomaly_detector.py       # ML anomaly detection tests
├── test_alert_manager.py          # Alert management tests
├── test_api_crud.py               # Backend API CRUD tests
├── test_authentication.py         # Authentication & RBAC tests
└── README.md                      # This file
```

## Fixtures

Common fixtures available in `conftest.py`:

- `test_settings`: Test configuration settings
- `test_db_engine`: In-memory SQLite database
- `test_db_session`: Database session
- `sample_node`: Sample VPS node
- `sample_user`: Sample user account
- `sample_container`: Sample Docker container
- `sample_alert`: Sample alert
- `sample_metrics_data`: Sample metrics
- `mock_*`: Various mocked components

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-cov
      - run: pytest tests/ --cov=backend --cov-report=xml
      - uses: codecov/codecov-action@v3
```

## Test Best Practices

1. **Isolation**: Each test is independent and doesn't affect others
2. **Fixtures**: Reusable test data via pytest fixtures
3. **Mocking**: External dependencies are mocked appropriately
4. **Async Support**: Async tests use `pytest-asyncio`
5. **Edge Cases**: Tests include edge cases and error scenarios
6. **Coverage**: Aim for >80% code coverage

## Troubleshooting

### Database Issues

If you encounter database-related errors:
- Tests use in-memory SQLite, no MySQL required
- Each test gets a fresh database session
- Database is cleaned up automatically after each test

### Async Test Failures

If async tests fail:
- Ensure `pytest-asyncio` is installed
- Check `asyncio_mode = auto` in `pytest.ini`
- Use `@pytest.mark.asyncio` decorator

### Import Errors

If you encounter import errors:
- Run tests from the project root directory
- Ensure `backend` module is in Python path
- Check that `conftest.py` is in the tests directory

## Writing New Tests

When adding new tests:

1. Create test file with `test_` prefix
2. Organize tests into classes with `Test` prefix
3. Use descriptive test method names with `test_` prefix
4. Add appropriate markers: `@pytest.mark.unit`, `@pytest.mark.asyncio`
5. Use fixtures from `conftest.py` when possible
6. Include docstrings explaining what is being tested
7. Test both success and failure scenarios
8. Include edge cases

Example:

```python
@pytest.mark.unit
class TestMyComponent:
    """Test MyComponent functionality"""
    
    def test_normal_operation(self, sample_fixture):
        """Test component works under normal conditions"""
        result = my_function(sample_fixture)
        assert result is not None
    
    def test_edge_case_empty_input(self):
        """Test component handles empty input"""
        result = my_function([])
        assert result == expected_default
```

## License

Copyright © 2024 VPS Monitoring AI Project
