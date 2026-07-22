from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional, Dict, Any
from app.models.artifact import Artifact, SourceTool, ArtifactType
from app.services.embeddings import embedding_service
import logging

logger = logging.getLogger(__name__)


class ArtifactStoreService:
    """Service for storing and retrieving artifacts with pgvector integration"""
    
    def __init__(self):
        self.embedding_service = embedding_service
    
    async def create_artifact(
        self,
        db: AsyncSession,
        company_id: str,
        source_tool: SourceTool,
        artifact_type: ArtifactType,
        external_id: str,
        content: str,
        author: str,
        author_email: str,
        source_created_at,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Artifact:
        """
        Create a new artifact with embedding
        """
        try:
            # Generate embedding for the artifact
            enhanced_metadata = metadata or {}
            enhanced_metadata.update({
                'source_tool': source_tool.value,
                'artifact_type': artifact_type.value,
                'author': author
            })
            
            embedding = await self.embedding_service.generate_artifact_embedding(
                content, enhanced_metadata
            )
            
            # Create artifact
            artifact = Artifact(
                company_id=company_id,
                source_tool=source_tool,
                artifact_type=artifact_type,
                external_id=external_id,
                content=content,
                author=author,
                author_email=author_email,
                source_created_at=source_created_at,
                artifact_metadata=metadata or {},
                embedding=embedding
            )
            
            db.add(artifact)
            await db.commit()
            await db.refresh(artifact)
            
            logger.info(f"Created artifact {artifact.id} with embedding")
            return artifact
            
        except Exception as e:
            logger.error(f"Failed to create artifact: {e}")
            await db.rollback()
            raise Exception(f"Artifact creation failed: {e}")
    
    async def get_artifact_by_external_id(
        self,
        db: AsyncSession,
        company_id: str,
        source_tool: SourceTool,
        external_id: str
    ) -> Optional[Artifact]:
        """
        Get artifact by external ID (for deduplication)
        """
        result = await db.execute(
            select(Artifact).where(
                Artifact.company_id == company_id,
                Artifact.source_tool == source_tool,
                Artifact.external_id == external_id
            )
        )
        return result.scalar_one_or_none()
    
    async def update_artifact(
        self,
        db: AsyncSession,
        artifact: Artifact,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Artifact:
        """
        Update existing artifact and regenerate embedding if content changed
        """
        try:
            if content:
                artifact.content = content
                # Regenerate embedding
                enhanced_metadata = metadata or artifact.artifact_metadata
                enhanced_metadata.update({
                    'source_tool': artifact.source_tool.value,
                    'artifact_type': artifact.artifact_type.value,
                    'author': artifact.author
                })
                artifact.embedding = await self.embedding_service.generate_artifact_embedding(
                    content, enhanced_metadata
                )
            
            if metadata:
                artifact.artifact_metadata = metadata
            
            await db.commit()
            await db.refresh(artifact)
            
            logger.info(f"Updated artifact {artifact.id}")
            return artifact
            
        except Exception as e:
            logger.error(f"Failed to update artifact: {e}")
            await db.rollback()
            raise Exception(f"Artifact update failed: {e}")
    
    async def search_similar_artifacts(
        self,
        db: AsyncSession,
        company_id: str,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[tuple[Artifact, float]]:
        """
        Search for similar artifacts using pgvector cosine similarity
        """
        try:
            # Convert embedding to PostgreSQL array format
            embedding_array = f"[{','.join(map(str, query_embedding))}]"
            
            # Build raw SQL query with cosine similarity
            sql_query = f"""
                SELECT *, 
                       1 - (embedding <=> {embedding_array}::vector) as similarity
                FROM artifacts
                WHERE company_id = :company_id
                  AND embedding IS NOT NULL
            """
            
            # Add optional filters
            params = {"company_id": company_id}
            if source_tool:
                sql_query += " AND source_tool = :source_tool"
                params["source_tool"] = source_tool.value
            if artifact_type:
                sql_query += " AND artifact_type = :artifact_type"
                params["artifact_type"] = artifact_type.value
            
            # Add ordering and limit
            sql_query += f"""
                ORDER BY embedding <=> {embedding_array}::vector
                LIMIT :limit
            """
            params["limit"] = limit
            
            # Execute raw query
            result = await db.execute(sql_query, params)
            rows = result.fetchall()
            
            # Convert to Artifact objects and calculate similarity
            artifacts_with_similarity = []
            for row in rows:
                # Create Artifact object from row data
                artifact_dict = {
                    'id': row[0],
                    'company_id': row[1],
                    'source_tool': row[2],
                    'artifact_type': row[3],
                    'external_id': row[4],
                    'content': row[5],
                    'author': row[6],
                    'author_email': row[7],
                    'source_created_at': row[8],
                    'metadata': row[9],
                    'embedding': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                }
                
                # Calculate similarity manually if not provided
                similarity = 1 - (row[13] if len(row) > 13 else 0)
                
                if similarity >= threshold:
                    artifact = Artifact(**artifact_dict)
                    artifacts_with_similarity.append((artifact, similarity))
            
            logger.info(f"Found {len(artifacts_with_similarity)} similar artifacts")
            return artifacts_with_similarity
            
        except Exception as e:
            logger.error(f"Failed to search similar artifacts: {e}")
            # Fallback to Python-based similarity calculation
            return await self._fallback_similarity_search(
                db, company_id, query_embedding, limit, threshold, source_tool, artifact_type
            )
    
    async def _fallback_similarity_search(
        self,
        db: AsyncSession,
        company_id: str,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[tuple[Artifact, float]]:
        """
        Fallback similarity search using Python-based calculation
        """
        try:
            # Get all candidate artifacts
            query = select(Artifact).where(
                Artifact.company_id == company_id,
                Artifact.embedding.isnot(None)
            )
            
            if source_tool:
                query = query.where(Artifact.source_tool == source_tool)
            if artifact_type:
                query = query.where(Artifact.artifact_type == artifact_type)
            
            result = await db.execute(query)
            artifacts = result.scalars().all()
            
            # Calculate similarities in Python
            artifacts_with_similarity = []
            for artifact in artifacts:
                if artifact.embedding:
                    similarity = self.embedding_service.calculate_similarity(
                        query_embedding, artifact.embedding
                    )
                    if similarity >= threshold:
                        artifacts_with_similarity.append((artifact, similarity))
            
            # Sort by similarity and limit
            artifacts_with_similarity.sort(key=lambda x: x[1], reverse=True)
            return artifacts_with_similarity[:limit]
            
        except Exception as e:
            logger.error(f"Fallback similarity search also failed: {e}")
            return []
    
    async def semantic_search(
        self,
        db: AsyncSession,
        company_id: str,
        query_text: str,
        limit: int = 10,
        threshold: float = 0.7,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None
    ) -> List[tuple[Artifact, float]]:
        """
        Perform semantic search by generating query embedding first
        """
        try:
            # Generate embedding for query text
            query_embedding = await self.embedding_service.generate_embedding(query_text)
            
            # Search for similar artifacts
            return await self.search_similar_artifacts(
                db, company_id, query_embedding, limit, threshold, source_tool, artifact_type
            )
            
        except Exception as e:
            logger.error(f"Failed to perform semantic search: {e}")
            raise Exception(f"Semantic search failed: {e}")
    
    async def get_company_artifacts(
        self,
        db: AsyncSession,
        company_id: str,
        source_tool: Optional[SourceTool] = None,
        artifact_type: Optional[ArtifactType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Artifact]:
        """
        Get artifacts for a company with optional filters
        """
        query = select(Artifact).where(Artifact.company_id == company_id)
        
        if source_tool:
            query = query.where(Artifact.source_tool == source_tool)
        if artifact_type:
            query = query.where(Artifact.artifact_type == artifact_type)
        
        query = query.order_by(Artifact.created_at.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def delete_artifact(self, db: AsyncSession, artifact_id: str) -> bool:
        """
        Delete an artifact by ID
        """
        try:
            result = await db.execute(
                select(Artifact).where(Artifact.id == artifact_id)
            )
            artifact = result.scalar_one_or_none()
            
            if not artifact:
                return False
            
            await db.delete(artifact)
            await db.commit()
            
            logger.info(f"Deleted artifact {artifact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete artifact: {e}")
            await db.rollback()
            raise Exception(f"Artifact deletion failed: {e}")


# Global artifact store service instance
artifact_store_service = ArtifactStoreService()