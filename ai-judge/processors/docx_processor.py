"""
DOCX file processor.
"""

import os
import docx
from typing import List
from .base_processor import BaseFileProcessor


class DocxProcessor(BaseFileProcessor):
    """Processor for DOCX files."""
    
    def validate_file(self) -> bool:
        """Validate DOCX file."""
        if not os.path.isfile(self.file_path):
            return False
        
        # Check file extension
        if not self.file_path.lower().endswith('.docx'):
            return False
            
        return True
    
    def process(self) -> str:
        """
        Extract text from DOCX file.
        
        Returns:
            Extracted text content
        """
        if not self.validate_file():
            raise FileNotFoundError(f"DOCX file not found or invalid: {self.file_path}")
        
        try:
            doc = docx.Document(self.file_path)
            # Extract text from all paragraphs
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            self.processed_content = "\n".join(paragraphs)
            return self.processed_content
        except Exception as e:
            raise ValueError(f"Error reading DOCX file '{self.file_path}': {e}")
    
    def get_paragraphs(self) -> List[str]:
        """
        Get list of paragraphs from the document.
        
        Returns:
            List of paragraph texts
        """
        if self.processed_content is None:
            self.process()
        
        return [p.strip() for p in self.processed_content.split('\n') if p.strip()]
    
    def get_metadata(self) -> dict:
        """Get extended metadata for DOCX files."""
        metadata = super().get_metadata()
        
        if self.processed_content:
            paragraphs = self.get_paragraphs()
            metadata.update({
                'paragraph_count': len(paragraphs),
                'word_count': len(self.processed_content.split()),
                'character_count': len(self.processed_content)
            })
        
        return metadata
