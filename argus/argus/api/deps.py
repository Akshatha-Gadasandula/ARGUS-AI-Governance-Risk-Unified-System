"""
Dependency injection for FastAPI routes.
Provides database sessions and authentication.
"""
import logging
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from argus.config import settings
from argus.db.database import get_session as get_db_session

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


async def get_session() -> AsyncGenerator:
    """
    Dependency providing database session for each request.
    
    Yields:
        AsyncSession for database operations
    """
    async for session in get_db_session():
        yield session


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
 ) -> dict:
    """
    Dependency for authentication.
    Extracts and validates JWT token.
    
    Args:
        credentials: HTTP Bearer token if provided
        
    Returns:
        Dictionary with username and role
    """
    # For development: allow anonymous access
    if not credentials:
        return {"username": "dev_user", "role": "admin"}

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return {
        "username": username,
        "role": payload.get("role", "user"),
    }
