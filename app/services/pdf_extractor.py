"""
PDF and Document Text Extraction Service
Extracts actual text content from uploaded PDF and DOC files
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdfminer.high_level import extract_text as pdfminer_extract
    from pdfminer.layout import LAParams
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentTextExtractor:
    """Extract text from PDF and DOCX files"""
    
    def __init__(self):
        self.available_methods = []
        if PYMUPDF_AVAILABLE:
            self.available_methods.append('pymupdf')
        if PDFMINER_AVAILABLE:
            self.available_methods.append('pdfminer')
        if DOCX_AVAILABLE:
            self.available_methods.append('docx')
        
        logger.info(f"Available extraction methods: {self.available_methods}")
    
    def extract_pdf_text_pymupdf(self, file_path: str) -> str:
        """Extract text using PyMuPDF (fastest and most reliable)"""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text.strip()
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return ""
    
    def extract_pdf_text_pdfminer(self, file_path: str) -> str:
        """Extract text using PDFMiner (backup method)"""
        try:
            # Configure layout parameters for better text extraction
            laparams = LAParams(
                line_margin=0.5,
                word_margin=0.1,
                char_margin=2.0,
                boxes_flow=0.5,
                all_texts=False
            )
            text = pdfminer_extract(file_path, laparams=laparams)
            return text.strip()
        except Exception as e:
            logger.error(f"PDFMiner extraction failed: {e}")
            return ""
    
    def extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX files"""
        try:
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            return ""
    
    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from PDF, DOC, or DOCX files
        Returns cleaned, readable text or empty string if extraction fails
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return ""
        
        file_ext = Path(file_path).suffix.lower()
        text = ""
        
        if file_ext == '.pdf':
            # Try PyMuPDF first (fastest and most reliable)
            if 'pymupdf' in self.available_methods:
                text = self.extract_pdf_text_pymupdf(file_path)
                if text:
                    logger.info(f"Successfully extracted {len(text)} characters using PyMuPDF")
                else:
                    logger.warning("PyMuPDF extraction returned empty text")
            
            # Fallback to PDFMiner if PyMuPDF failed
            if not text and 'pdfminer' in self.available_methods:
                logger.info("Trying PDFMiner as backup...")
                text = self.extract_pdf_text_pdfminer(file_path)
                if text:
                    logger.info(f"Successfully extracted {len(text)} characters using PDFMiner")
        
        elif file_ext in ['.docx', '.doc']:
            if 'docx' in self.available_methods:
                text = self.extract_docx_text(file_path)
                if text:
                    logger.info(f"Successfully extracted {len(text)} characters from DOCX")
        
        else:
            logger.warning(f"Unsupported file type: {file_ext}")
            return ""
        
        if not text:
            logger.error(f"Failed to extract text from {file_path}")
            return ""
        
        # Clean and normalize the text
        cleaned_text = self.clean_extracted_text(text)
        logger.info(f"Final cleaned text length: {len(cleaned_text)} characters")
        
        return cleaned_text
    
    def clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                cleaned_lines.append(line)
        
        # Join with single newlines and limit length
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Limit text length to prevent overwhelming the AI
        if len(cleaned_text) > 8000:
            cleaned_text = cleaned_text[:8000] + "... [text truncated]"
        
        return cleaned_text
    
    def extract_key_sections(self, text: str) -> dict:
        """
        Extract key resume sections like experience, education, skills
        Returns a dictionary with identified sections
        """
        sections = {
            'experience': [],
            'education': [],
            'skills': [],
            'contact': [],
            'summary': []
        }
        
        if not text:
            return sections
        
        text_lower = text.lower()
        lines = text.split('\n')
        
        # Common section headers
        experience_headers = ['experience', 'work experience', 'employment', 'professional experience', 'career history']
        education_headers = ['education', 'educational background', 'academic background', 'qualifications']
        skills_headers = ['skills', 'technical skills', 'core competencies', 'technologies', 'expertise']
        
        current_section = None
        section_content = []
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Check if this line is a section header
            if any(header in line_lower for header in experience_headers):
                if current_section and section_content:
                    sections[current_section].extend(section_content)
                current_section = 'experience'
                section_content = []
            elif any(header in line_lower for header in education_headers):
                if current_section and section_content:
                    sections[current_section].extend(section_content)
                current_section = 'education'
                section_content = []
            elif any(header in line_lower for header in skills_headers):
                if current_section and section_content:
                    sections[current_section].extend(section_content)
                current_section = 'skills'
                section_content = []
            elif line.strip():
                if current_section:
                    section_content.append(line.strip())
                else:
                    # Content before any section headers (likely summary/contact)
                    if '@' in line or 'phone' in line_lower or 'email' in line_lower:
                        sections['contact'].append(line.strip())
                    else:
                        sections['summary'].append(line.strip())
        
        # Add the last section content
        if current_section and section_content:
            sections[current_section].extend(section_content)
        
        return sections

# Global instance
_extractor = None

def get_text_extractor() -> DocumentTextExtractor:
    """Get singleton text extractor instance"""
    global _extractor
    if _extractor is None:
        _extractor = DocumentTextExtractor()
    return _extractor

def extract_resume_text(file_path: str) -> str:
    """Convenience function to extract text from resume file"""
    extractor = get_text_extractor()
    return extractor.extract_text_from_file(file_path)

def analyze_resume_sections(file_path: str) -> dict:
    """Extract and analyze key resume sections"""
    extractor = get_text_extractor()
    text = extractor.extract_text_from_file(file_path)
    return extractor.extract_key_sections(text)