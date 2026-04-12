from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Task sentence to parse.")


class ParseResponse(BaseModel):
    raw_text: str
    cleaned_text: str
    task: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    person: List[str] = Field(default_factory=list)
    location: List[str] = Field(default_factory=list)
    command: Optional[str] = None
    priority: str = "Normal"
    category: Optional[str] = None
    parser_backend: str
    confidence: float = Field(ge=0.0, le=1.0)
    warnings: List[str] = Field(default_factory=list)
    ambiguities: List[str] = Field(default_factory=list)
