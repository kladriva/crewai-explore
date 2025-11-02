"""
Unit tests for CrewOrchestrator
Tests agent task sequencing and end-to-end metrics processing
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.agents.crew_orchestrator import CrewOrchestrator


@pytest.mark.unit
class TestCrewOrchestrator:
    """Test CrewOrchestrator agent coordination"""
    
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    def test_initialization(self, mock_alerter, mock_executor, mock_analyzer, mock_observer):
        """Test that all agents are initialized correctly"""
        orchestrator = CrewOrchestrator()
        
        assert orchestrator.observer is not None
        assert orchestrator.analyzer is not None
        assert orchestrator.executor is not None
        assert orchestrator.alerter is not None
        
        mock_observer.assert_called_once()
        mock_analyzer.assert_called_once()
        mock_executor.assert_called_once()
        mock_alerter.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.agents.crew_orchestrator.Crew')
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    async def test_process_metrics_full_workflow(
        self, mock_alerter_cls, mock_executor_cls, mock_analyzer_cls, mock_observer_cls, mock_crew_cls,
        sample_metrics_data, sample_ml_predictions
    ):
        """Test complete metrics processing workflow: Observe -> Analyze -> Execute -> Alert"""
        # Setup mocks
        mock_observer = Mock()
        mock_observer.agent = Mock()
        mock_observer.create_observation_task = Mock(return_value=Mock())
        mock_observer_cls.return_value = mock_observer
        
        mock_analyzer = Mock()
        mock_analyzer.agent = Mock()
        mock_analyzer.create_anomaly_detection_task = Mock(return_value=Mock())
        mock_analyzer_cls.return_value = mock_analyzer
        
        mock_executor = Mock()
        mock_executor.agent = Mock()
        mock_executor.create_action_planning_task = Mock(return_value=Mock())
        mock_executor_cls.return_value = mock_executor
        
        mock_alerter = Mock()
        mock_alerter.agent = Mock()
        mock_alerter.create_alert_decision_task = Mock(return_value=Mock())
        mock_alerter_cls.return_value = mock_alerter
        
        # Mock Crew responses
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff = Mock(side_effect=[
            "Observation: High CPU usage detected",
            "Analysis: Immediate action required - CPU at 85%",
            "Action Plan: Restart service XYZ",
            "Alert Decision: SEND_CRITICAL to both channels"
        ])
        mock_crew_cls.return_value = mock_crew_instance
        
        # Execute
        orchestrator = CrewOrchestrator()
        result = await orchestrator.process_metrics(
            metrics_data=sample_metrics_data,
            ml_predictions=sample_ml_predictions
        )
        
        # Verify workflow sequence
        assert result["observation"] is not None
        assert result["analysis"] is not None
        assert result["action_plan"] is not None
        assert result["alert_decision"] is not None
        assert "node_name" in result
        assert "timestamp" in result
        
        # Verify all agents were called
        mock_observer.create_observation_task.assert_called_once()
        mock_analyzer.create_anomaly_detection_task.assert_called_once()
        mock_executor.create_action_planning_task.assert_called_once()
        mock_alerter.create_alert_decision_task.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.agents.crew_orchestrator.Crew')
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    async def test_process_metrics_no_action_needed(
        self, mock_alerter_cls, mock_executor_cls, mock_analyzer_cls, mock_observer_cls, mock_crew_cls,
        sample_metrics_data
    ):
        """Test workflow when no action is needed"""
        # Setup mocks
        mock_observer_cls.return_value = Mock(agent=Mock(), create_observation_task=Mock(return_value=Mock()))
        mock_analyzer_cls.return_value = Mock(agent=Mock(), create_anomaly_detection_task=Mock(return_value=Mock()))
        mock_executor_cls.return_value = Mock(agent=Mock())
        mock_alerter_cls.return_value = Mock(agent=Mock(), create_alert_decision_task=Mock(return_value=Mock()))
        
        # Mock Crew responses - no action required
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff = Mock(side_effect=[
            "Observation: All metrics normal",
            "Analysis: No issues detected, system operating normally",
            "Alert Decision: NO_ALERT"
        ])
        mock_crew_cls.return_value = mock_crew_instance
        
        orchestrator = CrewOrchestrator()
        result = await orchestrator.process_metrics(metrics_data=sample_metrics_data)
        
        assert result["action_plan"] == "NO_ACTION_REQUIRED"
        assert result["observation"] is not None
        assert result["analysis"] is not None
    
    @pytest.mark.asyncio
    @patch('backend.agents.crew_orchestrator.Crew')
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    async def test_process_metrics_with_trend_analysis(
        self, mock_alerter_cls, mock_executor_cls, mock_analyzer_cls, mock_observer_cls, mock_crew_cls,
        sample_metrics_data, sample_historical_data
    ):
        """Test workflow with historical data for trend analysis"""
        # Setup mocks
        mock_observer = Mock()
        mock_observer.agent = Mock()
        mock_observer.create_observation_task = Mock(return_value=Mock())
        mock_observer.create_trend_analysis_task = Mock(return_value=Mock())
        mock_observer_cls.return_value = mock_observer
        
        mock_analyzer_cls.return_value = Mock(agent=Mock(), create_anomaly_detection_task=Mock(return_value=Mock()))
        mock_executor_cls.return_value = Mock(agent=Mock())
        mock_alerter_cls.return_value = Mock(agent=Mock(), create_alert_decision_task=Mock(return_value=Mock()))
        
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff = Mock(side_effect=[
            "Observation: Current state",
            "Trend: Increasing CPU trend over time",
            "Analysis: Upward trend detected",
            "Alert Decision: SEND_WARNING"
        ])
        mock_crew_cls.return_value = mock_crew_instance
        
        orchestrator = CrewOrchestrator()
        result = await orchestrator.process_metrics(
            metrics_data=sample_metrics_data,
            historical_data=sample_historical_data
        )
        
        assert "trend_analysis" in result
        mock_observer.create_trend_analysis_task.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('backend.agents.crew_orchestrator.Crew')
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    async def test_process_metrics_error_handling(
        self, mock_alerter_cls, mock_executor_cls, mock_analyzer_cls, mock_observer_cls, mock_crew_cls,
        sample_metrics_data
    ):
        """Test error handling during metrics processing"""
        # Setup mocks to raise exception
        mock_observer_cls.return_value = Mock(agent=Mock(), create_observation_task=Mock(return_value=Mock()))
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff = Mock(side_effect=Exception("Test error"))
        mock_crew_cls.return_value = mock_crew_instance
        
        orchestrator = CrewOrchestrator()
        result = await orchestrator.process_metrics(metrics_data=sample_metrics_data)
        
        assert "error" in result
        assert result["error"] == "Test error"
    
    def test_should_take_action_with_critical_keyword(self):
        """Test action decision with critical keyword"""
        orchestrator = CrewOrchestrator()
        
        analysis = "System is in CRITICAL state, immediate action required"
        assert orchestrator._should_take_action(analysis) is True
    
    def test_should_take_action_with_restart_recommendation(self):
        """Test action decision with restart recommendation"""
        orchestrator = CrewOrchestrator()
        
        analysis = "Service performance degraded, should restart the container"
        assert orchestrator._should_take_action(analysis) is True
    
    def test_should_take_action_normal_state(self):
        """Test action decision when system is normal"""
        orchestrator = CrewOrchestrator()
        
        analysis = "All systems operating normally, no issues detected"
        assert orchestrator._should_take_action(analysis) is False
    
    def test_should_send_alert_critical(self):
        """Test alert decision for critical severity"""
        orchestrator = CrewOrchestrator()
        
        decision = "SEND_CRITICAL alert to both channels immediately"
        assert orchestrator._should_send_alert(decision) is True
    
    def test_should_send_alert_warning(self):
        """Test alert decision for warning severity"""
        orchestrator = CrewOrchestrator()
        
        decision = "SEND_WARNING alert via email"
        assert orchestrator._should_send_alert(decision) is True
    
    def test_should_not_send_alert(self):
        """Test alert decision when no alert needed"""
        orchestrator = CrewOrchestrator()
        
        decision = "NO_ALERT - situation is under control"
        assert orchestrator._should_send_alert(decision) is False
    
    def test_parse_alert_decision_critical(self):
        """Test parsing critical alert decision"""
        orchestrator = CrewOrchestrator()
        
        decision = "SEND_CRITICAL to both channels"
        parsed = orchestrator._parse_alert_decision(decision)
        
        assert parsed["severity"] == "CRITICAL"
        assert parsed["channels"] == "BOTH"
    
    def test_parse_alert_decision_warning(self):
        """Test parsing warning alert decision"""
        orchestrator = CrewOrchestrator()
        
        decision = "SEND_WARNING alert via Telegram"
        parsed = orchestrator._parse_alert_decision(decision)
        
        assert parsed["severity"] == "WARNING"
    
    def test_extract_issue_type_cpu(self):
        """Test issue type extraction for CPU"""
        orchestrator = CrewOrchestrator()
        
        analysis = "High CPU usage detected at 92%"
        assert orchestrator._extract_issue_type(analysis) == "High CPU Usage"
    
    def test_extract_issue_type_memory(self):
        """Test issue type extraction for memory"""
        orchestrator = CrewOrchestrator()
        
        analysis = "Memory usage exceeded threshold"
        assert orchestrator._extract_issue_type(analysis) == "High Memory Usage"
    
    def test_extract_issue_type_disk(self):
        """Test issue type extraction for disk"""
        orchestrator = CrewOrchestrator()
        
        analysis = "Disk space running low"
        assert orchestrator._extract_issue_type(analysis) == "High Disk Usage"
    
    def test_extract_issue_type_container(self):
        """Test issue type extraction for container"""
        orchestrator = CrewOrchestrator()
        
        analysis = "Container health check failing"
        assert orchestrator._extract_issue_type(analysis) == "Container Issue"
    
    def test_extract_issue_type_generic(self):
        """Test issue type extraction for generic issues"""
        orchestrator = CrewOrchestrator()
        
        analysis = "Network latency detected"
        assert orchestrator._extract_issue_type(analysis) == "System Anomaly"
    
    @pytest.mark.asyncio
    @patch('backend.agents.crew_orchestrator.Crew')
    @patch('backend.agents.crew_orchestrator.ObserverAgent')
    @patch('backend.agents.crew_orchestrator.AnalyzerAgent')
    @patch('backend.agents.crew_orchestrator.ExecutorAgent')
    @patch('backend.agents.crew_orchestrator.AlerterAgent')
    async def test_process_metrics_with_alert_formatting(
        self, mock_alerter_cls, mock_executor_cls, mock_analyzer_cls, mock_observer_cls, mock_crew_cls,
        sample_metrics_data
    ):
        """Test alert message formatting when alert should be sent"""
        # Setup mocks
        mock_observer_cls.return_value = Mock(agent=Mock(), create_observation_task=Mock(return_value=Mock()))
        mock_analyzer_cls.return_value = Mock(agent=Mock(), create_anomaly_detection_task=Mock(return_value=Mock()))
        mock_executor_cls.return_value = Mock(agent=Mock())
        
        mock_alerter = Mock()
        mock_alerter.agent = Mock()
        mock_alerter.create_alert_decision_task = Mock(return_value=Mock())
        mock_alerter.create_message_formatting_task = Mock(return_value=Mock())
        mock_alerter_cls.return_value = mock_alerter
        
        mock_crew_instance = Mock()
        mock_crew_instance.kickoff = Mock(side_effect=[
            "Observation: System under stress",
            "Analysis: No issues",
            "Alert Decision: SEND_WARNING to both",
            "Formatted alert message"
        ])
        mock_crew_cls.return_value = mock_crew_instance
        
        orchestrator = CrewOrchestrator()
        result = await orchestrator.process_metrics(metrics_data=sample_metrics_data)
        
        assert result["alert_messages"] is not None
        mock_alerter.create_message_formatting_task.assert_called_once()
