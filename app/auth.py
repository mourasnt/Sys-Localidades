from dotenv import load_dotenv
import os
import base64
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from typing import List

load_dotenv()

ALGORITHM = os.getenv("JWT_ALGORITHM", "RS256")
bearer_scheme = HTTPBearer()

def _load_public_key():
    key_b64 = os.getenv("RSA_PUBLIC_KEY")
    if key_b64:
        return base64.b64decode(key_b64).decode('utf-8')

    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "certs", "public_key.pem")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return f.read()
    raise RuntimeError("RSA public key not found. Set RSA_PUBLIC_KEY or place certs/public_key.pem")


PUBLIC_KEY = _load_public_key()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    logger = logging.getLogger(__name__)
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")

        if username is None:
            raise credentials_exception

        return {"username": username, "role": role, "payload": payload}

    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        raise credentials_exception

def require_roles(*allowed_roles: str):
    """Dependency factory to require specific roles. Usage: require_roles("admin", "moderator")"""
    async def check_role(current_user: dict = Depends(get_current_user)):
        # Normalizar role removendo prefixo 'role_' se existir
        user_role = current_user["role"]
        normalized_role = user_role.replace("role_", "") if user_role.startswith("role_") else user_role
        
        if normalized_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{normalized_role}' is not permitted. Allowed roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return check_role