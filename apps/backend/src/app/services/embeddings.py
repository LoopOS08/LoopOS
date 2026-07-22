from openai import AsyncOpenAI
from typing import List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI"""
    
    def __init__(self):
        self._client = None
        self._model = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client
    
    @property
    def model(self):
        if self._model is None:
            self._model = settings.OPENAI_EMBEDDING_MODEL
        return self._model
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise Exception(f"Embedding generation failed: {e}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise Exception(f"Batch embedding generation failed: {e}")
    
    async def generate_artifact_embedding(self, artifact_content: str, metadata: dict) -> List[float]:
        """
        Generate embedding for an artifact with enhanced context
        """
        # Enhance content with metadata for better semantic representation
        enhanced_text = self._enhance_artifact_text(artifact_content, metadata)
        return await self.generate_embedding(enhanced_text)
    
    def _enhance_artifact_text(self, content: str, metadata: dict) -> str:
        """
        Enhance artifact text with metadata for better embedding quality
        """
        enhanced_parts = [content]
        
        # Add author information if available
        if 'author' in metadata:
            enhanced_parts.append(f"Author: {metadata['author']}")
        
        # Add source tool if available
        if 'source_tool' in metadata:
            enhanced_parts.append(f"Source: {metadata['source_tool']}")
        
        # Add artifact type if available
        if 'artifact_type' in metadata:
            enhanced_parts.append(f"Type: {metadata['artifact_type']}")
        
        # Add any other relevant metadata
        for key, value in metadata.items():
            if key not in ['author', 'source_tool', 'artifact_type'] and isinstance(value, str):
                enhanced_parts.append(f"{key}: {value}")
        
        return " ".join(enhanced_parts)
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        """
        try:
            import numpy as np
            
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            magnitude1 = np.linalg.norm(vec1)
            magnitude2 = np.linalg.norm(vec2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            return float(dot_product / (magnitude1 * magnitude2))
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0


# Global embedding service instance
embedding_service = EmbeddingService()