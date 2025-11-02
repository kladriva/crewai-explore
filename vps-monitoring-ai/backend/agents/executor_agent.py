"""
Executor Agent - Plans and executes automated remediation actions
Ensures safe execution with dry-run and rollback capabilities
"""
from crewai import Agent, Task
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any
from loguru import logger

from backend.config.settings import settings


class ExecutorAgent:
    """Agent responsible for planning and executing remediation actions"""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.2,  # Lower temperature for more deterministic actions
            api_key=settings.openai_api_key
        )
        
        self.agent = Agent(
            role="Action Executor & Remediation Specialist",
            goal="Plan and safely execute automated remediation actions to resolve system issues, "
                 "following safety protocols and ensuring minimal impact on running services",
            backstory="You are a seasoned Site Reliability Engineer (SRE) with 20 years of experience "
                     "in production systems. You have managed incidents at scale and understand the "
                     "importance of careful, measured actions. You always consider the impact of actions "
                     "before executing them. You follow the principle: 'First, do no harm.' "
                     "You document every action for audit trails and compliance.",
            verbose=True,
            allow_delegation=False,
            llm=self.llm
        )
    
    def create_action_planning_task(
        self, 
        analysis: str, 
        current_actions_count: int,
        node_info: Dict[str, Any]
    ) -> Task:
        """
        Create a task to plan remediation actions
        
        Args:
            analysis: Analysis report from AnalyzerAgent
            current_actions_count: Number of actions taken in current hour
            node_info: Information about the target node
        
        Returns:
            Task object for action planning
        """
        actions_remaining = settings.max_actions_per_hour - current_actions_count
        
        description = f"""
        Plan remediation actions based on the following analysis.
        
        ## Analysis Report:
        {analysis}
        
        ## Target Node Information:
        - Node: {node_info.get('name', 'Unknown')}
        - IP: {node_info.get('ip_address', 'Unknown')}
        - OS: {node_info.get('os_type', 'Unknown')}
        
        ## Safety Constraints:
        - Actions taken this hour: {current_actions_count}/{settings.max_actions_per_hour}
        - Remaining action budget: {actions_remaining}
        - Auto-restart enabled: {settings.enable_auto_restart}
        - Cache clear enabled: {settings.enable_cache_clear}
        - Disk cleanup enabled: {settings.enable_disk_cleanup}
        
        ## Available Actions:
        1. **RESTART_CONTAINER**: Restart a specific container
        2. **STOP_CONTAINER**: Stop a misbehaving container
        3. **START_CONTAINER**: Start a stopped container
        4. **CLEAR_CACHE**: Clear application cache to free memory
        5. **DISK_CLEANUP**: Remove old logs and temporary files
        
        ## Action Planning Guidelines:
        - Start with least invasive actions (clear cache, disk cleanup)
        - Use container restart only when necessary
        - Never restart critical infrastructure containers without explicit approval
        - Always provide clear reasoning for each action
        - Consider dependencies (e.g., database before app servers)
        - If action budget exhausted, recommend manual intervention
        
        ## Your Task:
        Create an action plan with:
        1. **Priority**: HIGH/MEDIUM/LOW
        2. **Action Sequence**: Ordered list of actions to take
        3. **For Each Action**:
           - Action Type
           - Target (container ID/name or system)
           - Reasoning (why this action is needed)
           - Expected Outcome
           - Risks (what could go wrong)
        4. **Rollback Plan**: How to undo if something fails
        5. **Success Criteria**: How to verify actions worked
        
        If no action is needed or budget exhausted, clearly state "NO_ACTION_REQUIRED" with reasoning.
        """
        
        return Task(
            description=description,
            expected_output="Structured action plan with priority, sequence, reasoning, risks, "
                          "rollback plan, and success criteria",
            agent=self.agent
        )
    
    def create_execution_validation_task(
        self, 
        action_plan: str,
        dry_run_results: Dict[str, Any]
    ) -> Task:
        """
        Create a task to validate action execution results
        
        Args:
            action_plan: The original action plan
            dry_run_results: Results from dry-run execution
        
        Returns:
            Task object for validation
        """
        description = f"""
        Validate the execution plan before proceeding with real actions.
        
        ## Original Action Plan:
        {action_plan}
        
        ## Dry-Run Results:
        {self._format_dry_run_results(dry_run_results)}
        
        ## Your Task:
        1. Review if dry-run results indicate the actions will succeed
        2. Identify any unexpected outcomes from dry-run
        3. Assess if it's safe to proceed with actual execution
        4. Recommend modifications if needed
        5. Make final GO/NO-GO decision
        
        Provide your decision in this format:
        - Decision: [GO/NO_GO/MODIFY]
        - Confidence: [HIGH/MEDIUM/LOW]
        - Reasoning: [Clear explanation]
        - Modifications: [If MODIFY, what changes are needed]
        - Risks: [Remaining risks even if proceeding]
        """
        
        return Task(
            description=description,
            expected_output="Validation decision with confidence, reasoning, and any modifications",
            agent=self.agent
        )
    
    def create_post_action_analysis_task(
        self, 
        executed_actions: List[Dict[str, Any]],
        before_metrics: Dict[str, Any],
        after_metrics: Dict[str, Any]
    ) -> Task:
        """
        Create a task to analyze results after actions are executed
        
        Args:
            executed_actions: List of actions that were executed
            before_metrics: System metrics before actions
            after_metrics: System metrics after actions
        
        Returns:
            Task object for post-action analysis
        """
        description = f"""
        Analyze the impact of executed actions and determine success.
        
        ## Actions Executed:
        {self._format_executed_actions(executed_actions)}
        
        ## Metrics Comparison:
        ### Before Actions:
        - CPU: {before_metrics.get('cpu_percent', 0):.1f}%
        - Memory: {before_metrics.get('memory_percent', 0):.1f}%
        - Disk: {before_metrics.get('disk_percent', 0):.1f}%
        
        ### After Actions:
        - CPU: {after_metrics.get('cpu_percent', 0):.1f}%
        - Memory: {after_metrics.get('memory_percent', 0):.1f}%
        - Disk: {after_metrics.get('disk_percent', 0):.1f}%
        
        ### Change:
        - CPU: {after_metrics.get('cpu_percent', 0) - before_metrics.get('cpu_percent', 0):+.1f}%
        - Memory: {after_metrics.get('memory_percent', 0) - before_metrics.get('memory_percent', 0):+.1f}%
        - Disk: {after_metrics.get('disk_percent', 0) - before_metrics.get('disk_percent', 0):+.1f}%
        
        ## Your Task:
        1. Assess if actions achieved desired outcomes
        2. Determine if system health improved
        3. Identify any unexpected side effects
        4. Recommend if further actions are needed
        5. Document lessons learned for future incidents
        
        Provide assessment in this format:
        - Overall Success: [SUCCESS/PARTIAL/FAILURE]
        - Goals Achieved: [List what was accomplished]
        - Remaining Issues: [What still needs attention]
        - Side Effects: [Any unexpected outcomes]
        - Next Steps: [What to do next]
        - Lessons Learned: [For future reference]
        """
        
        return Task(
            description=description,
            expected_output="Post-action analysis with success assessment, remaining issues, "
                          "side effects, next steps, and lessons learned",
            agent=self.agent
        )
    
    def _format_dry_run_results(self, results: Dict[str, Any]) -> str:
        """Format dry-run results for task description"""
        if not results:
            return "No dry-run performed"
        
        formatted = []
        for action_id, result in results.items():
            formatted.append(
                f"- {action_id}: {result.get('status', 'unknown')} - "
                f"{result.get('message', 'No message')}"
            )
        return "\n".join(formatted)
    
    def _format_executed_actions(self, actions: List[Dict[str, Any]]) -> str:
        """Format executed actions for task description"""
        if not actions:
            return "No actions executed"
        
        formatted = []
        for action in actions:
            formatted.append(
                f"- {action.get('action_type', 'unknown')}: "
                f"Target: {action.get('target', 'unknown')}, "
                f"Status: {action.get('status', 'unknown')}, "
                f"Duration: {action.get('execution_time', 0):.2f}s"
            )
        return "\n".join(formatted)
