#!/usr/bin/env python
"""
Script to inspect ChromaDB embeddings and indexed chunks.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from files.services.vector_store import VectorStoreService
from django.conf import settings

def inspect_embeddings():
    """Inspect all embeddings in ChromaDB."""
    
    print("=" * 70)
    print("RAG EMBEDDINGS INSPECTION")
    print("=" * 70)
    print()
    
    # Initialize vector store
    persist_dir = getattr(
        settings,
        'CHROMADB_PERSIST_DIRECTORY',
        settings.BASE_DIR / 'data' / 'chromadb'
    )
    VectorStoreService.initialize(str(persist_dir))
    
    # Get collection
    collection = VectorStoreService.get_collection()
    
    # Get stats
    stats = VectorStoreService.get_collection_stats()
    print(f"Collection Name: {stats['collection_name']}")
    print(f"Total Chunks: {stats['total_chunks']}")
    print()
    
    if stats['total_chunks'] == 0:
        print("No embeddings found. Upload some files first!")
        return
    
    # Get all data from collection
    print("Fetching all chunks...")
    results = collection.get(
        include=['documents', 'metadatas', 'embeddings']
    )
    
    print(f"Retrieved {len(results['ids'])} chunks")
    print()
    
    # Group by file
    files_dict = {}
    for i, chunk_id in enumerate(results['ids']):
        metadata = results['metadatas'][i]
        document = results['documents'][i]
        embedding = results['embeddings'][i]
        
        file_id = metadata['file_id']
        if file_id not in files_dict:
            files_dict[file_id] = {
                'file_name': metadata['file_name'],
                'file_type': metadata['file_type'],
                'chunks': []
            }
        
        files_dict[file_id]['chunks'].append({
            'chunk_id': chunk_id,
            'chunk_index': metadata['chunk_index'],
            'text': document,
            'embedding_dim': len(embedding),
            'embedding_sample': embedding[:5]  # First 5 dimensions
        })
    
    # Display results
    print("=" * 70)
    print(f"INDEXED FILES: {len(files_dict)}")
    print("=" * 70)
    print()
    
    for file_id, file_info in files_dict.items():
        print(f"📄 File: {file_info['file_name']}")
        print(f"   Type: {file_info['file_type']}")
        print(f"   File ID: {file_id}")
        print(f"   Chunks: {len(file_info['chunks'])}")
        print()
        
        for chunk in sorted(file_info['chunks'], key=lambda x: x['chunk_index']):
            print(f"   Chunk #{chunk['chunk_index']}:")
            print(f"   ID: {chunk['chunk_id']}")
            print(f"   Embedding: {chunk['embedding_dim']} dimensions")
            print(f"   Sample: {chunk['embedding_sample']}")
            print(f"   Text Preview (first 100 chars):")
            preview = chunk['text'][:100].replace('\n', ' ')
            print(f"   '{preview}...'")
            print()
        
        print("-" * 70)
        print()
    
    # Summary
    total_chunks = sum(len(f['chunks']) for f in files_dict.values())
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Files: {len(files_dict)}")
    print(f"Total Chunks: {total_chunks}")
    print(f"Embedding Dimension: 384")
    print(f"Model: all-MiniLM-L6-v2")
    print()


if __name__ == '__main__':
    try:
        inspect_embeddings()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
