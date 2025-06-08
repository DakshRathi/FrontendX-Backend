# app/models.py
from pydantic import BaseModel
from typing import List, Literal

class AnalysisRequest(BaseModel):
    url: str
    strategy: Literal["mobile", "desktop"] = "desktop"

class Metric(BaseModel):
    title: str
    value: str

class AnalysisResponse(BaseModel):
    performance_score: int
    metrics: List[Metric]
    initial_suggestion: str

class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]
