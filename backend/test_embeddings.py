#!/usr/bin/env python
"""
Interactive tool to test embeddings and semantic search.
"""

import os
import sys
import django
import numpy as np

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from files.services.vector_store import VectorStoreService
from files.services.embeddings import EmbeddingService
from django.conf import settings


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def test_search(query_text, top_k=5, threshold=0.3):
    """Test semantic search with a query."""
    
    print("\n" + "=" * 70)
    print(f"TESTING QUERY: '{query_text}'")
    print("=" * 70)
    
    # Generate query embedding
    print("\n1. Generating query embedding...")
    query_embedding = EmbeddingService.generate_embedding(query_text)
    print(f"   ✓ Query embedding: 384 dimensions")
    print(f"   ✓ Sample: {query_embedding[:5]}")
    
    # Search
    print(f"\n2. Searching with threshold={threshold}, top_k={top_k}...")
    results = VectorStoreService.search(
        query_embedding=query_embedding,
        top_k=top_k,
        threshold=threshold
    )
    
    print(f"   ✓ Found {len(results)} chunks")
    
    # Display results
    if results:
        print("\n3. Results:")
        print("-" * 70)
        
        for i, result in enumerate(results, 1):
            print(f"\n   Result #{i}")
            print(f"   File: {result['file_name']}")
            print(f"   Score: {result['score']:.4f} ({result['score']*100:.1f}%)")
            print(f"   Chunk Index: {result['chunk_index']}")
            print(f"   Preview: {result['chunk_text'][:150]}...")
            print()
    else:
        print("\n   ⚠ No results found. Try:")
        print("     - Lower threshold (e.g., 0.2)")
        print("     - Different query terms")
        print("     - Upload more files")
    
    return results


def compare_queries():
    """Compare multiple queries to see similarity scores."""
    
    print("\n" + "=" * 70)
    print("QUERY COMPARISON")
    print("=" * 70)
    
    queries = [
        "software engineer",
        "backend developer",
        "file storage system",
        "duplicate files",
        "product requirements",
    ]
    
    print("\nGenerating embeddings for all queries...")
    embeddings = {}
    for query in queries:
        embeddings[query] = EmbeddingService.generate_embedding(query)
        print(f"   ✓ {query}")
    
    print("\nQuery Similarity Matrix:")
    print("-" * 70)
    print(f"{'Query':<30} ", end="")
    for q in queries:
        print(f"{q[:15]:<17}", end="")
    print()
    print("-" * 70)
    
    for q1 in queries:
        print(f"{q1:<30} ", end="")
        for q2 in queries:
            sim = cosine_similarity(embeddings[q1], embeddings[q2])
            print(f"{sim:6.4f}           ", end="")
        print()
    print()


def main():
    """Main function."""
    
    print("\n" + "=" * 70)
    print("RAG EMBEDDING TESTING TOOL")
    print("=" * 70)
    
    # Initialize
    persist_dir = getattr(
        settings,
        'CHROMADB_PERSIST_DIRECTORY',
        settings.BASE_DIR / 'data' / 'chromadb'
    )
    VectorStoreService.initialize(str(persist_dir))
    
    # Get stats
    stats = VectorStoreService.get_collection_stats()
    print(f"\nCollection: {stats['collection_name']}")
    print(f"Total Chunks: {stats['total_chunks']}")
    print(f"Model: all-MiniLM-L6-v2 (384 dimensions)")
    
    if stats['total_chunks'] == 0:
        print("\n⚠ No embeddings found. Upload some files first!")
        return
    
    # Test searches
    test_queries = [
        "software engineer backend",
        "file storage deduplication",
        "product requirements",
    ]
    
    for query in test_queries:
        test_search(query, top_k=3, threshold=0.25)
    
    # Compare queries
    compare_queries()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("\nEmbeddings are working correctly!")
    print("\nTo test with your own query:")
    print("  python test_embeddings.py 'your query here'")
    print("\nOr use the UI:")
    print("  http://localhost:3000 -> Semantic Search tab")
    print()


if __name__ == '__main__':
    try:
        if len(sys.argv) > 1:
            # Custom query from command line
            query = ' '.join(sys.argv[1:])
            persist_dir = getattr(
                settings,
                'CHROMADB_PERSIST_DIRECTORY',
                settings.BASE_DIR / 'data' / 'chromadb'
            )
            VectorStoreService.initialize(str(persist_dir))
            test_search(query, top_k=5, threshold=0.25)
        else:
            main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
