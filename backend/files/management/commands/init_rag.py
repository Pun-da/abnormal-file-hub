"""
Management command to initialize RAG vector store.

Usage:
    python manage.py init_rag
    python manage.py init_rag --reindex  # Reindex all existing files
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from files.services.vector_store import VectorStoreService
from files.tasks import reindex_all_files


class Command(BaseCommand):
    help = 'Initialize RAG vector store (ChromaDB) and optionally reindex all files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reindex',
            action='store_true',
            help='Reindex all existing files after initialization',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset (delete) existing vector store before initialization',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Initializing RAG vector store...'))
        
        # Get persist directory from settings
        persist_dir = getattr(
            settings,
            'CHROMADB_PERSIST_DIRECTORY',
            settings.BASE_DIR / 'data' / 'chromadb'
        )
        
        self.stdout.write(f'ChromaDB directory: {persist_dir}')
        
        try:
            # Initialize vector store
            VectorStoreService.initialize(str(persist_dir))
            
            if options['reset']:
                self.stdout.write(self.style.WARNING('Resetting vector store...'))
                VectorStoreService.reset_collection()
                self.stdout.write(self.style.SUCCESS('Vector store reset complete'))
            
            # Get stats
            stats = VectorStoreService.get_collection_stats()
            self.stdout.write(
                f"Collection: {stats['collection_name']}\n"
                f"Existing chunks: {stats['total_chunks']}"
            )
            
            self.stdout.write(self.style.SUCCESS('RAG vector store initialized successfully'))
            
            # Reindex if requested
            if options['reindex']:
                self.stdout.write(self.style.NOTICE('Starting reindexing of all files...'))
                self.stdout.write(
                    self.style.WARNING(
                        'This may take a while depending on the number of files.'
                    )
                )
                
                result = reindex_all_files()
                
                if result.get('success'):
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Reindexing complete:\n"
                            f"  Total files: {result['total_files']}\n"
                            f"  Indexed: {result['indexed']}\n"
                            f"  Skipped: {result['skipped']}"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Reindexing failed: {result.get('error', 'Unknown error')}"
                        )
                    )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to initialize RAG: {str(e)}')
            )
            raise
