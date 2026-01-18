"""
Views for RAG semantic search functionality.

Provides semantic search endpoint for natural language queries against file contents.
"""

import logging
from collections import defaultdict
from typing import List, Dict, Any
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from .services.embeddings import EmbeddingService
from .services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


def initialize_vector_store():
    """Initialize vector store if not already done."""
    try:
        VectorStoreService.get_collection()
    except RuntimeError:
        # Not initialized, do it now
        persist_dir = getattr(
            settings,
            'CHROMADB_PERSIST_DIRECTORY',
            settings.BASE_DIR / 'data' / 'chromadb'
        )
        VectorStoreService.initialize(str(persist_dir))


@api_view(['GET'])
def semantic_search(request):
    """
    Semantic search endpoint for natural language queries.
    
    Query Parameters:
        q (str): Natural language query (required, min 3 chars)
        top_k (int): Maximum number of results (default: 10, max: 50)
        threshold (float): Minimum similarity score 0-1 (default: 0.5)
        aggregation (str): Score aggregation method: 'max', 'mean', 'weighted' (default: 'max')
    
    Returns:
        {
            "query": "original query text",
            "results": [
                {
                    "file_id": "uuid",
                    "file_name": "document.pdf",
                    "file_type": "application/pdf",
                    "score": 0.85,
                    "matched_chunks": 3,
                    "preview": "Best matching text snippet..."
                }
            ],
            "total_results": 5,
            "parameters": {
                "top_k": 10,
                "threshold": 0.5,
                "aggregation": "max"
            }
        }
    
    Error Responses:
        400: Invalid parameters
        500: Search failed (ChromaDB unavailable, etc.)
    """
    # Get query parameter
    query = request.GET.get('q', '').strip()
    
    if not query:
        return Response(
            {'error': 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(query) < 3:
        return Response(
            {'error': 'Query must be at least 3 characters'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(query) > 500:
        query = query[:500]
        logger.warning(f"Query truncated to 500 characters")
    
    # Get optional parameters with validation
    try:
        top_k = int(request.GET.get('top_k', 10))
        if top_k < 1 or top_k > 50:
            return Response(
                {'error': 'top_k must be between 1 and 50'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {'error': 'top_k must be an integer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        threshold = float(request.GET.get('threshold', 0.5))
        if threshold < 0 or threshold > 1:
            return Response(
                {'error': 'threshold must be between 0 and 1'},
                status=status.HTTP_400_BAD_REQUEST
            )
    except ValueError:
        return Response(
            {'error': 'threshold must be a number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    aggregation = request.GET.get('aggregation', 'max').lower()
    if aggregation not in ['max', 'mean', 'weighted']:
        return Response(
            {'error': 'aggregation must be one of: max, mean, weighted'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Initialize vector store if needed
        initialize_vector_store()
        
        # Generate query embedding
        logger.info(f"Semantic search query: '{query}' (top_k={top_k}, threshold={threshold})")
        query_embedding = EmbeddingService.generate_embedding(query)
        
        # Search vector store
        # Request more chunks than top_k since we'll aggregate by file
        chunk_results = VectorStoreService.search(
            query_embedding=query_embedding,
            top_k=top_k * 5,  # Get more chunks to ensure we have enough files
            threshold=threshold
        )
        
        # Aggregate results by file
        file_results = aggregate_results_by_file(chunk_results, aggregation)
        
        # Limit to top_k files
        file_results = file_results[:top_k]
        
        logger.info(f"Search returned {len(file_results)} files from {len(chunk_results)} chunks")
        
        return Response({
            'query': query,
            'results': file_results,
            'total_results': len(file_results),
            'parameters': {
                'top_k': top_k,
                'threshold': threshold,
                'aggregation': aggregation
            }
        })
        
    except RuntimeError as e:
        logger.error(f"Vector store unavailable: {str(e)}")
        return Response(
            {
                'error': 'Semantic search unavailable',
                'details': 'Vector store not initialized. Please ensure ChromaDB is set up.'
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}", exc_info=True)
        return Response(
            {
                'error': 'Search failed',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def aggregate_results_by_file(
    chunk_results: List[Dict[str, Any]],
    aggregation: str = 'max'
) -> List[Dict[str, Any]]:
    """
    Aggregate chunk results by file.
    
    Args:
        chunk_results: List of chunk search results
        aggregation: Method to aggregate scores ('max', 'mean', 'weighted')
    
    Returns:
        List of file results sorted by score (descending)
    """
    # Group chunks by file_id
    file_chunks = defaultdict(list)
    
    for chunk in chunk_results:
        file_id = chunk['file_id']
        file_chunks[file_id].append(chunk)
    
    # Aggregate scores per file
    file_results = []
    
    for file_id, chunks in file_chunks.items():
        # Get file metadata from first chunk
        first_chunk = chunks[0]
        
        # Calculate aggregated score
        if aggregation == 'max':
            # Max score: file is relevant if any chunk matches well
            score = max(chunk['score'] for chunk in chunks)
        elif aggregation == 'mean':
            # Mean score: average relevance across all chunks
            score = sum(chunk['score'] for chunk in chunks) / len(chunks)
        elif aggregation == 'weighted':
            # Weighted: higher weight to top chunks
            sorted_chunks = sorted(chunks, key=lambda x: x['score'], reverse=True)
            weights = [1.0 / (i + 1) for i in range(len(sorted_chunks))]
            total_weight = sum(weights)
            score = sum(
                chunk['score'] * weight
                for chunk, weight in zip(sorted_chunks, weights)
            ) / total_weight
        else:
            score = max(chunk['score'] for chunk in chunks)
        
        # Get best matching chunk for preview
        best_chunk = max(chunks, key=lambda x: x['score'])
        preview = best_chunk['chunk_text']
        if len(preview) > 200:
            preview = preview[:200] + '...'
        
        file_results.append({
            'file_id': file_id,
            'file_name': first_chunk['file_name'],
            'file_type': first_chunk['file_type'],
            'score': round(score, 4),
            'matched_chunks': len(chunks),
            'preview': preview
        })
    
    # Sort by score descending
    file_results.sort(key=lambda x: x['score'], reverse=True)
    
    return file_results


@api_view(['GET'])
def rag_stats(request):
    """
    Get RAG indexing statistics.
    
    Returns:
        {
            "total_indexed_chunks": 1234,
            "collection_name": "file_vault_embeddings",
            "embedding_dimension": 384,
            "model_name": "all-MiniLM-L6-v2"
        }
    """
    try:
        initialize_vector_store()
        
        stats = VectorStoreService.get_collection_stats()
        stats['embedding_dimension'] = EmbeddingService.get_dimension()
        stats['model_name'] = EmbeddingService.MODEL_NAME
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve statistics', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
