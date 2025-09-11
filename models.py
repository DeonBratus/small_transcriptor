from pydantic import BaseModel
from typing import List


class TranscriptionRequest(BaseModel):
    num_speakers: int = 4
    use_gpu: bool = True

class TranscriptionSegment(BaseModel):
    speaker: str
    text: str
    start: float
    end: float

class TranscriptionResponse(BaseModel):
    segments: List[TranscriptionSegment]
    processing_time: float
    gpu_used: bool