import abc
from enum import Enum
from typing import List, Optional, Dict, Any
from typing import TypeVar
from typing import Union
from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field

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
    event_details: dict = {}
    patrol_segments: List[str] = []
    updated_at: datetime
    created_at: datetime
    event_category: str

