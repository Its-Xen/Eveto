from fastapi import HTTPException, status


def get_credentials_exception() -> HTTPException:
    """Returns the standard 401 Unauthorized exception for bad tokens."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_forbidden_exception(required_role: str) -> HTTPException:
    """Returns the standard 403 Forbidden exception for bad roles."""
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Access forbidden. Requires {required_role} role.",
    )
