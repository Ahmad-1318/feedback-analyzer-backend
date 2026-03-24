from pydantic import BaseModel, EmailStr

class UserSignup(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
