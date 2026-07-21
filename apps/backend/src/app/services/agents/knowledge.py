from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json
import re

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """
    Knowledge Agent - Decision extraction and knowledge management
    
    Role: Makes the company's institutional knowledge queryable and alive. Captures decisions before they are lost.
    Goal Monitored: decision_capture_rate — target: >90% of decisions documented within 24 hours
    """
    
    def __init__(self):
        super().__init__(
            name="knowledge",
            description="Decision extraction and knowledge management agent",
            permissions=[
                "read_artifacts",
                "extract_decisions",
                "create_knowledge",
                "update_notion",
                "post_slack"
            ]
        )
        
        # Decision patterns to detect
        self.decision_patterns = [
            r'we should',
            r'let\'s go with',
            r'decided to',
            r'we\'ll',
            r'agreed to',
            r'the plan is',
            r'going with',
            r'confirmed',
            r'final decision',
            r'we have decided'
        ]
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Retrieve recent messages with decision patterns
        - Get meeting transcripts
        - Get new documents
        - Get existing decision log for deduplication
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            decision_messages = []
            meeting_artifacts = []
            document_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # decision_messages = await artifact_store_service.semantic_search(...)
            # meeting_artifacts = await artifact_store_service.semantic_search(...)
            # document_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = decision_messages + meeting_artifacts + document_artifacts
            
            # Filter for decision patterns
            decision_artifacts = self._filter_decision_artifacts(all_relevant)
            
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
                for artifact in decision_artifacts
            ]
            
            # Add knowledge-specific context
            context.additional_context.update({
                'decision_message_count': len(decision_messages),
                'meeting_count': len(meeting_artifacts),
                'document_count': len(document_artifacts),
                'total_decisions_detected': len(decision_artifacts),
                'analysis_type': 'decision_extraction'
            })
            
            logger.info(f"Knowledge Agent retrieved {len(context.relevant_artifacts)} decision artifacts")
            return context
            
        except Exception as e:
            logger.error(f"Knowledge Agent context retrieval failed: {e}")
            return context
    
    def _filter_decision_artifacts(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter artifacts for decision patterns
        """
        decision_artifacts = []
        
        for artifact in artifacts:
            content = artifact.get('content', '').lower()
            
            # Check if content contains decision patterns
            for pattern in self.decision_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    decision_artifacts.append(artifact)
                    break
        
        return decision_artifacts
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Extract decisions from artifacts
        - Check for duplicates
        - Determine if action is needed
        """
        try:
            # Extract decisions from artifacts
            decisions = self._extract_decisions(context.relevant_artifacts)
            
            decision_count = len(decisions)
            
            should_act = False
            action_type = "no_action"
            reasoning = "No decisions requiring documentation"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if decision_count > 0:
                should_act = True
                action_type = "document_decision"
                reasoning = f"Extracted {decision_count} decisions requiring documentation"
                output = {
                    "decisions": decisions,
                    "action": "create_decision_entries",
                    "total_decisions": decision_count
                }
                confidence = 0.85
                
                # Check if any decisions are significant enough for Notion documentation
                significant_decisions = [d for d in decisions if d.get('significance', 'low') == 'high']
                if significant_decisions:
                    action_type = "document_and_publish"
                    reasoning = f"Extracted {decision_count} decisions, {len(significant_decisions)} are significant"
                    output['significant_decisions'] = significant_decisions
                    output['create_notion_pages'] = True
            
            return AgentReasoning(
                should_act=should_act,
                action_type=action_type,
                reasoning=reasoning,
                output=output,
                confidence=confidence,
                requires_human_approval=requires_approval
            )
            
        except Exception as e:
            logger.error(f"Knowledge Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _extract_decisions(self, artifacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract decisions from artifacts
        """
        decisions = []
        
        for artifact in artifacts:
            content = artifact.get('content', '')
            author = artifact.get('author', 'Unknown')
            source = artifact.get('source_tool', 'unknown')
            created_at = artifact.get('created_at', '')
            
            # Extract decision using patterns
            for pattern in self.decision_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # Get context around the decision (100 chars before and after)
                    start = max(0, match.start() - 100)
                    end = min(len(content), match.end() + 100)
                    decision_context = content[start:end].strip()
                    
                    # Determine significance
                    significance = self._determine_significance(decision_context)
                    
                    decision = {
                        'content': decision_context,
                        'author': author,
                        'source': source,
                        'detected_at': created_at,
                        'artifact_id': artifact.get('id'),
                        'significance': significance,
                        'pattern_matched': pattern
                    }
                    
                    decisions.append(decision)
        
        return decisions
    
    def _determine_significance(self, decision_context: str) -> str:
        """
        Determine if a decision is high, medium, or low significance
        """
        high_significance_keywords = [
            'strategy', 'roadmap', 'pricing', 'funding', 'hiring', 'launch',
            'partnership', 'acquisition', 'pivot', 'architecture', 'policy'
        ]
        
        context_lower = decision_context.lower()
        
        for keyword in high_significance_keywords:
            if keyword in context_lower:
                return 'high'
        
        return 'medium' if len(decision_context) > 100 else 'low'
    
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
            
            logger.info(f"Knowledge Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Knowledge Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action
        """
        try:
            if reasoning.action_type == "document_decision":
                # TODO: Create decision entries in database
                decisions = reasoning.output.get('decisions', [])
                logger.info(f"Would create {len(decisions)} decision entries in database")
                
            elif reasoning.action_type == "document_and_publish":
                # TODO: Create decision entries and Notion pages
                decisions = reasoning.output.get('decisions', [])
                significant = reasoning.output.get('significant_decisions', [])
                logger.info(f"Would create {len(decisions)} decision entries and {len(significant)} Notion pages")
                
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
            logger.error(f"Knowledge Agent outcome measurement failed: {e}")
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
                    'success_rate': 0.82
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.72
                })
            
            logger.info("Knowledge Agent learning completed")
            
        except Exception as e:
            logger.error(f"Knowledge Agent learning failed: {e}")
