from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class AlignmentAgent(BaseAgent):
    """
    Alignment Agent - Engineering-business alignment monitoring
    
    Role: Flags when engineering is building the wrong thing. Continuously compares stated priorities against actual work in progress.
    Goal Monitored: sprint_priority_alignment_pct — target set by company (e.g., >75%)
    """
    
    def __init__(self):
        super().__init__(
            name="alignment",
            description="Engineering-business alignment monitoring agent",
            permissions=[
                "read_artifacts",
                "compare_goals",
                "flag_drift",
                "post_slack"
            ]
        )
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Get OKR documents and roadmap from Notion/Drive
        - Get leadership priority statements from Slack/Teams
        - Get all current sprint tickets from Linear/Jira
        - Get GitHub commits and PRs (last 7 days)
        - Get previous alignment scores for trend
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            priority_artifacts = []
            leadership_artifacts = []
            sprint_artifacts = []
            github_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # priority_artifacts = await artifact_store_service.semantic_search(...)
            # leadership_artifacts = await artifact_store_service.semantic_search(...)
            # sprint_artifacts = await artifact_store_service.semantic_search(...)
            # github_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = priority_artifacts + leadership_artifacts + sprint_artifacts + github_artifacts
            
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
            
            # Add alignment-specific context
            context.additional_context.update({
                'priority_document_count': len(priority_artifacts),
                'leadership_statement_count': len(leadership_artifacts),
                'sprint_ticket_count': len(sprint_artifacts),
                'github_activity_count': len(github_artifacts),
                'analysis_type': 'alignment_monitoring'
            })
            
            logger.info(f"Alignment Agent retrieved {len(context.relevant_artifacts)} relevant artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Alignment Agent context retrieval failed: {e}")
            return context
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Compare what should be built vs what is being built
        - Classify tickets as aligned, misaligned, or unclear
        - Determine if action is needed
        """
        try:
            # Analyze alignment
            alignment_analysis = self._analyze_alignment(context.relevant_artifacts)
            
            aligned_count = alignment_analysis.get('aligned_count', 0)
            misaligned_count = alignment_analysis.get('misaligned_count', 0)
            unclear_count = alignment_analysis.get('unclear_count', 0)
            total_tickets = aligned_count + misaligned_count + unclear_count
            
            # Calculate alignment percentage
            alignment_pct = (aligned_count / total_tickets * 100) if total_tickets > 0 else 0
            
            # Get alignment goal
            alignment_goal = None
            for goal in context.current_goal_state.get('goals', []):
                if goal.get('metric_name') == 'sprint_priority_alignment_pct':
                    alignment_goal = goal
                    break
            
            target_alignment = alignment_goal.get('target_value', 75) if alignment_goal else 75
            
            should_act = False
            action_type = "no_action"
            reasoning = "Engineering alignment is acceptable"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if alignment_pct < target_alignment:
                should_act = True
                action_type = "alert_misalignment"
                reasoning = f"Sprint alignment ({alignment_pct:.1f}%) below target ({target_alignment}%)"
                output = {
                    "message": f"Alignment Alert: Sprint alignment at {alignment_pct:.1f}% vs target {target_alignment}%. {misaligned_count} tickets appear misaligned.",
                    "channel": "#engineering-leadership",
                    "alignment_score": alignment_pct,
                    "target_score": target_alignment,
                    "aligned_count": aligned_count,
                    "misaligned_count": misaligned_count,
                    "unclear_count": unclear_count,
                    "misaligned_tickets": alignment_analysis.get('misaligned_tickets', [])[:5]
                }
                confidence = 0.85
            elif misaligned_count > 2:
                should_act = True
                action_type = "flag_drift"
                reasoning = f"Detected {misaligned_count} potentially misaligned tickets"
                output = {
                    "message": f"Alignment Notice: {misaligned_count} tickets may not align with stated priorities.",
                    "channel": "#engineering",
                    "misaligned_tickets": alignment_analysis.get('misaligned_tickets', [])[:3]
                }
                confidence = 0.75
            else:
                should_act = True
                action_type = "status_report"
                reasoning = f"Generating alignment status report ({alignment_pct:.1f}% alignment)"
                output = {
                    "report_type": "alignment_status",
                    "alignment_score": alignment_pct,
                    "target_score": target_alignment,
                    "status": "on_track" if alignment_pct >= target_alignment else "at_risk",
                    "summary": alignment_analysis.get('summary', {})
                }
                confidence = 0.8
            
            return AgentReasoning(
                should_act=should_act,
                action_type=action_type,
                reasoning=reasoning,
                output=output,
                confidence=confidence,
                requires_human_approval=requires_approval
            )
            
        except Exception as e:
            logger.error(f"Alignment Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _analyze_alignment(self, artifacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze alignment between priorities and actual work
        """
        # Separate priorities and work items
        priority_artifacts = [a for a in artifacts if a.get('artifact_type') == 'document' or 
                            (a.get('artifact_type') == 'message' and 'priority' in a.get('content', '').lower())]
        work_artifacts = [a for a in artifacts if a.get('artifact_type') in ['ticket', 'commit', 'review']]
        
        # Extract priority keywords
        priority_keywords = []
        for artifact in priority_artifacts:
            content = artifact.get('content', '').lower()
            # Simple keyword extraction (would be more sophisticated with LLM)
            words = content.split()
            priority_keywords.extend([w for w in words if len(w) > 4])
        
        # Remove duplicates and common words
        common_words = {'this', 'that', 'with', 'from', 'have', 'will', 'should', 'could', 'would'}
        priority_keywords = list(set([w for w in priority_keywords if w not in common_words]))
        
        # Classify work items
        aligned_tickets = []
        misaligned_tickets = []
        unclear_tickets = []
        
        for artifact in work_artifacts:
            content = artifact.get('content', '').lower()
            metadata = artifact.get('metadata', {})
            
            # Check for alignment with priorities
            alignment_score = 0
            for keyword in priority_keywords:
                if keyword in content:
                    alignment_score += 1
            
            ticket_info = {
                'title': metadata.get('title') or content[:50],
                'source': artifact.get('source_tool'),
                'alignment_score': alignment_score,
                'content_preview': content[:100]
            }
            
            if alignment_score >= 2:
                aligned_tickets.append(ticket_info)
            elif alignment_score == 0:
                misaligned_tickets.append(ticket_info)
            else:
                unclear_tickets.append(ticket_info)
        
        return {
            'aligned_count': len(aligned_tickets),
            'misaligned_count': len(misaligned_tickets),
            'unclear_count': len(unclear_tickets),
            'aligned_tickets': aligned_tickets,
            'misaligned_tickets': misaligned_tickets,
            'unclear_tickets': unclear_tickets,
            'summary': {
                'total_analyzed': len(work_artifacts),
                'priority_keywords': priority_keywords[:10],
                'alignment_assessment': 'good' if len(aligned_tickets) > len(misaligned_tickets) else 'concerning'
            }
        }
    
    async def phase3_action_execution(self, reasoning: AgentReasoning, context: AgentContext) -> AgentAction:
        """
        Phase 3: Action Execution
        """
        try:
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
            
            if reasoning.should_act and not reasoning.requires_human_approval:
                await self._execute_action(action, reasoning)
            
            logger.info(f"Alignment Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Alignment Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action
        """
        try:
            if reasoning.action_type == "alert_misalignment":
                logger.info(f"Would post misalignment alert to Slack: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "flag_drift":
                logger.info(f"Would flag alignment drift: {reasoning.output.get('message')}")
                
            elif reasoning.action_type == "status_report":
                logger.info(f"Would generate alignment status report")
                
        except Exception as e:
            logger.error(f"Failed to execute action: {e}")
            raise
    
    async def phase4_outcome_measurement(self, action: AgentAction) -> AgentOutcome:
        """
        Phase 4: Outcome Measurement
        """
        try:
            return AgentOutcome(
                success=True,
                goal_metric_before=0.0,
                goal_metric_after=0.0,
                delta=0.0,
                human_feedback=None
            )
            
        except Exception as e:
            logger.error(f"Alignment Agent outcome measurement failed: {e}")
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
        """
        try:
            if outcome.success:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': True
                }
                self.update_intelligence({
                    'successful_patterns': [pattern],
                    'success_rate': 0.77
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.67
                })
            
            logger.info("Alignment Agent learning completed")
            
        except Exception as e:
            logger.error(f"Alignment Agent learning failed: {e}")
