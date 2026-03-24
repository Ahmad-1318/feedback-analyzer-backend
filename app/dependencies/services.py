from app.core.database import get_database
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.user_repository import UserRepository
from app.services.feedback_service import FeedbackService
from app.services.analytics_service import AnalyticsService
from app.services.auth_service import AuthService

_feedback_repo: FeedbackRepository = None
_user_repo: UserRepository = None
_feedback_service: FeedbackService = None
_analytics_service: AnalyticsService = None
_auth_service: AuthService = None


def get_feedback_repository() -> FeedbackRepository:
    global _feedback_repo
    if _feedback_repo is None:
        db = get_database()
        _feedback_repo = FeedbackRepository(db)
    return _feedback_repo


def get_user_repository() -> UserRepository:
    global _user_repo
    if _user_repo is None:
        db = get_database()
        _user_repo = UserRepository(db)
    return _user_repo

def get_feedback_service() -> FeedbackService:
    global _feedback_service
    if _feedback_service is None:
        feedback_repo = get_feedback_repository()
        _feedback_service = FeedbackService(feedback_repo)
    return _feedback_service


def get_analytics_service() -> AnalyticsService:
    global _analytics_service
    if _analytics_service is None:
        feedback_repo = get_feedback_repository()
        _analytics_service = AnalyticsService(feedback_repo)
    return _analytics_service


def get_auth_service() -> AuthService:
    global _auth_service
    if _auth_service is None:
        user_repo = get_user_repository()
        _auth_service = AuthService(user_repo)
    return _auth_service


