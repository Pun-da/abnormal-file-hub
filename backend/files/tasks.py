"""
Celery tasks for RAG indexing operations.

Handles asynchronous text extraction, chunking, embedding generation,
and vector storage for uploaded files.
"""

import logging
from uuid import UUID
from celery import shared_task
from django.conf import settings
from contracts.models import File
from .services.text_extraction import TextExtractionService
from .services.chunking import ChunkingService
from .services.embeddings import EmbeddingService
from .services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


def _ensure_vector_store_initialized():
    """Ensure VectorStoreService is initialized in this worker process."""
    try:
        VectorStoreService.get_collection()
    except RuntimeError:
        # Not initialized, do it now
        from django.conf import settings
        persist_dir = getattr(
            settings,
            'CHROMADB_PERSIST_DIRECTORY',
            settings.BASE_DIR / 'data' / 'chromadb'
        )
        logger.info(f"Initializing VectorStore in worker: {persist_dir}")
        VectorStoreService.initialize(str(persist_dir))


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3},
    name='files.tasks.index_file_for_rag'
)
def index_file_for_rag(self, file_id: str) -> dict:
    """
    Index a file for semantic search (RAG).
    
    This task:
    1. Extracts text from the file
    2. Chunks the text
    3. Generates embeddings
    4. Stores in vector database
    
    Args:
        file_id: UUID string of the file to index
        
    Returns:
        Dictionary with indexing results
    """
    try:
        # Ensure VectorStore is initialized in this worker
        _ensure_vector_store_initialized()
        
        file_uuid = UUID(file_id)
        logger.info(f"Starting RAG indexing for file {file_uuid}")
        
        # Get file record
        try:
            file_record = File.objects.select_related('content').get(id=file_uuid)
        except File.DoesNotExist:
            logger.error(f"File {file_uuid} not found")
            return {
                'success': False,
                'error': 'File not found',
                'file_id': file_id
            }
        
        # Get file path
        file_path = file_record.content.file.path
        
        # Check if file type is supported
        if not TextExtractionService.is_supported(file_path):
            logger.info(f"File {file_uuid} has unsupported type, skipping indexing")
            return {
                'success': True,
                'skipped': True,
                'reason': 'Unsupported file type',
                'file_id': file_id,
                'file_name': file_record.original_filename
            }
        
        # Extract text
        logger.info(f"Extracting text from {file_record.original_filename}")
        text, error = TextExtractionService.extract_text(file_path)
        
        if error or not text:
            logger.warning(
                f"Text extraction failed for {file_uuid}: {error or 'empty content'}"
            )
            return {
                'success': True,
                'skipped': True,
                'reason': error or 'No text content',
                'file_id': file_id,
                'file_name': file_record.original_filename
            }
        
        # Check minimum text length
        if len(text.strip()) < 50:
            logger.info(f"File {file_uuid} has insufficient text content")
            return {
                'success': True,
                'skipped': True,
                'reason': 'Insufficient text content',
                'file_id': file_id,
                'file_name': file_record.original_filename
            }
        
        # Chunk text
        logger.info(f"Chunking text ({len(text)} chars)")
        chunks = ChunkingService.chunk_text(text)
        
        if not chunks:
            logger.warning(f"No chunks generated for {file_uuid}")
            return {
                'success': True,
                'skipped': True,
                'reason': 'No chunks generated',
                'file_id': file_id,
                'file_name': file_record.original_filename
            }
        
        # Generate embeddings
        chunk_texts = [chunk_text for chunk_text, _ in chunks]
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks")
        embeddings = EmbeddingService.generate_embeddings(
            chunk_texts,
            batch_size=32,
            show_progress=False
        )
        
        # Store in vector database
        logger.info(f"Storing {len(chunks)} chunks in vector database")
        chunks_added = VectorStoreService.add_document_chunks(
            file_id=file_uuid,
            chunks=chunks,
            embeddings=embeddings,
            file_name=file_record.original_filename,
            file_type=file_record.file_type
        )
        
        logger.info(f"Successfully indexed file {file_uuid} with {chunks_added} chunks")
        
        return {
            'success': True,
            'file_id': file_id,
            'file_name': file_record.original_filename,
            'chunks_indexed': chunks_added,
            'text_length': len(text)
        }
        
    except Exception as e:
        logger.error(f"RAG indexing failed for file {file_id}: {str(e)}", exc_info=True)
        # Re-raise for Celery retry
        raise


@shared_task(
    bind=True,
    name='files.tasks.delete_file_from_rag'
)
def delete_file_from_rag(self, file_id: str) -> dict:
    """
    Remove a file's vectors from the RAG index.
    
    Args:
        file_id: UUID string of the file to remove
        
    Returns:
        Dictionary with deletion results
    """
    try:
        # Ensure VectorStore is initialized in this worker
        _ensure_vector_store_initialized()
        
        file_uuid = UUID(file_id)
        logger.info(f"Deleting RAG index for file {file_uuid}")
        
        chunks_deleted = VectorStoreService.delete_file_chunks(file_uuid)
        
        logger.info(f"Deleted {chunks_deleted} chunks for file {file_uuid}")
        
        return {
            'success': True,
            'file_id': file_id,
            'chunks_deleted': chunks_deleted
        }
        
    except Exception as e:
        logger.error(f"RAG deletion failed for file {file_id}: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'file_id': file_id
        }


@shared_task(
    bind=True,
    name='files.tasks.reindex_all_files'
)
def reindex_all_files(self) -> dict:
    """
    Reindex all files in the database.
    Useful for rebuilding the RAG index from scratch.
    
    Returns:
        Dictionary with reindexing results
    """
    try:
        logger.info("Starting full reindexing of all files")
        
        # Get all files
        files = File.objects.select_related('content').all()
        total_files = files.count()
        
        logger.info(f"Found {total_files} files to reindex")
        
        # Queue indexing tasks for all files
        indexed_count = 0
        skipped_count = 0
        
        for file_record in files:
            try:
                result = index_file_for_rag(str(file_record.id))
                if result.get('success') and not result.get('skipped'):
                    indexed_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"Failed to index file {file_record.id}: {str(e)}")
                skipped_count += 1
        
        logger.info(
            f"Reindexing complete: {indexed_count} indexed, "
            f"{skipped_count} skipped, {total_files} total"
        )
        
        return {
            'success': True,
            'total_files': total_files,
            'indexed': indexed_count,
            'skipped': skipped_count
        }
        
    except Exception as e:
        logger.error(f"Full reindexing failed: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e)
        }
