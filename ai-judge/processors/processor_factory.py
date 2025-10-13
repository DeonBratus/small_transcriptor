"""
Factory for creating file processors.
"""

from typing import Dict, Type, Any
from .base_processor import BaseFileProcessor
from .docx_processor import DocxProcessor
from .pptx_processor import PptxProcessor


class ProcessorFactory:
    """Factory class for creating file processors."""
    
    # Registry of supported file types and their processors
    _processors: Dict[str, Type[BaseFileProcessor]] = {
        '.docx': DocxProcessor,
        '.pptx': PptxProcessor,
    }
    
    @classmethod
    def create_processor(cls, file_path: str, file_type: str = None, **kwargs) -> BaseFileProcessor:
        """
        Create a processor for the given file.
        
        Args:
            file_path: Path to the file
            file_type: File type (if None, will be inferred from extension)
            **kwargs: Additional arguments for processor initialization
            
        Returns:
            Appropriate processor instance
            
        Raises:
            ValueError: If file type is not supported
        """
        if file_type is None:
            file_type = cls._get_file_extension(file_path)
        
        if file_type not in cls._processors:
            raise ValueError(f"Unsupported file type: {file_type}")
        
        processor_class = cls._processors[file_type]
        return processor_class(file_path, **kwargs)
    
    @classmethod
    def get_supported_types(cls) -> list:
        """
        Get list of supported file types.
        
        Returns:
            List of supported file extensions
        """
        return list(cls._processors.keys())
    
    @classmethod
    def register_processor(cls, file_type: str, processor_class: Type[BaseFileProcessor]):
        """
        Register a new processor for a file type.
        
        Args:
            file_type: File extension (e.g., '.pdf')
            processor_class: Processor class
        """
        cls._processors[file_type] = processor_class
    
    @staticmethod
    def _get_file_extension(file_path: str) -> str:
        """
        Extract file extension from path.
        
        Args:
            file_path: Path to file
            
        Returns:
            File extension in lowercase
        """
        return os.path.splitext(file_path)[1].lower()
    
    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        """
        Check if file type is supported.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file type is supported
        """
        file_type = cls._get_file_extension(file_path)
        return file_type in cls._processors


# Import os for the static method
import os
