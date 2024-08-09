from datetime import datetime
from typing import List

from pydantic.v1 import BaseModel, Field


class ERLocation(BaseModel):
    latitude: str
    longitude: str


class EREvent(BaseModel):
    id: str
    location: ERLocation = None
    time: datetime
    serial_number: int
    message: str = None
    provenance: str = None
    event_type: str
    priority: int
    priority_label: str
    title: str = None
    state: str = None
    event_details: dict = Field(default_factory=dict)
    patrol_segments: List[str] = Field(default_factory=list)
    updated_at: datetime
    created_at: datetime
    event_category: str
