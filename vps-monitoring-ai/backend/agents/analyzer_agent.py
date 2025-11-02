"""
Analyzer Agent - Detects anomalies and explains system behavior
Uses ML models and rule-based logic for intelligent analysis
"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
from loguru import logger

from backend.config.settings import settings


class AnalyzerAgent:
    """Agent responsible for analyzing observations and detecting anomalies"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.4,
            api_key=settings.openai_api_key
        )
        
        self.agent = Agent(
            role="System Analyst & Anomaly Detector",
            goal="Analyze system observations, detect anomalies using ML models and rules, "
                 "explain root causes, and determine if automated actions are required",
            backstory="You are a senior DevOps engineer and data scientist with expertise in "
                     "anomaly detection, root cause analysis, and predictive maintenance. "
                     "You have worked on mission-critical systems where downtime costs millions. "
                     "You combine statistical analysis, machine learning insights, and deep system "
                     "knowledge to make accurate assessments. You always explain your reasoning clearly.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_anomaly_detection_task(
        self, 
        observation: str, 
        ml_predictions: Optional[Dict[str, Any]] = None,
        historical_context: Optional[str] = None
    ) -> Task:
        """
        Create a task to detect and analyze anomalies
        
        Args:
            observation: Observation report from ObserverAgent
            ml_predictions: ML model predictions and anomaly scores
            historical_context: Context from previous similar incidents
        
        Returns:
            Task object for anomaly analysis
        """
        ml_info = ""
        if ml_predictions:
            ml_info = f"""
            ## ML Model Insights:
            - Anomaly Score: {ml_predictions.get('anomaly_score', 0):.2f} 
              (Threshold: {settings.anomaly_threshold})
            - Is Anomaly: {ml_predictions.get('is_anomaly', False)}
            - Model Confidence: {ml_predictions.get('confidence', 0):.1f}%
            - Similar Past Incidents: {ml_predictions.get('similar_incidents', 0)}
            """
        
        history_info = ""
        if historical_context:
            history_info = f"""
            ## Historical Context:
            {historical_context}
            """
        
        description = f"""
        Analyze the following system observation for anomalies and determine required actions.
        
        ## Current Observation:
        {observation}
        
        {ml_info}
        {history_info}
        
        ## Analysis Guidelines:
        1. **Threshold-based**: Check if metrics exceed warning/critical thresholds
        2. **ML-based**: Consider anomaly scores from ML models
        3. **Pattern-based**: Look for unusual patterns (e.g., sudden spikes, oscillations)
        4. **Container-specific**: Identify misbehaving containers
        5. **Root Cause**: Explain WHY the issue is occurring
        
        ## Action Decision Criteria:
        - **Immediate Action Required** if:
          * Critical threshold exceeded (CPU>85%, Memory>90%, Disk>95%)
          * Container crashed or stuck restarting
          * Anomaly score > {settings.anomaly_threshold} with high confidence
          * System stability at risk
        
        - **Monitoring Required** if:
          * Warning threshold exceeded but stable
          * Gradual resource increase detected
          * Minor anomalies without immediate risk
        
        - **No Action Required** if:
          * All metrics within normal ranges
          * Expected behavior (e.g., scheduled jobs)
          * Low confidence anomaly predictions
        
        ## Your Task:
        Provide a comprehensive analysis with:
        1. Anomaly Classification: [CRITICAL/WARNING/NORMAL]
        2. Root Cause Analysis: Explain what's causing the issue
        3. Risk Assessment: What could happen if not addressed
        4. Recommended Actions: Specific actions to take (or none if stable)
        5. Reasoning: Clear explanation of your decision
        """
        
        return Task(
            description=description,
            expected_output="Structured anomaly analysis with classification, root cause, "
                          "risk assessment, recommended actions, and reasoning",
            agent=self.agent
        )
    
    def create_correlation_task(self, multi_node_data: Dict[str, Any]) -> Task:
        """
        Create a task to correlate issues across multiple nodes
        
        Args:
            multi_node_data: Data from multiple nodes for correlation
        
        Returns:
            Task object for correlation analysis
        """
        description = f"""
        Analyze potential correlations between issues across {len(multi_node_data)} nodes.
        
        ## Multi-Node Overview:
        {self._format_multi_node_summary(multi_node_data)}
        
        ## Your Task:
        1. Identify if issues on one node are related to issues on other nodes
        2. Detect cascade failures or distributed system problems
        3. Determine if there's a common root cause affecting multiple nodes
        4. Assess if actions on one node might impact other nodes
        5. Provide coordinated action recommendations
        
        Look for patterns like:
        - Network issues affecting multiple nodes
        - Database overload impacting all connected services
        - Distributed cache problems
        - Load balancing issues
        """
        
        return Task(
            description=description,
            expected_output="Multi-node correlation analysis with coordinated recommendations",
            agent=self.agent
        )
    
    def create_explanation_task(self, action_history: List[Dict[str, Any]]) -> Task:
        """
        Create a task to explain what happened after actions were taken
        
        Args:
            action_history: List of actions taken and their results
        
        Returns:
            Task object for generating explanations
        """
        description = f"""
        Explain the impact of recent automated actions.
        
        ## Actions Taken:
        {self._format_action_history(action_history)}
        
        ## Your Task:
        1. Summarize what actions were taken and why
        2. Explain the outcome (success/failure)
        3. Analyze the impact on system health
        4. Determine if further actions are needed
        5. Provide a clear explanation for audit and user understanding
        
        Make your explanation clear for both technical and non-technical stakeholders.
        """
        
        return Task(
            description=description,
            expected_output="Clear explanation of actions, outcomes, and impact",
            agent=self.agent
        )
    
    def _format_multi_node_summary(self, multi_node_data: Dict[str, Any]) -> str:
        """Format multi-node data for correlation task"""
        summary = []
        for node_id, node_data in multi_node_data.items():
            summary.append(
                f"Node {node_id}: CPU {node_data.get('cpu', 0):.1f}%, "
                f"Memory {node_data.get('memory', 0):.1f}%, "
                f"Status: {node_data.get('status', 'unknown')}"
            )
        return "\n".join(summary)
    
    def _format_action_history(self, actions: List[Dict[str, Any]]) -> str:
        """Format action history for explanation task"""
        if not actions:
            return "No recent actions taken"
        
        formatted = []
        for action in actions:
            formatted.append(
                f"- {action.get('timestamp', 'Unknown time')}: "
                f"{action.get('action_type', 'Unknown action')} on "
                f"{action.get('target', 'unknown target')} - "
                f"Result: {action.get('status', 'unknown')}"
            )
        return "\n".join(formatted)
