"""
Crew Orchestrator - Coordinates all agents to work together
Manages the workflow: Observe → Analyze → Execute → Alert
"""
from crewai import Crew, Process
from typing import Dict, List, Any, Optional
from loguru import logger
from datetime import datetime

from backend.agents.observer_agent import ObserverAgent
from backend.agents.analyzer_agent import AnalyzerAgent
from backend.agents.executor_agent import ExecutorAgent
from backend.agents.alerter_agent import AlerterAgent


class CrewOrchestrator:
    """
    Orchestrates the multi-agent monitoring system
    
    Workflow:
    1. Observer Agent: Collects and observes metrics
    2. Analyzer Agent: Detects anomalies and explains issues
    3. Executor Agent: Plans and executes remediation
    4. Alerter Agent: Decides and sends notifications
    """
    
    def __init__(self):
        """Initialize all agents"""
        logger.info("Initializing CrewAI Orchestrator with all agents...")
        
        self.observer = ObserverAgent()
        self.analyzer = AnalyzerAgent()
        self.executor = ExecutorAgent()
        self.alerter = AlerterAgent()
        
        logger.success("All agents initialized successfully")
    
    async def process_metrics(
        self, 
        metrics_data: Dict[str, Any],
        ml_predictions: Optional[Dict[str, Any]] = None,
        historical_data: Optional[List[Dict[str, Any]]] = None,
        recent_alerts: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Main processing pipeline for incoming metrics
        
        Args:
            metrics_data: Current metrics from node
            ml_predictions: ML model predictions
            historical_data: Historical metrics for trend analysis
            recent_alerts: Recent alerts to avoid duplication
        
        Returns:
            Dictionary with observation, analysis, actions, and alerts
        """
        logger.info(f"Processing metrics for node: {metrics_data.get('node_name', 'Unknown')}")
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "node_name": metrics_data.get("node_name"),
            "observation": None,
            "analysis": None,
            "action_plan": None,
            "actions_executed": [],
            "alert_decision": None,
            "alert_messages": None
        }
        
        try:
            # STEP 1: Observer Agent - Analyze current state
            logger.info("Step 1: Observer Agent analyzing metrics...")
            observation_task = self.observer.create_observation_task(metrics_data)
            
            # Create crew for observation
            observation_crew = Crew(
                agents=[self.observer.agent],
                tasks=[observation_task],
                process=Process.sequential,
                verbose=False
            )
            
            observation_result = observation_crew.kickoff()
            result["observation"] = str(observation_result)
            logger.debug(f"Observation: {result['observation'][:200]}...")
            
            # Optional: Trend analysis if historical data available
            if historical_data and len(historical_data) > 1:
                logger.info("Step 1b: Observer Agent analyzing trends...")
                trend_task = self.observer.create_trend_analysis_task(historical_data)
                if trend_task:
                    trend_crew = Crew(
                        agents=[self.observer.agent],
                        tasks=[trend_task],
                        process=Process.sequential,
                        verbose=False
                    )
                    trend_result = trend_crew.kickoff()
                    result["trend_analysis"] = str(trend_result)
            
            # STEP 2: Analyzer Agent - Detect anomalies
            logger.info("Step 2: Analyzer Agent detecting anomalies...")
            analysis_task = self.analyzer.create_anomaly_detection_task(
                observation=result["observation"],
                ml_predictions=ml_predictions,
                historical_context=result.get("trend_analysis")
            )
            
            analysis_crew = Crew(
                agents=[self.analyzer.agent],
                tasks=[analysis_task],
                process=Process.sequential,
                verbose=False
            )
            
            analysis_result = analysis_crew.kickoff()
            result["analysis"] = str(analysis_result)
            logger.debug(f"Analysis: {result['analysis'][:200]}...")
            
            # Determine if actions are needed based on analysis
            needs_action = self._should_take_action(result["analysis"])
            
            # STEP 3: Executor Agent - Plan and execute actions (if needed)
            if needs_action:
                logger.info("Step 3: Executor Agent planning actions...")
                
                # Get current action count for safety limits
                current_actions = self._get_current_hour_action_count(metrics_data.get("node_id"))
                
                action_planning_task = self.executor.create_action_planning_task(
                    analysis=result["analysis"],
                    current_actions_count=current_actions,
                    node_info={
                        "name": metrics_data.get("node_name"),
                        "ip_address": metrics_data.get("node_ip"),
                        "os_type": metrics_data.get("os_type")
                    }
                )
                
                executor_crew = Crew(
                    agents=[self.executor.agent],
                    tasks=[action_planning_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                action_plan_result = executor_crew.kickoff()
                result["action_plan"] = str(action_plan_result)
                logger.info(f"Action plan created: {result['action_plan'][:200]}...")
            else:
                logger.info("Step 3: No actions needed based on analysis")
                result["action_plan"] = "NO_ACTION_REQUIRED"
            
            # STEP 4: Alerter Agent - Decide on alerts
            logger.info("Step 4: Alerter Agent deciding on alerts...")
            
            alert_decision_task = self.alerter.create_alert_decision_task(
                analysis=result["analysis"],
                recent_alerts=recent_alerts or [],
                node_info={
                    "name": metrics_data.get("node_name"),
                    "ip_address": metrics_data.get("node_ip"),
                    "environment": metrics_data.get("environment", "production")
                }
            )
            
            alerter_crew = Crew(
                agents=[self.alerter.agent],
                tasks=[alert_decision_task],
                process=Process.sequential,
                verbose=False
            )
            
            alert_decision_result = alerter_crew.kickoff()
            result["alert_decision"] = str(alert_decision_result)
            
            # If alert should be sent, format messages
            if self._should_send_alert(result["alert_decision"]):
                logger.info("Step 4b: Formatting alert messages...")
                
                message_task = self.alerter.create_message_formatting_task(
                    alert_decision=self._parse_alert_decision(result["alert_decision"]),
                    incident_data={
                        "node_name": metrics_data.get("node_name"),
                        "issue_type": self._extract_issue_type(result["analysis"]),
                        "current_state": result["observation"],
                        "details": result["analysis"],
                        "actions_taken": result.get("action_plan", "None")
                    }
                )
                
                message_crew = Crew(
                    agents=[self.alerter.agent],
                    tasks=[message_task],
                    process=Process.sequential,
                    verbose=False
                )
                
                message_result = message_crew.kickoff()
                result["alert_messages"] = str(message_result)
            
            logger.success(f"Metrics processing complete for {metrics_data.get('node_name')}")
            return result
            
        except Exception as e:
            logger.error(f"Error in crew orchestration: {e}", exc_info=True)
            result["error"] = str(e)
            return result
    
    def _should_take_action(self, analysis: str) -> bool:
        """Determine if actions should be taken based on analysis"""
        analysis_lower = analysis.lower()
        action_keywords = [
            "immediate action required",
            "critical",
            "action required",
            "recommended actions",
            "should restart",
            "should clear"
        ]
        return any(keyword in analysis_lower for keyword in action_keywords)
    
    def _should_send_alert(self, alert_decision: str) -> bool:
        """Determine if alert should be sent based on decision"""
        decision_lower = alert_decision.lower()
        return "send_critical" in decision_lower or "send_warning" in decision_lower
    
    def _parse_alert_decision(self, alert_decision: str) -> Dict[str, Any]:
        """Parse alert decision text into structured data"""
        # Simple parsing - in production, use more robust parsing
        return {
            "severity": "WARNING" if "warning" in alert_decision.lower() else "CRITICAL",
            "channels": "BOTH"
        }
    
    def _extract_issue_type(self, analysis: str) -> str:
        """Extract issue type from analysis"""
        analysis_lower = analysis.lower()
        if "cpu" in analysis_lower:
            return "High CPU Usage"
        elif "memory" in analysis_lower:
            return "High Memory Usage"
        elif "disk" in analysis_lower:
            return "High Disk Usage"
        elif "container" in analysis_lower:
            return "Container Issue"
        else:
            return "System Anomaly"
    
    def _get_current_hour_action_count(self, node_id: Optional[int]) -> int:
        """Get count of actions taken in current hour (placeholder)"""
        # TODO: Implement actual count from database
        return 0
