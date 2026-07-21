from typing import Dict, List, Optional, Set
from app.services.agent_base import AgentContext
import logging

logger = logging.getLogger(__name__)


class AgentDispatcher:
    """
    Agent Dispatcher - Routes artifacts to appropriate agents based on type and source
    
    Routing logic based on planning.md specifications:
    - message/slack -> Knowledge, Operations, Alignment, Customer Intelligence, Spec Agent
    - deal/hubspot -> Revenue Agent, Customer Intelligence
    - contact/hubspot -> Customer Intelligence
    - email/gmail -> Customer Intelligence, Knowledge Agent
    - ticket/linear-jira -> Operations Agent, Alignment Agent
    - commit/github -> Operations Agent, Alignment Agent
    - pull_request/github -> Operations Agent, Alignment Agent
    - transaction/stripe -> Finance Agent, Revenue Agent
    - meeting/zoom -> Knowledge Agent, Spec Agent
    - document/notion -> Knowledge Agent, Alignment Agent
    - document/google_drive -> Knowledge Agent, Alignment Agent
    - message/teams -> Knowledge, Operations, Alignment, Customer Intelligence
    - ticket/asana -> Operations Agent, Alignment Agent
    - invoice/quickbooks-xero -> Finance Agent
    - ticket/intercom-zendesk -> Customer Intelligence, Operations Agent
    """
    
    def __init__(self):
        # Define routing rules
        self.routing_rules = {
            # Slack messages
            ('message', 'slack'): ['knowledge', 'operations', 'alignment', 'customer_intelligence', 'spec'],
            
            # Gmail emails
            ('email', 'gmail'): ['customer_intelligence', 'knowledge'],
            
            # HubSpot deals and contacts
            ('deal', 'hubspot'): ['revenue', 'customer_intelligence'],
            ('contact', 'hubspot'): ['customer_intelligence'],
            
            # Linear/Jira tickets
            ('ticket', 'linear'): ['operations', 'alignment'],
            ('ticket', 'jira'): ['operations', 'alignment'],
            
            # GitHub commits and PRs
            ('commit', 'github'): ['operations', 'alignment'],
            ('pull_request', 'github'): ['operations', 'alignment'],
            ('review', 'github'): ['operations', 'alignment'],
            
            # Stripe transactions
            ('transaction', 'stripe'): ['finance', 'revenue'],
            
            # Zoom meetings
            ('meeting', 'zoom'): ['knowledge', 'spec'],
            ('call', 'zoom'): ['knowledge', 'spec'],
            
            # Notion documents
            ('document', 'notion'): ['knowledge', 'alignment'],
            
            # Google Drive documents
            ('document', 'google_drive'): ['knowledge', 'alignment'],
            
            # Teams messages
            ('message', 'teams'): ['knowledge', 'operations', 'alignment', 'customer_intelligence'],
            
            # Asana tickets
            ('ticket', 'asana'): ['operations', 'alignment'],
            
            # QuickBooks/Xero invoices
            ('invoice', 'quickbooks'): ['finance'],
            ('invoice', 'xero'): ['finance'],
            
            # Intercom/Zendesk support tickets
            ('ticket', 'intercom'): ['customer_intelligence', 'operations'],
            ('ticket', 'zendesk'): ['customer_intelligence', 'operations'],
            
            # Salesforce deals and contacts
            ('deal', 'salesforce'): ['revenue', 'customer_intelligence'],
            ('contact', 'salesforce'): ['customer_intelligence'],

            # MCP bridge (universal - routes to knowledge by default)
            ('message', 'mcp'): ['knowledge'],
            ('document', 'mcp'): ['knowledge', 'alignment'],

            # Zapier/Make bridge (source-specific routing determined by content)
            ('message', 'zapier'): ['knowledge'],
            ('email', 'zapier'): ['customer_intelligence', 'knowledge'],
            ('ticket', 'zapier'): ['operations', 'alignment'],
            ('deal', 'zapier'): ['revenue', 'customer_intelligence'],
            ('message', 'make'): ['knowledge'],
            ('email', 'make'): ['customer_intelligence', 'knowledge'],
            ('ticket', 'make'): ['operations', 'alignment'],

            # REST API custom connector
            ('message', 'rest_api'): ['knowledge'],
        }
        
        # Default agents for unknown artifact types
        self.default_agents = ['knowledge']
    
    def route_artifact(
        self,
        artifact_type: str,
        source_tool: str,
        content: Optional[str] = None
    ) -> List[str]:
        """
        Route an artifact to appropriate agents based on type and source
        
        Args:
            artifact_type: Type of artifact (message, email, ticket, deal, etc.)
            source_tool: Source tool (slack, gmail, hubspot, etc.)
            content: Optional content for additional routing logic
        
        Returns:
            List of agent names that should process this artifact
        """
        # Look up routing rule
        key = (artifact_type.lower(), source_tool.lower())
        agents = self.routing_rules.get(key)
        
        if agents:
            routed_agents = agents.copy()
            
            # Apply content-based routing for special cases
            if content:
                routed_agents = self._apply_content_routing(
                    routed_agents, 
                    artifact_type, 
                    source_tool, 
                    content
                )
            
            logger.info(f"Routed {artifact_type}/{source_tool} to agents: {routed_agents}")
            return routed_agents
        
        # No specific rule found, use default
        logger.warning(f"No routing rule for {artifact_type}/{source_tool}, using default agents")
        return self.default_agents.copy()
    
    def _apply_content_routing(
        self,
        base_agents: List[str],
        artifact_type: str,
        source_tool: str,
        content: str
    ) -> List[str]:
        """
        Apply content-based routing for special cases
        
        This adds or removes agents based on content analysis
        """
        content_lower = content.lower()
        agents = base_agents.copy()
        
        # Special routing for decision language in Slack/Teams
        if source_tool in ['slack', 'teams'] and artifact_type == 'message':
            decision_patterns = ['we should', 'let\'s', 'decided', 'agreed', 'the plan is']
            has_decision = any(pattern in content_lower for pattern in decision_patterns)
            
            if has_decision:
                # Ensure spec agent is included for decisions
                if 'spec' not in agents:
                    agents.append('spec')
                logger.debug("Added spec agent due to decision language")
        
        # Special routing for customer mentions
        customer_keywords = ['customer', 'client', 'account', 'churn', 'retention']
        has_customer = any(keyword in content_lower for keyword in customer_keywords)
        
        if has_customer and 'customer_intelligence' not in agents:
            agents.append('customer_intelligence')
            logger.debug("Added customer_intelligence agent due to customer mention")
        
        # Special routing for blocker language
        blocker_keywords = ['blocked', 'stuck', 'waiting', 'need approval', 'blocked by']
        has_blocker = any(keyword in content_lower for keyword in blocker_keywords)
        
        if has_blocker and 'operations' not in agents:
            agents.append('operations')
            logger.debug("Added operations agent due to blocker language")
        
        # Special routing for priority language
        priority_keywords = ['priority', 'important', 'focus', 'strategic', 'goal']
        has_priority = any(keyword in content_lower for keyword in priority_keywords)
        
        if has_priority and 'alignment' not in agents:
            agents.append('alignment')
            logger.debug("Added alignment agent due to priority language")
        
        return agents
    
    def get_all_routing_rules(self) -> Dict[str, List[str]]:
        """
        Get all routing rules for display/configuration
        """
        return {
            f"{artifact_type}/{source_tool}": agents
            for (artifact_type, source_tool), agents in self.routing_rules.items()
        }
    
    def add_routing_rule(
        self,
        artifact_type: str,
        source_tool: str,
        agents: List[str]
    ) -> None:
        """
        Add or update a routing rule
        
        Args:
            artifact_type: Type of artifact
            source_tool: Source tool
            agents: List of agent names to route to
        """
        key = (artifact_type.lower(), source_tool.lower())
        self.routing_rules[key] = agents
        logger.info(f"Added/updated routing rule: {artifact_type}/{source_tool} -> {agents}")
    
    def remove_routing_rule(self, artifact_type: str, source_tool: str) -> None:
        """
        Remove a routing rule
        
        Args:
            artifact_type: Type of artifact
            source_tool: Source tool
        """
        key = (artifact_type.lower(), source_tool.lower())
        if key in self.routing_rules:
            del self.routing_rules[key]
            logger.info(f"Removed routing rule: {artifact_type}/{source_tool}")
    
    def get_agents_for_source_tool(self, source_tool: str) -> Set[str]:
        """
        Get all unique agents that handle artifacts from a specific source tool
        
        Args:
            source_tool: Source tool name
        
        Returns:
            Set of agent names
        """
        agents = set()
        source_tool_lower = source_tool.lower()
        
        for (artifact_type, tool), agent_list in self.routing_rules.items():
            if tool == source_tool_lower:
                agents.update(agent_list)
        
        return agents
    
    def get_source_tools_for_agent(self, agent_name: str) -> Set[str]:
        """
        Get all source tools that route to a specific agent
        
        Args:
            agent_name: Name of the agent
        
        Returns:
            Set of source tool names
        """
        source_tools = set()
        agent_name_lower = agent_name.lower()
        
        for (artifact_type, tool), agent_list in self.routing_rules.items():
            if agent_name_lower in [a.lower() for a in agent_list]:
                source_tools.add(tool)
        
        return source_tools


# Global dispatcher instance
agent_dispatcher = AgentDispatcher()
