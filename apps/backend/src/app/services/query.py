from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.models.artifact import SourceTool, ArtifactType
from app.services.artifact_store import artifact_store_service
from app.services.embeddings import embedding_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class QueryResult:
    """Result from a unified query with source attribution"""
    
    def __init__(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        confidence: float,
        caveats: List[str] = None
    ):
        self.answer = answer
        self.sources = sources
        self.confidence = confidence
        self.caveats = caveats or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            'answer': self.answer,
            'sources': self.sources,
            'confidence': self.confidence,
            'caveats': self.caveats
        }


class QueryService:
    """
    Unified Query Interface for cross-platform semantic search
    Enables questions like "What did we decide about pricing last week?"
    to be answered across all connected tools
    """
    
    def __init__(self):
        self.artifact_store = artifact_store_service
        self.embedding_service = embedding_service
    
    async def query(
        self,
        db: AsyncSession,
        company_id: str,
        question: str,
        limit: int = 15,
        threshold: float = 0.7,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None,
        date_range: Optional[tuple] = None
    ) -> QueryResult:
        """
        Execute a unified query across all connected tools
        
        Args:
            db: Database session
            company_id: Company to query
            question: Natural language question
            limit: Maximum number of artifacts to retrieve
            threshold: Similarity threshold (0.0-1.0)
            source_tool: Optional filter by source tool
            artifact_type: Optional filter by artifact type
            date_range: Optional (start_date, end_date) tuple
        
        Returns:
            QueryResult with answer, sources, confidence, and caveats
        """
        try:
            # Step 1: Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(question)
            
            # Step 2: Perform semantic search
            artifacts_with_similarity = await self.artifact_store.search_similar_artifacts(
                db=db,
                company_id=company_id,
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold,
                source_tool=source_tool,
                artifact_type=artifact_type
            )
            
            if not artifacts_with_similarity:
                return QueryResult(
                    answer="I couldn't find any relevant information in your connected tools.",
                    sources=[],
                    confidence=0.0,
                    caveats=["No matching artifacts found"]
                )
            
            # Step 3: Assemble context from top results
            context = self._assemble_context(artifacts_with_similarity)
            
            # Step 4: Get connected tools for caveats
            connected_tools = await self._get_connected_tools(db, company_id)
            
            # Step 5: Generate answer using LLM
            answer = await self._generate_answer(question, context)
            
            # Step 6: Format sources
            sources = self._format_sources(artifacts_with_similarity)
            
            # Step 7: Calculate confidence
            confidence = self._calculate_confidence(artifacts_with_similarity)
            
            # Step 8: Generate caveats
            caveats = self._generate_caveats(connected_tools, artifacts_with_similarity)
            
            return QueryResult(
                answer=answer,
                sources=sources,
                confidence=confidence,
                caveats=caveats
            )
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            return QueryResult(
                answer="I encountered an error while processing your query.",
                sources=[],
                confidence=0.0,
                caveats=["Error processing query"]
            )
    
    def _assemble_context(
        self,
        artifacts_with_similarity: List[tuple]
    ) -> str:
        """
        Assemble context from artifacts for LLM reasoning
        """
        context_parts = []
        
        for artifact, similarity in artifacts_with_similarity:
            source_tool = artifact.source_tool.value
            artifact_type = artifact.artifact_type.value
            author = artifact.author
            content = artifact.content
            source_date = artifact.source_created_at.strftime('%Y-%m-%d')
            
            context_part = (
                f"[Source: {source_tool} | Type: {artifact_type} | "
                f"Author: {author} | Date: {source_date} | "
                f"Relevance: {similarity:.2f}]\n"
                f"{content}\n"
            )
            
            context_parts.append(context_part)
        
        return '\n---\n'.join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        if not context or context.strip() == "":
            return "I couldn't find any relevant information to answer your question."

        system_prompt = (
            "You are LoopOS, a connective intelligence layer for company operations. "
            "Answer the user's question using ONLY the provided context from their connected tools. "
            "Each context block is tagged with [Source: tool | Type: type | Author: name | Date: date | Relevance: score]. "
            "Cite specific sources in your answer. If the context doesn't contain enough information, "
            "say so clearly. Do not make up information. "
            "Format your answer in a clear, readable way with bullet points where appropriate."
        )

        user_prompt = f"Question: {question}\n\nContext from connected tools:\n{context}"

        try:
            if settings.OPENAI_API_KEY:
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                response = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1024
                )
                return response.choices[0].message.content
            else:
                return f"Based on the information in your connected tools:\n\n{context}"
        except Exception as e:
            logger.error(f"LLM answer generation failed: {e}")
            return f"Based on the information in your connected tools:\n\n{context}"
    
    def _format_sources(
        self,
        artifacts_with_similarity: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Format sources for the response
        """
        sources = []
        
        for artifact, similarity in artifacts_with_similarity:
            source = {
                'tool': artifact.source_tool.value,
                'type': artifact.artifact_type.value,
                'author': artifact.author,
                'date': artifact.source_created_at.strftime('%Y-%m-%d %H:%M'),
                'preview': artifact.content[:200] + '...' if len(artifact.content) > 200 else artifact.content,
                'similarity': round(similarity, 3),
                'metadata': artifact.artifact_metadata
            }
            
            sources.append(source)
        
        return sources
    
    def _calculate_confidence(
        self,
        artifacts_with_similarity: List[tuple]
    ) -> float:
        """
        Calculate overall confidence based on similarity scores
        """
        if not artifacts_with_similarity:
            return 0.0
        
        # Average similarity of top 5 results
        top_results = artifacts_with_similarity[:5]
        similarities = [sim for _, sim in top_results]
        
        if not similarities:
            return 0.0
        
        avg_similarity = sum(similarities) / len(similarities)
        
        # Scale to 0-1 range (assuming typical similarities are 0.5-1.0)
        confidence = max(0.0, min(1.0, avg_similarity))
        
        return round(confidence, 2)
    
    def _generate_caveats(
        self,
        connected_tools: List[SourceTool],
        artifacts_with_similarity: List[tuple]
    ) -> List[str]:
        """
        Generate caveats about the query results
        """
        caveats = []
        
        # Check if we have results from limited tools
        represented_tools = set()
        for artifact, _ in artifacts_with_similarity:
            represented_tools.add(artifact.source_tool)
        
        missing_tools = set(connected_tools) - represented_tools
        
        if missing_tools:
            missing_tool_names = [tool.value for tool in missing_tools]
            caveats.append(f"Results limited to: {', '.join([tool.value for tool in represented_tools])}")
            caveats.append(f"Connected tools not included: {', '.join(missing_tool_names)}")
        
        # Check if results are old
        if artifacts_with_similarity:
            most_recent = max([artifact.source_created_at for artifact, _ in artifacts_with_similarity])
            days_old = (datetime.now() - most_recent).days
            
            if days_old > 30:
                caveats.append(f"Most recent result is {days_old} days old")
        
        # Check if we have few results
        if len(artifacts_with_similarity) < 3:
            caveats.append("Limited number of results - may not represent full context")
        
        return caveats
    
    async def _get_connected_tools(
        self,
        db: AsyncSession,
        company_id: str
    ) -> List[SourceTool]:
        """
        Get list of connected tools for a company
        """
        # In production, this would query the integrations table
        # For now, return all available tools
        return [
            SourceTool.SLACK,
            SourceTool.GMAIL,
            SourceTool.GITHUB,
            SourceTool.LINEAR,
            SourceTool.HUBSPOT,
            SourceTool.NOTION
        ]
    
    async def search_artifacts(
        self,
        db: AsyncSession,
        company_id: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[Dict[str, Any]]:
        """
        Simple semantic search returning artifacts directly
        Useful for UI components that need raw artifact data
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform semantic search
            artifacts_with_similarity = await self.artifact_store.search_similar_artifacts(
                db=db,
                company_id=company_id,
                query_embedding=query_embedding,
                limit=limit,
                threshold=threshold,
                source_tool=source_tool,
                artifact_type=artifact_type
            )
            
            # Format results
            results = []
            for artifact, similarity in artifacts_with_similarity:
                result = {
                    'id': artifact.id,
                    'tool': artifact.source_tool.value,
                    'type': artifact.artifact_type.value,
                    'content': artifact.content,
                    'author': artifact.author,
                    'author_email': artifact.author_email,
                    'date': artifact.source_created_at.isoformat(),
                    'similarity': round(similarity, 3),
                    'metadata': artifact.artifact_metadata
                }
                
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Artifact search failed: {e}")
            return []
    
    async def get_answer_suggestions(
        self,
        db: AsyncSession,
        company_id: str,
        partial_query: str,
        limit: int = 5
    ) -> List[str]:
        """
        Get query suggestions based on partial input
        Returns common questions or similar past queries
        """
        # In production, this would use a suggestion system
        # For now, return common query templates
        
        common_queries = [
            "What did we decide about pricing last week?",
            "Which customers are at risk this month?",
            "What are the top priorities for engineering?",
            "Show me recent decisions about product roadmap",
            "What's the status of the current sprint?",
            "Find all discussions about authentication",
            "What are our goals for this quarter?",
            "Show me customer feedback from last month",
            "What meetings did we have about the new feature?",
            "Find all mentions of budget or spending"
        ]
        
        # Filter by partial query
        if partial_query:
            suggestions = [
                q for q in common_queries
                if partial_query.lower() in q.lower()
            ]
        else:
            suggestions = common_queries[:limit]
        
        return suggestions[:limit]


# Global query service instance
query_service = QueryService()
