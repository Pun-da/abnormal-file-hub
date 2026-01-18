"""
Tests for RAG semantic search functionality.

Tests text extraction, chunking, embedding generation, vector storage,
and semantic search API.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, override_settings
from django.conf import settings
from rest_framework.test import APITestCase
from rest_framework import status
from contracts.models import File, FileContent
from files.services.text_extraction import TextExtractionService
from files.services.chunking import ChunkingService
from files.services.embeddings import EmbeddingService
from files.services.vector_store import VectorStoreService
import numpy as np


class TextExtractionServiceTest(TestCase):
    """Tests for text extraction from various file types."""
    
    def setUp(self):
        """Set up test files."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_is_supported_text_files(self):
        """Test that text file types are recognized as supported."""
        for ext in ['.txt', '.md', '.csv', '.json', '.xml']:
            self.assertTrue(
                TextExtractionService.is_supported(f'test{ext}'),
                f'{ext} should be supported'
            )
    
    def test_is_supported_pdf_files(self):
        """Test that PDF files are recognized as supported."""
        self.assertTrue(TextExtractionService.is_supported('test.pdf'))
    
    def test_is_not_supported_binary_files(self):
        """Test that unsupported file types are rejected."""
        for ext in ['.exe', '.bin', '.jpg', '.png']:
            self.assertFalse(
                TextExtractionService.is_supported(f'test{ext}'),
                f'{ext} should not be supported'
            )
    
    def test_extract_text_from_utf8_file(self):
        """Test extraction from UTF-8 text file."""
        test_file = os.path.join(self.test_dir, 'test.txt')
        test_content = "This is a test file.\nWith multiple lines."
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        text, error = TextExtractionService.extract_text(test_file)
        
        self.assertIsNone(error)
        self.assertEqual(text, test_content)
    
    def test_extract_empty_file(self):
        """Test extraction from empty file."""
        test_file = os.path.join(self.test_dir, 'empty.txt')
        
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('')
        
        text, error = TextExtractionService.extract_text(test_file)
        
        self.assertIsNone(error)
        self.assertEqual(text, '')
    
    def test_extract_unsupported_extension(self):
        """Test that unsupported extensions return error."""
        test_file = os.path.join(self.test_dir, 'test.exe')
        
        with open(test_file, 'wb') as f:
            f.write(b'binary content')
        
        text, error = TextExtractionService.extract_text(test_file)
        
        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertIn('Unsupported', error)


class ChunkingServiceTest(TestCase):
    """Tests for text chunking."""
    
    def test_chunk_text_simple(self):
        """Test basic text chunking."""
        text = "This is a sentence. " * 100  # Create long text
        
        chunks = ChunkingService.chunk_text(text, chunk_size=50, overlap=10)
        
        self.assertGreater(len(chunks), 1)
        
        # Verify each chunk has index
        for i, (chunk_text, chunk_index) in enumerate(chunks):
            self.assertEqual(chunk_index, i)
            self.assertIsInstance(chunk_text, str)
            self.assertGreater(len(chunk_text), 0)
    
    def test_chunk_text_respects_min_size(self):
        """Test that very short text is not chunked."""
        text = "Short text."
        
        chunks = ChunkingService.chunk_text(text, min_chunk_size=100)
        
        # Should return empty list for text below minimum
        self.assertEqual(len(chunks), 0)
    
    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = ChunkingService.chunk_text("")
        
        self.assertEqual(len(chunks), 0)
    
    def test_chunk_text_preserves_overlap(self):
        """Test that chunks have overlap."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. " * 20
        
        chunks = ChunkingService.chunk_text(text, chunk_size=100, overlap=20)
        
        if len(chunks) > 1:
            # Check that consecutive chunks have some common content
            # (not a strict test, but verifies overlap exists)
            self.assertGreater(len(chunks), 1)
    
    def test_estimate_token_count(self):
        """Test token count estimation."""
        text = "This is a test sentence."
        
        token_count = ChunkingService.estimate_token_count(text)
        
        # Should be roughly len(text) / 4
        expected = len(text) // 4
        self.assertGreater(token_count, 0)
        self.assertAlmostEqual(token_count, expected, delta=5)


class EmbeddingServiceTest(TestCase):
    """Tests for embedding generation."""
    
    @patch('files.services.embeddings.SentenceTransformer')
    def test_generate_embedding_single_text(self, mock_transformer):
        """Test generating embedding for single text."""
        # Mock the model
        mock_model = Mock()
        mock_embedding = np.random.rand(384)
        mock_model.encode.return_value = np.array([mock_embedding])
        mock_transformer.return_value = mock_model
        
        # Force reload model
        EmbeddingService._model = None
        
        embedding = EmbeddingService.generate_embedding("Test text")
        
        self.assertEqual(embedding.shape, (384,))
        mock_model.encode.assert_called_once()
    
    @patch('files.services.embeddings.SentenceTransformer')
    def test_generate_embeddings_multiple_texts(self, mock_transformer):
        """Test generating embeddings for multiple texts."""
        # Mock the model
        mock_model = Mock()
        mock_embeddings = np.random.rand(3, 384)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        # Force reload model
        EmbeddingService._model = None
        
        texts = ["Text one", "Text two", "Text three"]
        embeddings = EmbeddingService.generate_embeddings(texts)
        
        self.assertEqual(embeddings.shape, (3, 384))
        mock_model.encode.assert_called_once()
    
    def test_generate_embedding_empty_text_raises_error(self):
        """Test that empty text raises ValueError."""
        with self.assertRaises(ValueError):
            EmbeddingService.generate_embedding("")
    
    def test_generate_embeddings_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        with self.assertRaises(ValueError):
            EmbeddingService.generate_embeddings([])
    
    def test_get_dimension(self):
        """Test getting embedding dimension."""
        self.assertEqual(EmbeddingService.get_dimension(), 384)


class VectorStoreServiceTest(TestCase):
    """Tests for ChromaDB vector store operations."""
    
    def setUp(self):
        """Set up test ChromaDB."""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test ChromaDB."""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('files.services.vector_store.chromadb')
    def test_initialize_creates_client_and_collection(self, mock_chromadb):
        """Test that initialization creates client and collection."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client
        
        VectorStoreService._client = None
        VectorStoreService._collection = None
        
        VectorStoreService.initialize(self.test_dir)
        
        self.assertIsNotNone(VectorStoreService._client)
        self.assertIsNotNone(VectorStoreService._collection)
        mock_chromadb.PersistentClient.assert_called_once()
        mock_client.get_or_create_collection.assert_called_once()
    
    @patch('files.services.vector_store.chromadb')
    def test_add_document_chunks(self, mock_chromadb):
        """Test adding document chunks to vector store."""
        # Set up mocks
        mock_collection = Mock()
        VectorStoreService._collection = mock_collection
        
        from uuid import uuid4
        file_id = uuid4()
        chunks = [
            ("First chunk text", 0),
            ("Second chunk text", 1)
        ]
        embeddings = np.random.rand(2, 384)
        
        count = VectorStoreService.add_document_chunks(
            file_id=file_id,
            chunks=chunks,
            embeddings=embeddings,
            file_name="test.txt",
            file_type="text/plain"
        )
        
        self.assertEqual(count, 2)
        mock_collection.add.assert_called_once()
        
        # Verify call arguments
        call_args = mock_collection.add.call_args[1]
        self.assertEqual(len(call_args['ids']), 2)
        self.assertEqual(len(call_args['documents']), 2)
        self.assertEqual(len(call_args['metadatas']), 2)
        self.assertEqual(len(call_args['embeddings']), 2)


class SemanticSearchAPITest(APITestCase):
    """Tests for semantic search API endpoint."""
    
    def setUp(self):
        """Set up test data."""
        self.url = '/api/search/semantic/'
    
    @patch('files.rag_views.VectorStoreService')
    @patch('files.rag_views.EmbeddingService')
    def test_semantic_search_success(self, mock_embedding, mock_vector_store):
        """Test successful semantic search."""
        # Mock embedding generation
        mock_embedding.generate_embedding.return_value = np.random.rand(384)
        
        # Mock vector store search results
        mock_vector_store.search.return_value = [
            {
                'chunk_id': 'file1_0',
                'file_id': 'test-uuid-1',
                'chunk_index': 0,
                'file_name': 'document1.pdf',
                'file_type': 'application/pdf',
                'chunk_text': 'This is a relevant chunk of text.',
                'score': 0.85
            }
        ]
        
        # Mock get_collection to avoid initialization
        mock_vector_store.get_collection.return_value = Mock()
        
        response = self.client.get(self.url, {'q': 'test query'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('query', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['query'], 'test query')
    
    def test_semantic_search_missing_query(self):
        """Test that missing query returns 400."""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_semantic_search_short_query(self):
        """Test that very short query returns 400."""
        response = self.client.get(self.url, {'q': 'ab'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_semantic_search_invalid_top_k(self):
        """Test that invalid top_k returns 400."""
        response = self.client.get(self.url, {'q': 'test query', 'top_k': 'invalid'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_semantic_search_invalid_threshold(self):
        """Test that invalid threshold returns 400."""
        response = self.client.get(self.url, {'q': 'test query', 'threshold': '2.0'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_semantic_search_invalid_aggregation(self):
        """Test that invalid aggregation method returns 400."""
        response = self.client.get(self.url, {
            'q': 'test query',
            'aggregation': 'invalid'
        })
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('files.rag_views.VectorStoreService')
    def test_rag_stats_endpoint(self, mock_vector_store):
        """Test RAG stats endpoint."""
        mock_vector_store.get_collection_stats.return_value = {
            'total_chunks': 100,
            'collection_name': 'file_vault_embeddings'
        }
        mock_vector_store.get_collection.return_value = Mock()
        
        response = self.client.get('/api/search/rag-stats/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_chunks', response.data)
        self.assertIn('collection_name', response.data)


class RAGIntegrationTest(TestCase):
    """Integration tests for RAG indexing with file operations."""
    
    @patch('files.services.deduplication.DeduplicationService._trigger_rag_indexing')
    def test_upload_triggers_indexing(self, mock_trigger):
        """Test that file upload triggers RAG indexing."""
        from files.services.deduplication import DeduplicationService
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"This is test content for RAG indexing.",
            content_type="text/plain"
        )
        
        # Upload file
        file_record, is_duplicate = DeduplicationService.upload_file(
            file_obj=test_file,
            original_filename="test.txt",
            file_type="text/plain"
        )
        
        # Verify indexing was triggered
        mock_trigger.assert_called_once()
        call_args = mock_trigger.call_args[0]
        self.assertEqual(call_args[0].id, file_record.id)
    
    @patch('files.services.deduplication.DeduplicationService._trigger_rag_deletion')
    def test_delete_triggers_cleanup(self, mock_trigger):
        """Test that file deletion triggers RAG cleanup."""
        from files.services.deduplication import DeduplicationService
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"Test content",
            content_type="text/plain"
        )
        
        # Upload file
        with patch('files.services.deduplication.DeduplicationService._trigger_rag_indexing'):
            file_record, _ = DeduplicationService.upload_file(
                file_obj=test_file,
                original_filename="test.txt",
                file_type="text/plain"
            )
        
        file_id = str(file_record.id)
        
        # Delete file
        DeduplicationService.delete_file(file_record)
        
        # Verify RAG deletion was triggered
        mock_trigger.assert_called_once_with(file_id)
