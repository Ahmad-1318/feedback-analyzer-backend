from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime, timezone


class ThemeAnalysis(BaseModel):
    theme: str = Field()
    count: int = Field()
    sentiment: str = Field()
    examples: List[str] = Field(default_factory=list)
    percentage: float = Field(default=0.0)
    satisfaction: int = Field(default=50)


class FeatureSuggestion(BaseModel):
    feature: str = Field()
    priority: str = Field()
    reasoning: str = Field()
    affected_users: int = Field(default=0)
    impact_score: float = Field(default=5.0, ge=0.0, le=10.0)


class SentimentDistribution(BaseModel):
    positive: int = Field(ge=0, default=0)
    neutral: int = Field(ge=0, default=0)
    negative: int = Field(ge=0, default=0)
    mixed: int = Field(ge=0, default=0)

    @property
    def total(self) -> int:
        return self.positive + self.neutral + self.negative + self.mixed

    @property
    def positive_percentage(self) -> float:
        return (self.positive / self.total * 100) if self.total > 0 else 0

    @property
    def negative_percentage(self) -> float:
        return (self.negative / self.total * 100) if self.total > 0 else 0


class FeedbackAnalysis(BaseModel):
    total_feedbacks_analyzed: int = Field(ge=0, default=0)
    overall_sentiment: str = Field()
    satisfaction_index: float = Field(ge=0.0, le=1.0)
    sentiment_distribution: SentimentDistribution
    total_themes_detected: int = Field(ge=0, default=0)
    themes: List[ThemeAnalysis] = Field(default_factory=list)
    key_features_count: int = Field(ge=0, default=0)
    feature_suggestions: List[FeatureSuggestion] = Field(default_factory=list)
    chat_response: str = Field()
    is_question_response: bool = Field(default=False)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuestionResponse(BaseModel):
    answer: str = Field()
    supporting_data: Optional[Dict] = Field(default=None)
    is_question: bool = Field(default=True)


class FeedbackDocument(BaseModel):
    user_id: str = Field()
    conversation_id: Optional[str] = Field(default=None)
    content: str = Field()
    sentiment: str = Field(default="neutral")
    sentiment_score: float = Field(default=0.5)
    themes: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class AnalysisDocument(BaseModel):
    user_id: str = Field()
    conversation_id: Optional[str] = Field(default=None)
    analysis: Dict = Field()
    feedback_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
