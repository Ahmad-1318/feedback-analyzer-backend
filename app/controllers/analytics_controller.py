from typing import Annotated
from fastapi import APIRouter, Depends
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_analytics_service, get_feedback_service
from app.services.analytics_service import AnalyticsService
from app.services.feedback_service import FeedbackService
from app.models.user import UserInDB

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary")
def get_analytics_summary(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
):
    user_id = str(current_user.id)
    return analytics_service.get_analytics_summary(user_id)


@router.get("/history")
def get_analytics_history(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    limit: int = 10,
):
    user_id = str(current_user.id)
    return analytics_service.get_historical_analytics(user_id, limit=limit)


@router.get("/themes")
def get_theme_breakdown(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
):
    user_id = str(current_user.id)
    return analytics_service.get_theme_breakdown(user_id)


@router.get("/recommendations")
def get_recommendations(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    analytics_service: Annotated[AnalyticsService, Depends(get_analytics_service)],
):
    user_id = str(current_user.id)
    return analytics_service.get_recommendations(user_id)


@router.get("/stats")
def get_user_stats(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    user_id = str(current_user.id)
    return feedback_service.get_user_stats(user_id)
