from typing import Annotated, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form
from app.dependencies.auth import get_current_user
from app.dependencies.services import get_feedback_service
from app.services.feedback_service import FeedbackService
from app.models.user import UserInDB
from app.schemas.feedback import ChatRequest, QuickSentimentRequest, SentimentResponse, AnalysisResponse

router = APIRouter(prefix="/analyze", tags=["Feedback Analysis"])

@router.post("/chat", response_model=AnalysisResponse)
async def chat_analyze(
    request: ChatRequest,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    result = await feedback_service.process_message(
        user_id=str(current_user.id),
        message=request.message,
        conversation_id=request.conversation_id,
    )
    return result

@router.post("/upload")
async def upload_csv(
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
    file: UploadFile = File(...),
    conversation_id: Optional[str] = Form(None),
):
    content = await file.read()
    return await feedback_service.process_csv_content(
        user_id=str(current_user.id),
        content=content,
        filename=file.filename,
        conversation_id=conversation_id,
    )

@router.get("/quick-sentiment")
async def quick_sentiment(
    text: str,
    current_user: Annotated[UserInDB, Depends(get_current_user)],
    feedback_service: Annotated[FeedbackService, Depends(get_feedback_service)],
):
    return feedback_service.get_quick_sentiment(text)
