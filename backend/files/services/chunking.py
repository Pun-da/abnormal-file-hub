"""
Text chunking service for RAG semantic search.

Splits text into manageable chunks with overlap for better context preservation.
Uses token-aware chunking with sentence boundary detection.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class ChunkingService:
    """Service for chunking text into segments suitable for embedding."""
    
    # Default chunking parameters (per rag_search.md)
    DEFAULT_CHUNK_SIZE = 500  # tokens
    DEFAULT_OVERLAP = 50      # tokens
    MIN_CHUNK_SIZE = 50       # tokens
    
    # Approximate tokens per character (rough estimate for English)
    # More accurate would be using tiktoken, but this is simpler
    CHARS_PER_TOKEN = 4
    
    @classmethod
    def chunk_text(
        cls,
        text: str,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        overlap: int = DEFAULT_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE
    ) -> List[Tuple[str, int]]:
        """
        Split text into chunks with overlap, respecting sentence boundaries.
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size in tokens
            overlap: Overlap size in tokens
            min_chunk_size: Minimum chunk size in tokens
            
        Returns:
            List of tuples: (chunk_text, chunk_index)
        """
        if not text or not text.strip():
            return []
        
        # Convert token counts to character counts
        chunk_chars = chunk_size * cls.CHARS_PER_TOKEN
        overlap_chars = overlap * cls.CHARS_PER_TOKEN
        min_chars = min_chunk_size * cls.CHARS_PER_TOKEN
        
        # Split into sentences for better boundaries
        sentences = cls._split_into_sentences(text)
        
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence_length = len(sentence)
            
            # If adding this sentence exceeds chunk size
            if current_length > 0 and current_length + sentence_length > chunk_chars:
                # Save current chunk
                chunk_text = ' '.join(current_chunk).strip()
                if len(chunk_text) >= min_chars:
                    chunks.append((chunk_text, chunk_index))
                    chunk_index += 1
                
                # Start new chunk with overlap
                # Keep last few sentences for overlap
                overlap_text = []
                overlap_length = 0
                for s in reversed(current_chunk):
                    if overlap_length + len(s) <= overlap_chars:
                        overlap_text.insert(0, s)
                        overlap_length += len(s)
                    else:
                        break
                
                current_chunk = overlap_text
                current_length = overlap_length
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_length
        
        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            if len(chunk_text) >= min_chars:
                chunks.append((chunk_text, chunk_index))
        
        logger.info(f"Chunked text into {len(chunks)} segments")
        return chunks
    
    @classmethod
    def _split_into_sentences(cls, text: str) -> List[str]:
        """
        Split text into sentences using simple heuristics.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split on sentence boundaries
        # This is a simple approach; more sophisticated methods exist
        sentence_endings = re.compile(r'([.!?]+[\s\n]+)')
        
        sentences = []
        last_end = 0
        
        for match in sentence_endings.finditer(text):
            end_pos = match.end()
            sentence = text[last_end:end_pos].strip()
            if sentence:
                sentences.append(sentence)
            last_end = end_pos
        
        # Add remaining text
        if last_end < len(text):
            remaining = text[last_end:].strip()
            if remaining:
                sentences.append(remaining)
        
        # If no sentences found, treat entire text as one sentence
        if not sentences:
            sentences = [text]
        
        return sentences
    
    @classmethod
    def estimate_token_count(cls, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // cls.CHARS_PER_TOKEN
