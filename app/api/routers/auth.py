from typing import Annotated
from fastapi import APIRouter, Depends, status
from app.schemas.auth import UserSignup, UserLogin, Token, UserResponse
from app.services.auth_service import AuthService
from app.api.dependencies.services import get_auth_service
from app.api.dependencies.auth import get_current_user
from app.models.user import UserInDB

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def signup(
    user_data: UserSignup,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    return auth_service.signup(user_data)


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
):
    return auth_service.login(credentials)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: Annotated[UserInDB, Depends(get_current_user)]):
    return UserResponse(
        id=str(current_user.id),
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        email=current_user.email,
        created_at=current_user.created_at.isoformat(),
    )
