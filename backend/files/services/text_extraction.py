"""
Text extraction service for RAG semantic search.

Extracts text content from supported file types:
- Plain text files: .txt, .md, .csv, .json, .xml
- PDF documents: .pdf (using PyPDF2 and pdfplumber as fallback)
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import chardet

try:
    import PyPDF2
    import pdfplumber
except ImportError:
    PyPDF2 = None
    pdfplumber = None

logger = logging.getLogger(__name__)


class TextExtractionService:
    """Service for extracting text from various file types."""
    
    # Supported file extensions for text extraction
    SUPPORTED_TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.xml'}
    SUPPORTED_PDF_EXTENSIONS = {'.pdf'}
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        Check if a file type is supported for text extraction.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file type is supported, False otherwise
        """
        ext = Path(file_path).suffix.lower()
        return ext in cls.SUPPORTED_TEXT_EXTENSIONS or ext in cls.SUPPORTED_PDF_EXTENSIONS
    
    @classmethod
    def extract_text(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text content from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (extracted_text, error_message)
            - If successful: (text, None)
            - If failed: (None, error_message)
        """
        ext = Path(file_path).suffix.lower()
        
        try:
            if ext in cls.SUPPORTED_TEXT_EXTENSIONS:
                return cls._extract_text_file(file_path)
            elif ext in cls.SUPPORTED_PDF_EXTENSIONS:
                return cls._extract_pdf_file(file_path)
            else:
                return None, f"Unsupported file extension: {ext}"
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {str(e)}")
            return None, str(e)
    
    @classmethod
    def _extract_text_file(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from plain text files with encoding detection.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Tuple of (text, error_message)
        """
        try:
            # Try UTF-8 first (most common)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return text, None
            except UnicodeDecodeError:
                # Fallback: detect encoding
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8')
                confidence = detected.get('confidence', 0)
                
                if confidence < 0.7:
                    logger.warning(
                        f"Low encoding confidence ({confidence:.2f}) for {file_path}, "
                        f"detected: {encoding}"
                    )
                
                text = raw_data.decode(encoding, errors='replace')
                return text, None
                
        except Exception as e:
            logger.error(f"Failed to read text file {file_path}: {str(e)}")
            return None, f"Failed to read file: {str(e)}"
    
    @classmethod
    def _extract_pdf_file(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract text from PDF files using PyPDF2, with pdfplumber as fallback.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (text, error_message)
        """
        if PyPDF2 is None or pdfplumber is None:
            return None, "PDF extraction libraries not installed"
        
        # Try PyPDF2 first (faster)
        text = cls._extract_pdf_pypdf2(file_path)
        if text and len(text.strip()) > 50:  # Minimum threshold
            return text, None
        
        # Fallback to pdfplumber (better for complex PDFs)
        logger.info(f"PyPDF2 extraction insufficient for {file_path}, trying pdfplumber")
        text = cls._extract_pdf_pdfplumber(file_path)
        if text and len(text.strip()) > 0:
            return text, None
        
        # Both methods failed or returned empty content
        if text is not None and len(text.strip()) == 0:
            logger.warning(f"PDF {file_path} appears to have no extractable text (may be image-only)")
            return None, "PDF contains no extractable text (may be image-only)"
        
        return None, "Failed to extract text from PDF"
    
    @classmethod
    def _extract_pdf_pypdf2(cls, file_path: str) -> Optional[str]:
        """
        Extract text using PyPDF2.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                
                # Check if PDF is encrypted
                if reader.is_encrypted:
                    logger.warning(f"PDF {file_path} is encrypted, skipping")
                    return None
                
                text_parts = []
                for page_num in range(len(reader.pages)):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num} from {file_path}: {str(e)}")
                        continue
                
                return '\n\n'.join(text_parts) if text_parts else None
                
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed for {file_path}: {str(e)}")
            return None
    
    @classmethod
    def _extract_pdf_pdfplumber(cls, file_path: str) -> Optional[str]:
        """
        Extract text using pdfplumber (better for complex layouts).
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text or None if failed
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                text_parts = []
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)
                    except Exception as e:
                        logger.warning(
                            f"Failed to extract page {page_num} from {file_path} "
                            f"with pdfplumber: {str(e)}"
                        )
                        continue
                
                return '\n\n'.join(text_parts) if text_parts else None
                
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed for {file_path}: {str(e)}")
            return None
    
    @classmethod
    def get_supported_extensions(cls) -> set:
        """
        Get all supported file extensions.
        
        Returns:
            Set of supported extensions (e.g., {'.txt', '.pdf'})
        """
        return cls.SUPPORTED_TEXT_EXTENSIONS | cls.SUPPORTED_PDF_EXTENSIONS
