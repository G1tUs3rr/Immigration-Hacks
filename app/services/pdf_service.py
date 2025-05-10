import PyPDF2
from typing import Dict, List, Optional, Union
import logging
from pathlib import Path
import io

class PDFService:
    def __init__(self):
        """Initialize the PDF service with logging configuration."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def read_pdf(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Read a PDF file and extract its content and metadata.
        
        Args:
            pdf_path (Union[str, Path]): Path to the PDF file
            
        Returns:
            Dict: Dictionary containing PDF content and metadata
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                # Create PDF reader object
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract metadata
                metadata = pdf_reader.metadata
                
                # Extract text from all pages
                text_content = []
                for page in pdf_reader.pages:
                    text_content.append(page.extract_text())
                
                return {
                    'metadata': metadata,
                    'text_content': text_content,
                    'num_pages': len(pdf_reader.pages),
                    'file_name': pdf_path.name
                }
                
        except Exception as e:
            self.logger.error(f"Error reading PDF {pdf_path}: {str(e)}")
            raise

    def read_pdf_from_bytes(self, pdf_bytes: bytes) -> Dict:
        """
        Read a PDF from bytes (useful for PDFs received via API or network).
        
        Args:
            pdf_bytes (bytes): PDF file content as bytes
            
        Returns:
            Dict: Dictionary containing PDF content and metadata
        """
        try:
            # Create PDF reader object from bytes
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            # Extract metadata
            metadata = pdf_reader.metadata
            
            # Extract text from all pages
            text_content = []
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            return {
                'metadata': metadata,
                'text_content': text_content,
                'num_pages': len(pdf_reader.pages)
            }
            
        except Exception as e:
            self.logger.error(f"Error reading PDF from bytes: {str(e)}")
            raise

    def extract_text_by_page(self, pdf_path: Union[str, Path], page_numbers: Optional[List[int]] = None) -> Dict[int, str]:
        """
        Extract text from specific pages of a PDF.
        
        Args:
            pdf_path (Union[str, Path]): Path to the PDF file
            page_numbers (Optional[List[int]]): List of page numbers to extract (0-based). If None, extracts all pages.
            
        Returns:
            Dict[int, str]: Dictionary mapping page numbers to their text content
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                # Validate page numbers
                if page_numbers is not None:
                    if not all(0 <= page < total_pages for page in page_numbers):
                        raise ValueError(f"Page numbers must be between 0 and {total_pages - 1}")
                else:
                    page_numbers = range(total_pages)
                
                # Extract text from specified pages
                page_texts = {}
                for page_num in page_numbers:
                    page = pdf_reader.pages[page_num]
                    page_texts[page_num] = page.extract_text()
                
                return page_texts
                
        except Exception as e:
            self.logger.error(f"Error extracting text from PDF {pdf_path}: {str(e)}")
            raise

    def get_pdf_metadata(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Extract metadata from a PDF file.
        
        Args:
            pdf_path (Union[str, Path]): Path to the PDF file
            
        Returns:
            Dict: PDF metadata including title, author, subject, etc.
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata
                
                # Convert metadata to a more accessible format
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'modification_date': metadata.get('/ModDate', '')
                }
                
        except Exception as e:
            self.logger.error(f"Error extracting metadata from PDF {pdf_path}: {str(e)}")
            raise

    def get_pdf_info(self, pdf_path: Union[str, Path]) -> Dict:
        """
        Get basic information about a PDF file.
        
        Args:
            pdf_path (Union[str, Path]): Path to the PDF file
            
        Returns:
            Dict: Basic PDF information including number of pages, file size, etc.
        """
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                raise FileNotFoundError(f"PDF file not found: {pdf_path}")

            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                return {
                    'file_name': pdf_path.name,
                    'file_size': pdf_path.stat().st_size,
                    'num_pages': len(pdf_reader.pages),
                    'is_encrypted': pdf_reader.is_encrypted,
                    'file_path': str(pdf_path.absolute())
                }
                
        except Exception as e:
            self.logger.error(f"Error getting PDF info for {pdf_path}: {str(e)}")
            raise 