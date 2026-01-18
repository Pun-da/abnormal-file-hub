"""
Vector store service using ChromaDB for RAG semantic search.

Manages persistent storage and retrieval of document embeddings with metadata.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing vector embeddings in ChromaDB."""
    
    COLLECTION_NAME = 'file_vault_embeddings'
    
    _client: Optional[Any] = None
    _collection: Optional[Any] = None
    
    @classmethod
    def initialize(cls, persist_directory: str) -> None:
        """
        Initialize ChromaDB client and collection.
        
        Args:
            persist_directory: Directory for persistent storage
        """
        if chromadb is None:
            raise RuntimeError(
                "chromadb not installed. "
                "Install with: pip install chromadb"
            )
        
        try:
            # Create persist directory if it doesn't exist
            Path(persist_directory).mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Initializing ChromaDB at {persist_directory}")
            
            # Initialize client with persistence
            cls._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            cls._collection = cls._client.get_or_create_collection(
                name=cls.COLLECTION_NAME,
                metadata={
                    "description": "File vault document embeddings for semantic search",
                    "embedding_dimension": 384
                }
            )
            
            logger.info(
                f"ChromaDB initialized. Collection '{cls.COLLECTION_NAME}' "
                f"contains {cls._collection.count()} embeddings"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise
    
    @classmethod
    def get_collection(cls):
        """
        Get the ChromaDB collection, initializing if needed.
        
        Returns:
            ChromaDB collection
            
        Raises:
            RuntimeError: If collection is not initialized
        """
        if cls._collection is None:
            raise RuntimeError(
                "VectorStoreService not initialized. "
                "Call initialize() with persist_directory first."
            )
        return cls._collection
    
    @classmethod
    def add_document_chunks(
        cls,
        file_id: UUID,
        chunks: List[Tuple[str, int]],
        embeddings: np.ndarray,
        file_name: str,
        file_type: str
    ) -> int:
        """
        Add document chunks and their embeddings to the vector store.
        
        Args:
            file_id: UUID of the file
            chunks: List of (chunk_text, chunk_index) tuples
            embeddings: numpy array of embeddings (shape: [n_chunks, 384])
            file_name: Original filename
            file_type: MIME type
            
        Returns:
            Number of chunks added
            
        Raises:
            ValueError: If chunks and embeddings don't match
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            )
        
        if len(chunks) == 0:
            logger.warning(f"No chunks to add for file {file_id}")
            return 0
        
        try:
            collection = cls.get_collection()
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            metadatas = []
            embeddings_list = []
            
            file_id_str = str(file_id)
            
            for (chunk_text, chunk_index), embedding in zip(chunks, embeddings):
                # Create unique ID for this chunk
                chunk_id = f"{file_id_str}_{chunk_index}"
                
                ids.append(chunk_id)
                documents.append(chunk_text)
                metadatas.append({
                    'file_id': file_id_str,
                    'chunk_index': chunk_index,
                    'file_name': file_name,
                    'file_type': file_type
                })
                embeddings_list.append(embedding.tolist())
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings_list
            )
            
            logger.info(f"Added {len(chunks)} chunks for file {file_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add chunks for file {file_id}: {str(e)}")
            raise
    
    @classmethod
    def search(
        cls,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using query embedding.
        
        Args:
            query_embedding: Query embedding vector (shape: [384])
            top_k: Maximum number of results
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of result dictionaries with keys:
            - chunk_id: Unique chunk identifier
            - file_id: File UUID
            - chunk_index: Position in document
            - file_name: Original filename
            - file_type: MIME type
            - chunk_text: The matched text
            - score: Similarity score (0-1, higher is better)
        """
        try:
            collection = cls.get_collection()
            
            # Query ChromaDB
            results = collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Process results
            processed_results = []
            
            if not results['ids'] or not results['ids'][0]:
                return []
            
            for i, chunk_id in enumerate(results['ids'][0]):
                # Convert distance to similarity score
                # ChromaDB uses squared L2 distance; convert to cosine-like score
                distance = results['distances'][0][i]
                # For normalized embeddings, squared L2 = 2(1 - cosine_similarity)
                # So: similarity ≈ 1 - (distance / 2)
                # Clamp to [0, 1]
                score = max(0.0, min(1.0, 1.0 - (distance / 2.0)))
                
                # Apply threshold filter
                if score < threshold:
                    continue
                
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                
                processed_results.append({
                    'chunk_id': chunk_id,
                    'file_id': metadata['file_id'],
                    'chunk_index': metadata['chunk_index'],
                    'file_name': metadata['file_name'],
                    'file_type': metadata['file_type'],
                    'chunk_text': document,
                    'score': score
                })
            
            logger.info(
                f"Search returned {len(processed_results)} results "
                f"(threshold: {threshold})"
            )
            
            return processed_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    @classmethod
    def delete_file_chunks(cls, file_id: UUID) -> int:
        """
        Delete all chunks associated with a file.
        
        Args:
            file_id: UUID of the file
            
        Returns:
            Number of chunks deleted
        """
        try:
            collection = cls.get_collection()
            file_id_str = str(file_id)
            
            # Get all chunks for this file
            results = collection.get(
                where={'file_id': file_id_str},
                include=[]  # Only need IDs
            )
            
            chunk_ids = results['ids']
            
            if not chunk_ids:
                logger.info(f"No chunks found for file {file_id}")
                return 0
            
            # Delete chunks
            collection.delete(ids=chunk_ids)
            
            logger.info(f"Deleted {len(chunk_ids)} chunks for file {file_id}")
            return len(chunk_ids)
            
        except Exception as e:
            logger.error(f"Failed to delete chunks for file {file_id}: {str(e)}")
            raise
    
    @classmethod
    def get_file_chunk_count(cls, file_id: UUID) -> int:
        """
        Get the number of chunks indexed for a file.
        
        Args:
            file_id: UUID of the file
            
        Returns:
            Number of indexed chunks
        """
        try:
            collection = cls.get_collection()
            file_id_str = str(file_id)
            
            results = collection.get(
                where={'file_id': file_id_str},
                include=[]
            )
            
            return len(results['ids'])
            
        except Exception as e:
            logger.error(f"Failed to get chunk count for file {file_id}: {str(e)}")
            return 0
    
    @classmethod
    def get_collection_stats(cls) -> Dict[str, Any]:
        """
        Get statistics about the vector store collection.
        
        Returns:
            Dictionary with stats:
            - total_chunks: Total number of indexed chunks
            - collection_name: Name of the collection
        """
        try:
            collection = cls.get_collection()
            
            return {
                'total_chunks': collection.count(),
                'collection_name': cls.COLLECTION_NAME
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                'total_chunks': 0,
                'collection_name': cls.COLLECTION_NAME,
                'error': str(e)
            }
    
    @classmethod
    def reset_collection(cls) -> None:
        """
        Reset the collection (delete all embeddings).
        WARNING: This deletes all indexed data!
        """
        try:
            if cls._client is None:
                logger.warning("Client not initialized, nothing to reset")
                return
            
            logger.warning(f"Resetting collection: {cls.COLLECTION_NAME}")
            cls._client.delete_collection(cls.COLLECTION_NAME)
            
            # Recreate collection
            cls._collection = cls._client.get_or_create_collection(
                name=cls.COLLECTION_NAME,
                metadata={
                    "description": "File vault document embeddings for semantic search",
                    "embedding_dimension": 384
                }
            )
            
            logger.info("Collection reset complete")
            
        except Exception as e:
            logger.error(f"Failed to reset collection: {str(e)}")
            raise
