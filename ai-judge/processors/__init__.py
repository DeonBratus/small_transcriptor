"""
Processors module for file handling in AI Judge system.
"""

from .base_processor import BaseFileProcessor
from .docx_processor import DocxProcessor
from .pptx_processor import PptxProcessor
from .processor_factory import ProcessorFactory

__all__ = [
    'BaseFileProcessor',
    'DocxProcessor', 
    'PptxProcessor',
    'ProcessorFactory'
]
