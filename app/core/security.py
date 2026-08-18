import jwt
from app.core.settings import settings
#! TODO: its example
def create_access_token(data: dict) -> str:
    # settings.jwt.private_key reads the .pem file automatically
    return jwt.encode(data, settings.jwt.private_key, algorithm=settings.jwt.algorithm)