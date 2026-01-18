"""
Embedding generation service for RAG semantic search.

Uses sentence-transformers (all-MiniLM-L6-v2) to generate 384-dimensional
embeddings for text chunks.
"""

import logging
from typing import List, Optional
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""
    
    MODEL_NAME = 'all-MiniLM-L6-v2'
    EMBEDDING_DIMENSION = 384
    
    _model: Optional[SentenceTransformer] = None
    
    @classmethod
    def get_model(cls) -> SentenceTransformer:
        """
        Get or load the embedding model (singleton pattern).
        
        Returns:
            Loaded SentenceTransformer model
            
        Raises:
            RuntimeError: If sentence-transformers is not installed
        """
        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        
        if cls._model is None:
            logger.info(f"Loading embedding model: {cls.MODEL_NAME}")
            cls._model = SentenceTransformer(cls.MODEL_NAME)
            logger.info(f"Model loaded successfully")
        
        return cls._model
    
    @classmethod
    def generate_embeddings(
        cls,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            batch_size: Batch size for encoding (for efficiency)
            show_progress: Whether to show progress bar
            
        Returns:
            numpy array of shape (len(texts), 384)
            
        Raises:
            ValueError: If texts is empty
            RuntimeError: If model loading fails
        """
        if not texts:
            raise ValueError("Cannot generate embeddings for empty text list")
        
        try:
            model = cls.get_model()
            
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True
            )
            
            logger.info(f"Generated {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    @classmethod
    def generate_embedding(cls, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            numpy array of shape (384,)
            
        Raises:
            ValueError: If text is empty
            RuntimeError: If model loading fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        embeddings = cls.generate_embeddings([text], show_progress=False)
        return embeddings[0]
    
    @classmethod
    def get_dimension(cls) -> int:
        """
        Get the embedding dimension.
        
        Returns:
            Embedding dimension (384)
        """
        return cls.EMBEDDING_DIMENSION
