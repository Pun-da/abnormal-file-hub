"""
Files app configuration.

Initializes RAG vector store on app startup.
"""

import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class FilesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'files'
    
    def ready(self):
        """
        Initialize RAG vector store when app is ready.
        
        This ensures ChromaDB is initialized before any requests are processed.
        """
        # Only initialize in main process (not in management commands)
        import sys
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv[0]:
            try:
                from django.conf import settings
                from files.services.vector_store import VectorStoreService
                
                persist_dir = getattr(
                    settings,
                    'CHROMADB_PERSIST_DIRECTORY',
                    settings.BASE_DIR / 'data' / 'chromadb'
                )
                
                logger.info("Initializing RAG vector store on startup...")
                VectorStoreService.initialize(str(persist_dir))
                
                stats = VectorStoreService.get_collection_stats()
                logger.info(
                    f"RAG vector store ready: {stats['total_chunks']} chunks indexed"
                )
                
            except Exception as e:
                logger.warning(
                    f"Failed to initialize RAG vector store on startup: {str(e)}. "
                    f"Run 'python manage.py init_rag' to initialize manually."
                )
