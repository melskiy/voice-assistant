"""
Domain value objects for voice assistant.

Value objects are immutable and identified by their attributes.
"""

from .audio_chunk import AudioChunk
from .confidence import ConfidenceScore
from .phone_number import PhoneNumber
from .priority import Priority
from .audio_segment import AudioSegment
from .dialog_response import DialogResponse

__all__ = [
    'AudioChunk',
    'ConfidenceScore',
    'PhoneNumber',
    'Priority',
    'AudioSegment',
    'DialogResponse',
]
