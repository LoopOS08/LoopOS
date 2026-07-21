from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class OperationsAgent(BaseAgent):
    """
    Operations Agent - Task coordination and workflow automation
    
    Role: Watches all active tasks and projects across Linear, Jira, Asana, Trello, Notion, and GitHub
    Goal Monitored: sprint_completion_rate — target set by company (e.g., 80%)
    """
    
    def __init__(self):
        super().__init__(
            name="operations",
            description="Task coordination and workflow automation agent",
            permissions=[
                "read_artifacts",
                "read_tasks",
                "update_status",
                "create_tickets",
                "post_slack"
            ]
        )
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve overdue tasks from Linear/Jira/Asana/Trello
        - Get Slack messages with blocker language
        - Get current sprint plan and completion rate
        - Load recent actions
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            # In production, this would call artifact_store_service.semantic_search with actual db
            overdue_artifacts = []
            blocker_artifacts = []
            sprint_artifacts = []
            
            # Search for overdue tasks from artifacts (placeholder)
            # overdue_artifacts = await artifact_store_service.semantic_search(...)
            
            # Search for blocker language in Slack (placeholder)
            # blocker_artifacts = await artifact_store_service.semantic_search(...)
            
            # Get current sprint-related artifacts (placeholder)
            # sprint_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = overdue_artifacts + blocker_artifacts + sprint_artifacts
            
            # Update context with retrieved artifacts
            context.relevant_artifacts = [
                {
                    'id': artifact.get('id'),
                    'content': artifact.get('content'),
                    'source_tool': artifact.get('source_tool'),
                    'artifact_type': artifact.get('artifact_type'),
                    'author': artifact.get('author'),
                    'created_at': artifact.get('created_at'),
                    'metadata': artifact.get('metadata', {})
                }
                for artifact in all_relevant
            ]
            
            # Add operations-specific context
            context.additional_context.update({
                'overdue_task_count': len(overdue_artifacts),
                'blocker_message_count': len(blocker_artifacts),
                'sprint_artifact_count': len(sprint_artifacts),
                'analysis_type': 'operations_monitoring'
            })
            
            logger.info(f"Operations Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Operations Agent context retrieval failed: {e}")
            # Return original context if retrieval fails
            return context
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Analyze overdue tasks and blockers
        - Determine if action is needed
        - Decide on action type
        """
        try:
            # Extract key information from context
            overdue_count = context.additional_context.get('overdue_task_count', 0)
            blocker_count = context.additional_context.get('blocker_message_count', 0)
            artifact_count = len(context.relevant_artifacts)
            
            # Get current goal state for sprint completion
            sprint_goal = None
            for goal in context.current_goal_state.get('goals', []):
                if goal.get('metric_name') == 'sprint_completion_rate':
                    sprint_goal = goal
                    break
            
            # Build reasoning prompt
            prompt = f"""
            You are the Operations Agent for LoopOS. Analyze the current operational state and determine if action is needed.
            
            Context:
            - Overdue tasks: {overdue_count}
            - Blocker messages detected: {blocker_count}
            - Relevant artifacts analyzed: {artifact_count}
            - Current sprint completion goal: {sprint_goal.get('current_value', 'unknown')}% target: {sprint_goal.get('target_value', 'unknown')}% if sprint_goal else 'Not set'
            
            Relevant artifacts:
            {json.dumps(context.relevant_artifacts[:5], indent=2)}
            
            Determine:
            1. Should action be taken? (true/false)
            2. What type of action? (alert_slack, update_status, generate_briefing, reassign_task, no_action)
            3. What is the reasoning?
            4. What is the specific output?
            5. Confidence level (0.0-1.0)
            6. Does this require human approval? (true for reassignments, false for alerts)
            
            Rules:
            - If overdue_count > 3: alert_slack with summary
            - If blocker_count > 5: alert_slack with blocker summary
            - If sprint completion < target: generate_briefing
            - Task reassignment always requires human approval
            - Simple status updates and alerts do not require approval
            """
            
            # TODO: Replace with actual LLM call
            # For now, using rule-based reasoning
            should_act = False
            action_type = "no_action"
            reasoning = "No immediate action required"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if overdue_count > 3:
                should_act = True
                action_type = "alert_slack"
                reasoning = f"Found {overdue_count} overdue tasks requiring attention"
                output = {
                    "message": f"Operations Alert: {overdue_count} tasks are overdue. Immediate attention required.",
                    "channel": "#engineering",
                    "overdue_tasks": [a for a in context.relevant_artifacts if a.get('artifact_type') == 'ticket'][:5]
                }
                confidence = 0.9
            elif blocker_count > 5:
                should_act = True
                action_type = "alert_slack"
                reasoning = f"Detected {blocker_count} blocker messages indicating workflow issues"
                output = {
                    "message": f"Operations Alert: {blocker_count} blocker messages detected. Team may be stuck.",
                    "channel": "#engineering",
                    "blocker_summary": [a for a in context.relevant_artifacts if 'block' in a.get('content', '').lower()][:5]
                }
                confidence = 0.85
            elif sprint_goal and sprint_goal.get('current_value', 0) < sprint_goal.get('target_value', 80):
                should_act = True
                action_type = "generate_briefing"
                reasoning = f"Sprint completion rate ({sprint_goal.get('current_value')}%) below target ({sprint_goal.get('target_value')}%)"
                output = {
                    "briefing_type": "sprint_status",
                    "current_rate": sprint_goal.get('current_value'),
                    "target_rate": sprint_goal.get('target_value'),
                    "gap": sprint_goal.get('target_value') - sprint_goal.get('current_value'),
                    "recommendations": ["Review sprint scope", "Identify bottlenecks", "Consider reprioritization"]
                }
                confidence = 0.9
            
            return AgentReasoning(
                should_act=should_act,
                action_type=action_type,
                reasoning=reasoning,
                output=output,
                confidence=confidence,
                requires_human_approval=requires_approval
            )
            
        except Exception as e:
            logger.error(f"Operations Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        """
        Phase 3: Action Execution
        - Execute the determined action
        - Queue for approval if required
        - Log action with full context
        """
        try:
            # Create action record
            action = AgentAction(
                agent_name=self.name,
                action_type=reasoning.action_type,
                context={
                    'company_id': context.company_id,
                    'relevant_artifacts': context.relevant_artifacts,
                    'current_goal_state': context.current_goal_state,
                    'additional_context': context.additional_context
                },
                reasoning=reasoning.reasoning,
                output=reasoning.output,
                artifact_ids=[a.get('id') for a in context.relevant_artifacts if a.get('id')],
                goal_id=context.additional_context.get('goal_id'),
                requires_human_approval=reasoning.requires_human_approval,
                confidence=reasoning.confidence
            )
            
            # If approval required, this will be queued in the approval system
            # If auto-execute, perform the action here
            if reasoning.should_act and not reasoning.requires_human_approval:
                await self._execute_action(action, reasoning)
            
            logger.info(f"Operations Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Operations Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action (integration-specific)
        """
        try:
            if reasoning.action_type == "alert_slack":
                # TODO: Integrate with Slack API
                logger.info(f"Would post to Slack: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "generate_briefing":
                # TODO: Generate and store briefing
                logger.info(f"Would generate briefing: {reasoning.output.get('briefing_type')}")
                
            elif reasoning.action_type == "update_status":
                # TODO: Update task status in Linear/Jira
                logger.info(f"Would update task status")
                
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            raise
    
    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        """
        Phase 4: Outcome Measurement
        - Compare goal metric before and after action
        - Record outcome
        """
        try:
            # TODO: Implement actual goal metric comparison
            # For now, return placeholder outcome
            return AgentOutcome(
                success=True,
                goal_metric_before=0.0,
                goal_metric_after=0.0,
                delta=0.0,
                human_feedback=None
            )
            
        except Exception as e:
            logger.error(f"Operations Agent outcome measurement failed: {e}")
            return AgentOutcome(
                success=False,
                goal_metric_before=0.0,
                goal_metric_after=0.0,
                delta=0.0,
                human_feedback=f"Measurement failed: {str(e)}"
            )
    
    async def phase5_learning(self, action: AgentAction, outcome: AgentOutcome) -> None:
        """
        Phase 5: Learning
        - Update agent intelligence based on outcome
        - Extract patterns from success/failure
        """
        try:
            # TODO: Implement learning logic
            # Update intelligence based on action outcome
            if outcome.success:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': True
                }
                self.update_intelligence({
                    'successful_patterns': [pattern],
                    'success_rate': 0.8  # Placeholder
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.6  # Placeholder
                })
            
            logger.info("Operations Agent learning completed")
            
        except Exception as e:
            logger.error(f"Operations Agent learning failed: {e}")
