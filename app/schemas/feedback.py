from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class QuickSentimentRequest(BaseModel):
    text: str

class SentimentResponse(BaseModel):
    text: str
    sentiment: str
    confidence: float

class AnalysisResponse(BaseModel):
    conversation_id: str
    response: str
    analysis: Optional[Dict[str, Any]] = None
    is_question: bool = False
