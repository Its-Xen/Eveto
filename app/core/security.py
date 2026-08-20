from typing import Any

import jwt

from app.core.settings import settings


#! TODO: its example
def create_access_token(data: dict[str, Any]) -> str:
    token = jwt.encode(data, settings.jwt.private_key, algorithm=settings.jwt.algorithm)
    return token
