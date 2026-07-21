from typing import Dict, Any, List, Optional
from app.services.agent_base import BaseAgent, AgentContext, AgentReasoning, AgentAction, AgentOutcome
import logging
import json

logger = logging.getLogger(__name__)


class SpecAgent(BaseAgent):
    """
    Spec Agent - Decision-to-specification generation
    
    Role: Closes the gap between 'we decided to do X' and 'here is exactly what X means, ready to build.'
    Goal Monitored: decision_to_spec_conversion_rate — target: >80% of engineering decisions have a spec within 24 hours
    """
    
    def __init__(self):
        super().__init__(
            name="spec",
            description="Decision-to-specification generation agent",
            permissions=[
                "read_artifacts",
                "create_tickets",
                "update_requirements",
                "create_notion",
                "post_slack"
            ]
        )
    
    async def phase1_context_retrieval(self, context: AgentContext) -> AgentContext:
        """
        Phase 1: Context Retrieval
        - Get unspecced decisions (last 24 hours)
        - Get related code repositories from GitHub
        - Get existing specs for deduplication
        - Get codebase architecture from Notion
        - Get team member expertise signals
        """
        try:
            company_id = context.company_id
            
            # For now, use placeholder data since semantic_search needs db session
            decision_artifacts = []
            spec_artifacts = []
            github_artifacts = []
            
            # In production, these would call artifact_store_service.semantic_search with actual db
            # decision_artifacts = await artifact_store_service.semantic_search(...)
            # spec_artifacts = await artifact_store_service.semantic_search(...)
            # github_artifacts = await artifact_store_service.semantic_search(...)
            
            # Combine all relevant artifacts
            all_relevant = decision_artifacts + spec_artifacts + github_artifacts
            
            # Filter for decisions that need specs
            unspecced_decisions = self._filter_unspecced_decisions(all_relevant, spec_artifacts)
            
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
                for artifact in unspecced_decisions
            ]
            
            # Add spec-specific context
            context.additional_context.update({
                'decision_count': len(decision_artifacts),
                'existing_spec_count': len(spec_artifacts),
                'github_artifact_count': len(github_artifacts),
                'unspecced_decision_count': len(unspecced_decisions),
                'analysis_type': 'spec_generation'
            })
            
            logger.info(f"Spec Agent retrieved {len(context.relevant_artifacts)} unspecced decisions")
            return context
            
        except Exception as e:
            logger.error(f"Spec Agent context retrieval failed: {e}")
            return context
    
    def _filter_unspecced_decisions(self, artifacts: List[Dict[str, Any]], existing_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter decisions that don't have specs yet
        """
        unspecced = []
        
        # Create a set of spec titles for quick lookup
        spec_titles = set()
        for spec in existing_specs:
            content = spec.get('content', '').lower()
            spec_titles.add(content[:50])  # Simple deduplication
        
        for artifact in artifacts:
            if artifact.get('artifact_type') not in ['message', 'document']:
                continue
                
            content = artifact.get('content', '').lower()
            
            # Check if this appears to be a decision
            decision_keywords = ['decided', 'should', 'let\'s', 'agreed', 'plan', 'going to']
            is_decision = any(keyword in content for keyword in decision_keywords)
            
            if is_decision:
                # Check if spec already exists
                content_prefix = content[:50]
                if content_prefix not in spec_titles:
                    unspecced.append(artifact)
        
        return unspecced
    
    async def phase2_reasoning(self, context: AgentContext) -> AgentReasoning:
        """
        Phase 2: Reasoning
        - Analyze unspecced decisions
        - Generate specs for decisions
        - Determine if action is needed
        """
        try:
            unspecced_count = context.additional_context.get('unspecced_decision_count', 0)
            
            should_act = False
            action_type = "no_action"
            reasoning = "No decisions requiring specs"
            output = {}
            confidence = 0.8
            requires_approval = False
            
            if unspecced_count > 0:
                # Generate specs for unspecced decisions
                specs = self._generate_specs(context.relevant_artifacts)
                
                if specs:
                    should_act = True
                    action_type = "create_spec"
                    reasoning = f"Generated {len(specs)} specs for unspecced decisions"
                    output = {
                        "specs": specs,
                        "action": "create_tickets_and_specs",
                        "total_specs": len(specs)
                    }
                    confidence = 0.85
                    
                    # Check if any specs are XL (require approval)
                    xl_specs = [s for s in specs if s.get('estimated_effort') == 'XL']
                    if xl_specs:
                        requires_approval = True
                        reasoning = f"Generated {len(specs)} specs, {len(xl_specs)} are XL and require approval"
                        output['requires_approval'] = True
                        output['xl_specs'] = xl_specs
            
            return AgentReasoning(
                should_act=should_act,
                action_type=action_type,
                reasoning=reasoning,
                output=output,
                confidence=confidence,
                requires_human_approval=requires_approval
            )
            
        except Exception as e:
            logger.error(f"Spec Agent reasoning failed: {e}")
            return AgentReasoning(
                should_act=False,
                action_type="no_action",
                reasoning=f"Reasoning failed due to error: {str(e)}",
                output={},
                confidence=0.0,
                requires_human_approval=False
            )
    
    def _generate_specs(self, decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate specs from decisions
        """
        specs = []
        
        for decision in decisions:
            content = decision.get('content', '')
            author = decision.get('author', 'Unknown')
            source = decision.get('source_tool', 'unknown')
            
            # Generate spec from decision
            spec = self._create_spec_from_decision(content, author, source)
            if spec:
                specs.append(spec)
        
        return specs
    
    def _create_spec_from_decision(self, decision_content: str, author: str, source: str) -> Optional[Dict[str, Any]]:
        """
        Create a spec from a decision
        """
        try:
            # Extract key information from decision
            content_lower = decision_content.lower()
            
            # Determine title (imperative form)
            title = self._extract_title(decision_content)
            
            # Determine context
            context = f"Decision made by {author} in {source}: {decision_content[:200]}"
            
            # Generate acceptance criteria
            acceptance_criteria = self._generate_acceptance_criteria(decision_content)
            
            # Estimate effort
            effort = self._estimate_effort(decision_content)
            
            # Suggest assignee based on content
            suggested_assignee = self._suggest_assignee(decision_content, author)
            
            # Determine priority
            priority = self._determine_priority(decision_content)
            
            return {
                'title': title,
                'context': context,
                'acceptance_criteria': acceptance_criteria,
                'dependencies': [],
                'estimated_effort': effort,
                'suggested_assignee': suggested_assignee,
                'priority': priority,
                'source_decision': decision_content[:500],
                'author': author
            }
            
        except Exception as e:
            logger.error(f"Failed to create spec from decision: {e}")
            return None
    
    def _extract_title(self, content: str) -> str:
        """
        Extract imperative title from decision
        """
        # Simple extraction - take first meaningful phrase
        words = content.split()
        if len(words) > 10:
            return ' '.join(words[:10]).capitalize()
        return content[:50].capitalize()
    
    def _generate_acceptance_criteria(self, content: str) -> List[str]:
        """
        Generate acceptance criteria from decision
        """
        # Generate generic acceptance criteria
        criteria = [
            "Implementation meets the requirements specified in the decision",
            "Code is reviewed and approved by at least one team member",
            "Tests are written and passing for the new functionality",
            "Documentation is updated if necessary"
        ]
        
        # Add specific criteria based on content
        content_lower = content.lower()
        if 'api' in content_lower:
            criteria.append("API endpoints are documented and tested")
        if 'ui' in content_lower or 'interface' in content_lower:
            criteria.append("UI/UX is reviewed and approved")
        if 'database' in content_lower or 'data' in content_lower:
            criteria.append("Data migration is considered and executed if needed")
        
        return criteria[:5]  # Limit to 5 criteria
    
    def _estimate_effort(self, content: str) -> str:
        """
        Estimate effort based on content complexity
        """
        content_lower = content.lower()
        
        # Complexity indicators
        xl_indicators = ['rewrite', 'architecture', 'migration', 'infrastructure', 'platform']
        l_indicators = ['feature', 'integration', 'system', 'module']
        m_indicators = ['update', 'improve', 'enhance', 'fix']
        s_indicators = ['small', 'minor', 'simple', 'quick']
        
        for indicator in xl_indicators:
            if indicator in content_lower:
                return 'XL'
        
        for indicator in l_indicators:
            if indicator in content_lower:
                return 'L'
        
        for indicator in m_indicators:
            if indicator in content_lower:
                return 'M'
        
        for indicator in s_indicators:
            if indicator in content_lower:
                return 'S'
        
        return 'M'  # Default to medium
    
    def _suggest_assignee(self, content: str, author: str) -> str:
        """
        Suggest assignee based on content and author
        """
        # Simple logic - suggest the author or leave as TBD
        content_lower = content.lower()
        
        if 'backend' in content_lower or 'api' in content_lower:
            return 'Backend Team'
        elif 'frontend' in content_lower or 'ui' in content_lower:
            return 'Frontend Team'
        elif 'design' in content_lower:
            return 'Design Team'
        else:
            return author  # Default to decision author
    
    def _determine_priority(self, content: str) -> str:
        """
        Determine priority based on content
        """
        content_lower = content.lower()
        
        high_priority = ['urgent', 'critical', 'important', 'priority', 'asap']
        low_priority = ['later', 'eventually', 'nice to have', 'maybe']
        
        for indicator in high_priority:
            if indicator in content_lower:
                return 'high'
        
        for indicator in low_priority:
            if indicator in content_lower:
                return 'low'
        
        return 'medium'  # Default to medium
    
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
            
            logger.info(f"Spec Agent executed action: {reasoning.action_type}")
            return action
            
        except Exception as e:
            logger.error(f"Spec Agent action execution failed: {e}")
            raise
    
    async def _execute_action(self, action: AgentAction, reasoning: AgentReasoning) -> None:
        """
        Execute the actual action
        """
        try:
            if reasoning.action_type == "create_spec":
                specs = reasoning.output.get('specs', [])
                logger.info(f"Would create {len(specs)} specs and corresponding tickets")
                
                # TODO: Create spec entries in database
                # TODO: Create Linear/Jira tickets for each spec
                # TODO: Create Notion pages for specs
                
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
            logger.error(f"Spec Agent outcome measurement failed: {e}")
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
                    'success_rate': 0.83
                })
            else:
                pattern = {
                    'action_type': action.action_type,
                    'context_clues': action.context.get('additional_context', {}),
                    'successful': False
                }
                self.update_intelligence({
                    'failed_patterns': [pattern],
                    'success_rate': 0.73
                })
            
            logger.info("Spec Agent learning completed")
            
        except Exception as e:
            logger.error(f"Spec Agent learning failed: {e}")
