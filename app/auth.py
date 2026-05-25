from dotenv import load_dotenv
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    raise RuntimeError("API_TOKEN environment variable is not set")

x_token_header = APIKeyHeader(name="x-token", auto_error=False)

async def get_current_user(token: str = Depends(x_token_header)):
    if token is None or token != API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing x-token",
        )
    return {"authenticated": True, "token": token}
