from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class CharacterLookInfo(BaseModel):
    look_id: str
    name: str
    image_url: str
    source_type: str = "upload"


class CharacterInfo(BaseModel):
    character_id: str
    name: str
    image_url: str
    voice: str = ""
    persona: str = ""
    source_type: str = "self_avatar"
    reference_images: list[str] = Field(default_factory=list)
    reference_count: int = 1
    looks: list[CharacterLookInfo] = Field(default_factory=list)
    look_count: int = 0


class JobInfo(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    output_url: Optional[str] = None
    error: Optional[str] = None
