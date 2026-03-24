from app.repositories.user_repository import UserRepository
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import UserInDB
from app.schemas.auth import UserSignup, UserLogin, Token, UserResponse
from app.core.exceptions import ValidationError, AuthenticationException

class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository
    def signup(self, user_data: UserSignup) -> UserResponse:
        existing_user = self.user_repository.find_by_email(user_data.email)
        if existing_user:
            raise ValidationError("Email already registered")
        user = UserInDB(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
        )
        created_user = self.user_repository.create_user(user)
        return UserResponse(
            id=str(created_user.id),
            first_name=created_user.first_name,
            last_name=created_user.last_name,
            email=created_user.email,
            created_at=created_user.created_at.isoformat(),
        )
    def login(self, credentials: UserLogin) -> Token:
        user = self.user_repository.find_by_email(credentials.email)
        if not user or not verify_password(credentials.password, user.hashed_password):
            raise AuthenticationException("Invalid email or password")
        access_token = create_access_token(
            data={"sub": user.email, "user_id": str(user.id)}
        )
        return Token(access_token=access_token)
