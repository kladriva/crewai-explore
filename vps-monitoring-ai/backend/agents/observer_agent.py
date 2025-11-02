"""
Observer Agent - Collects and observes metrics and logs
Monitors system health and container states
"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any
from datetime import datetime
from loguru import logger

from backend.config.settings import settings


class ObserverAgent:
    """Agent responsible for observing system metrics and container states"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.3,
            api_key=settings.openai_api_key
        )
        
        self.agent = Agent(
            role="System Observer & Metrics Collector",
            goal="Continuously monitor VPS nodes, collect real-time metrics from containers, "
                 "track system resources (CPU, Memory, Disk), and identify current system state",
            backstory="You are an expert system administrator with deep knowledge of Linux systems, "
                     "Docker containers, and infrastructure monitoring. You have 15 years of experience "
                     "in large-scale distributed systems and can quickly assess system health. "
                     "You pay attention to every detail and can spot subtle changes in system behavior.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_observation_task(self, metrics_data: Dict[str, Any]) -> Task:
        """
        Create a task to analyze current metrics and system state
        
        Args:
            metrics_data: Dictionary containing node, system, and container metrics
        
        Returns:
            Task object for CrewAI
        """
        description = f"""
        Analyze the current system state for node: {metrics_data.get('node_name', 'Unknown')}
        
        ## System Metrics (Current):
        - CPU Usage: {metrics_data.get('cpu_percent', 0):.1f}%
        - Memory Usage: {metrics_data.get('memory_percent', 0):.1f}% 
          ({metrics_data.get('memory_used_mb', 0):.1f}MB / {metrics_data.get('memory_total_mb', 0):.1f}MB)
        - Disk Usage: {metrics_data.get('disk_percent', 0):.1f}%
          ({metrics_data.get('disk_used_gb', 0):.1f}GB / {metrics_data.get('disk_total_gb', 0):.1f}GB)
        
        ## Container Status:
        Total Containers: {len(metrics_data.get('containers', []))}
        
        {self._format_container_details(metrics_data.get('containers', []))}
        
        ## Thresholds:
        - CPU Warning: {settings.cpu_warning_threshold}% | Critical: {settings.cpu_critical_threshold}%
        - Memory Warning: {settings.memory_warning_threshold}% | Critical: {settings.memory_critical_threshold}%
        - Disk Warning: {settings.disk_warning_threshold}% | Critical: {settings.disk_critical_threshold}%
        
        ## Your Task:
        1. Assess the overall health of the system
        2. Identify any metrics approaching or exceeding warning/critical thresholds
        3. Note any containers consuming excessive resources
        4. Highlight any containers in abnormal states (stopped, restarting, etc.)
        5. Provide a clear summary of what you observe
        
        Return your observations in this structured format:
        - Overall Health: [HEALTHY/WARNING/CRITICAL]
        - Key Findings: [List critical observations]
        - Resource Concerns: [Specific concerns about CPU/Memory/Disk]
        - Container Issues: [Any problematic containers]
        - Recommendations: [What should be investigated further]
        """
        
        return Task(
            description=description,
            expected_output="A structured observation report with health status, key findings, "
                          "resource concerns, container issues, and recommendations",
            agent=self.agent
        )
    
    def create_trend_analysis_task(self, historical_data: List[Dict[str, Any]]) -> Task:
        """
        Create a task to analyze trends over time
        
        Args:
            historical_data: List of metrics data points over time
        
        Returns:
            Task object for trend analysis
        """
        if not historical_data:
            return None
        
        # Calculate trends
        cpu_trend = self._calculate_trend([d.get('cpu_percent', 0) for d in historical_data])
        memory_trend = self._calculate_trend([d.get('memory_percent', 0) for d in historical_data])
        disk_trend = self._calculate_trend([d.get('disk_percent', 0) for d in historical_data])
        
        description = f"""
        Analyze resource usage trends over the last {len(historical_data)} data points.
        
        ## Trends Detected:
        - CPU: {cpu_trend['direction']} ({cpu_trend['change']:.1f}% change)
        - Memory: {memory_trend['direction']} ({memory_trend['change']:.1f}% change)
        - Disk: {disk_trend['direction']} ({disk_trend['change']:.1f}% change)
        
        ## Historical Data Summary:
        - CPU Range: {min([d.get('cpu_percent', 0) for d in historical_data]):.1f}% - 
          {max([d.get('cpu_percent', 0) for d in historical_data]):.1f}%
        - Memory Range: {min([d.get('memory_percent', 0) for d in historical_data]):.1f}% - 
          {max([d.get('memory_percent', 0) for d in historical_data]):.1f}%
        
        ## Your Task:
        1. Identify concerning trends (rapid increases, sustained high usage)
        2. Predict if any resource will reach critical levels soon
        3. Determine if patterns indicate normal load or potential issues
        4. Suggest proactive measures based on trends
        """
        
        return Task(
            description=description,
            expected_output="Trend analysis with predictions and proactive recommendations",
            agent=self.agent
        )
    
    def _format_container_details(self, containers: List[Dict[str, Any]]) -> str:
        """Format container details for the task description"""
        if not containers:
            return "No containers running"
        
        details = []
        for container in containers[:10]:  # Limit to top 10 for context
            details.append(
                f"- {container.get('name', 'unknown')}: "
                f"CPU: {container.get('cpu_percent', 0):.1f}%, "
                f"Memory: {container.get('memory_percent', 0):.1f}%, "
                f"Status: {container.get('status', 'unknown')}"
            )
        
        if len(containers) > 10:
            details.append(f"... and {len(containers) - 10} more containers")
        
        return "\n".join(details)
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """Calculate trend direction and magnitude"""
        if len(values) < 2:
            return {"direction": "STABLE", "change": 0.0}
        
        first_val = values[0]
        last_val = values[-1]
        change = last_val - first_val
        
        if abs(change) < 5:
            direction = "STABLE"
        elif change > 0:
            direction = "INCREASING" if change > 10 else "SLIGHTLY_INCREASING"
        else:
            direction = "DECREASING" if change < -10 else "SLIGHTLY_DECREASING"
        
        return {
            "direction": direction,
            "change": abs(change),
            "start": first_val,
            "end": last_val
        }
