"""
Alerter Agent - Manages alerts and notifications
Decides when to alert, formats messages, and tracks alert states
"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any
from loguru import logger

from backend.config.settings import settings


class AlerterAgent:
    """Agent responsible for intelligent alerting and notifications"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key
        )
        
        self.agent = Agent(
            role="Alert Manager & Communication Specialist",
            goal="Determine when to send alerts, craft clear and actionable notifications, "
                 "prevent alert fatigue, and ensure critical issues reach the right people",
            backstory="You are an experienced incident commander who has managed thousands of alerts. "
                     "You understand the balance between being thorough and avoiding alert fatigue. "
                     "You know that poorly crafted alerts lead to ignored notifications. "
                     "You write clear, concise, and actionable alerts that help people make quick decisions. "
                     "You prioritize alerts based on business impact and urgency.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_alert_decision_task(
        self, 
        analysis: str,
        recent_alerts: List[Dict[str, Any]],
        node_info: Dict[str, Any]
    ) -> Task:
        """
        Create a task to decide if an alert should be sent
        
        Args:
            analysis: Analysis from AnalyzerAgent
            recent_alerts: Recent alerts to avoid duplicates
            node_info: Information about the node
        
        Returns:
            Task object for alert decision
        """
        recent_alerts_summary = self._format_recent_alerts(recent_alerts)
        
        description = f"""
        Decide if an alert should be sent based on the following analysis.
        
        ## System Analysis:
        {analysis}
        
        ## Node Information:
        - Node: {node_info.get('name', 'Unknown')}
        - IP: {node_info.get('ip_address', 'Unknown')}
        - Environment: {node_info.get('environment', 'Unknown')}
        
        ## Recent Alerts (Last 24h):
        {recent_alerts_summary}
        
        ## Alert Decision Guidelines:
        
        ### SEND CRITICAL ALERT if:
        - System is in CRITICAL state (>85% CPU, >90% Memory, >95% Disk)
        - Container crash loop or repeated failures
        - Automated actions failed to resolve the issue
        - Potential data loss or service outage imminent
        - Issue requires immediate human intervention
        
        ### SEND WARNING ALERT if:
        - Metrics in WARNING range but stable
        - Unusual patterns detected but system operational
        - Proactive notification for trend that will become critical
        - First occurrence of a new issue type
        
        ### DO NOT SEND ALERT if:
        - Duplicate of recent alert (within last 1 hour)
        - Issue already resolved by automated actions
        - Metrics within normal operating ranges
        - Temporary spike that has already recovered
        - Alert would contribute to alert fatigue
        
        ## Your Task:
        Provide an alert decision with:
        1. **Decision**: [SEND_CRITICAL/SEND_WARNING/DO_NOT_SEND]
        2. **Severity**: [CRITICAL/WARNING/INFO]
        3. **Reasoning**: Why alert should or should not be sent
        4. **Channels**: [EMAIL/TELEGRAM/BOTH] if sending
        5. **Deduplication**: Is this a duplicate? Should it be suppressed?
        6. **Urgency**: [IMMEDIATE/SCHEDULED/BATCHED]
        """
        
        return Task(
            description=description,
            expected_output="Alert decision with severity, reasoning, channels, and urgency",
            agent=self.agent
        )
    
    def create_message_formatting_task(
        self, 
        alert_decision: Dict[str, Any],
        incident_data: Dict[str, Any]
    ) -> Task:
        """
        Create a task to format alert messages for different channels
        
        Args:
            alert_decision: Decision from alert_decision_task
            incident_data: Full context about the incident
        
        Returns:
            Task object for message formatting
        """
        description = f"""
        Format alert messages for {alert_decision.get('channels', 'EMAIL')} channel(s).
        
        ## Alert Context:
        - Severity: {alert_decision.get('severity', 'WARNING')}
        - Node: {incident_data.get('node_name', 'Unknown')}
        - Issue Type: {incident_data.get('issue_type', 'Unknown')}
        - Current State: {incident_data.get('current_state', 'Unknown')}
        
        ## Incident Details:
        {incident_data.get('details', 'No details available')}
        
        ## Actions Taken:
        {incident_data.get('actions_taken', 'No actions taken yet')}
        
        ## Message Formatting Guidelines:
        
        ### For EMAIL:
        - Subject: [SEVERITY] Node Name - Brief Issue Description
        - Body should include:
          * **Summary**: One-line description
          * **Impact**: What services/users are affected
          * **Current Status**: Latest metrics and state
          * **Actions Taken**: What automated actions occurred
          * **Root Cause**: If known
          * **Required Action**: What human needs to do (if any)
          * **Timeline**: When issue started
        - Use clear formatting (headers, bullet points)
        - Include dashboard links for deeper investigation
        
        ### For TELEGRAM:
        - Keep it concise (under 300 words)
        - Use emoji for quick visual scanning:
          * 🔴 Critical
          * ⚠️ Warning
          * 📊 Metrics
          * 🔧 Actions
          * ✅ Resolved
        - First line should be most critical info
        - Include node name and severity
        - Add quick action buttons if applicable
        
        ## Your Task:
        Create formatted messages for each channel:
        1. Email subject line
        2. Email body (HTML-friendly)
        3. Telegram message (with emojis)
        4. Include all relevant context
        5. Make messages actionable and clear
        """
        
        return Task(
            description=description,
            expected_output="Formatted alert messages for email and/or Telegram with proper structure",
            agent=self.agent
        )
    
    def create_alert_resolution_task(
        self, 
        alert_id: int,
        resolution_data: Dict[str, Any]
    ) -> Task:
        """
        Create a task to format resolution notifications
        
        Args:
            alert_id: ID of the alert being resolved
            resolution_data: Data about how the issue was resolved
        
        Returns:
            Task object for resolution notification
        """
        description = f"""
        Create a resolution notification for alert #{alert_id}.
        
        ## Resolution Information:
        - Issue: {resolution_data.get('issue_description', 'Unknown')}
        - Resolution Method: {resolution_data.get('resolution_method', 'Unknown')}
        - Duration: {resolution_data.get('duration_minutes', 0)} minutes
        - Final Status: {resolution_data.get('final_status', 'Unknown')}
        
        ## Metrics After Resolution:
        {resolution_data.get('final_metrics', 'Not available')}
        
        ## Your Task:
        Create a resolution message that:
        1. Confirms the issue is resolved
        2. Explains what fixed it
        3. Shows before/after metrics
        4. Indicates if manual intervention was needed
        5. Provides any follow-up recommendations
        
        Keep it brief and positive while being informative.
        """
        
        return Task(
            description=description,
            expected_output="Concise resolution notification with outcome and follow-up",
            agent=self.agent
        )
    
    def _format_recent_alerts(self, alerts: List[Dict[str, Any]]) -> str:
        """Format recent alerts for task description"""
        if not alerts:
            return "No recent alerts in the last 24 hours"
        
        formatted = []
        for alert in alerts[:5]:  # Show last 5
            formatted.append(
                f"- [{alert.get('severity', 'UNKNOWN')}] {alert.get('timestamp', 'Unknown time')}: "
                f"{alert.get('title', 'No title')} - "
                f"{'Resolved' if alert.get('is_resolved') else 'Active'}"
            )
        
        if len(alerts) > 5:
            formatted.append(f"... and {len(alerts) - 5} more alerts")
        
        return "\n".join(formatted)
