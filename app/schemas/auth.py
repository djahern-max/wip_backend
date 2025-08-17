# ===== backend/app/schemas/auth.py =====
from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str  # Can be username or email
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str = None