from typing import Any, Dict, Optional
from fastapi import status


class AppException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail
        self.errors = errors


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found", detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class ValidationError(AppException):
    def __init__(
        self,
        message: str = "Validation failed",
        detail: Optional[str] = None,
        errors: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            errors=errors,
        )


class ServiceException(AppException):
    def __init__(self, message: str = "Internal service error", detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed", detail: Optional[str] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )
