from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    """Raised when a resource is not found in the db."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictError(HTTPException):
    """Raised when a request conflicts with the current state of the db."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


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
