from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.settings import settings

# Initialize the hasher once
# Argon2id is the default, which provides the best protection against
# both side-channel attacks and GPU cracking.
ph = PasswordHasher()


# Password Hasher/Verifier
def hash_password(password: str) -> str:
    """Hashes a plantext password usingg Argon2id."""
    return ph.hash(password)


def verify_password(plaintext_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against the stored Argon2 hash."""
    try:
        # * ph.verify returns True if it matches, raises exception if it doesn't
        ph.verify(hashed_password, plaintext_password)
        return True
    except VerificationError:
        return False
    except Exception:
        #! Catch any other argon2 exceptions (ex: invalid hash format)
        return False


# JWT Setup
def create_access_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),  # User ID
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload, settings.jwt.private_key, algorithm=settings.jwt.algorithm
    )


def create_refresh_token(subject: str | int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=7)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(
        payload, settings.jwt.private_key, algorithm=settings.jwt.algorithm
    )
