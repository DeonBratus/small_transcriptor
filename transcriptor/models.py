from pydantic import BaseModel
from typing import List, Optional


class TranscriptionRequest(BaseModel):
    num_speakers: int = 4
    use_multithreading: bool = True
    chunk_duration: float = 30.0
    max_workers: Optional[int] = None

class TranscriptionSegment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float

class TranscriptionResponse(BaseModel):
    segments: List[TranscriptionSegment]
    processing_time: float
    multithreading_used: bool
    threads_count: int