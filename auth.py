from fastapi import HTTPException, status, Cookie, Header, Depends
from typing import Optional
from sqlalchemy.orm import Session
from database import get_db
import crud, models

SESSION_COOKIE_NAME = "dakshina_admin_session"
SESSION_TOKEN = "secure_admin_access_token"


def verify_admin_credentials(username: str, password: str, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, username, password)
    return user is not None


def get_current_admin(session_token: Optional[str] = Cookie(None), authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    token = session_token
    if not token and authorization:
        # Check if it's Bearer token
        if authorization.startswith("Bearer "):
            token = authorization[7:]
    print(f"Checking admin session: cookie='{session_token}', header='{authorization}', token='{token}'")
    if token != SESSION_TOKEN:
        print("Session invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized. Admin login required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    print("Session valid")
    return True
