"""
Base class for file processors.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseFileProcessor(ABC):
    """Abstract base class for file processors."""
    
    def __init__(self, file_path: str):
        """
        Initialize processor with file path.
        
        Args:
            file_path: Path to the file to process
        """
        self.file_path = file_path
        self.processed_content = None
    
    @abstractmethod
    def process(self) -> str:
        """
        Process the file and return extracted content.
        
        Returns:
            Extracted text content from the file
        """
        pass
    
    @abstractmethod
    def validate_file(self) -> bool:
        """
        Validate that the file exists and is of correct type.
        
        Returns:
            True if file is valid, False otherwise
        """
        pass
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the processed file.
        
        Returns:
            Dictionary with file metadata
        """
        return {
            'file_path': self.file_path,
            'file_type': self.__class__.__name__.replace('Processor', '').lower(),
            'processed': self.processed_content is not None
        }
