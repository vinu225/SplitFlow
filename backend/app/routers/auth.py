"""
Authentication & Multi-Tenant Creator Router.
Provides secure expiring session tokens with role-based access control.
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Creator, UserSession
from app.schemas import CreatorCreate, CreatorResponse, SessionResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
security = HTTPBearer()

def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> UserSession:
    """Dependency verifying the cryptographic session token."""
    token = credentials.credentials
    user_session = db.query(UserSession).filter_by(id=token).first()
    if not user_session or user_session.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or is invalid. Please authenticate."
        )
    return user_session

def require_role(allowed_roles: list[str]):
    """Role-based authorization guard."""
    def dependency(session: UserSession = Depends(get_current_session)):
        if session.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of roles: {allowed_roles}"
            )
        return session
    return dependency

@router.post("/register", response_model=CreatorResponse)
def register_creator(data: CreatorCreate, db: Session = Depends(get_db)):
    """Registers a new creator tenant."""
    existing = db.query(Creator).filter_by(email=data.email).first()
    if existing:
        return existing

    creator = Creator(
        business_name=data.business_name,
        email=data.email,
        paypal_merchant_id=data.paypal_merchant_id
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return creator

@router.post("/session", response_model=SessionResponse)
def create_session(creator_id: int, role: str = "CREATOR_OWNER", db: Session = Depends(get_db)):
    """Creates a signed, expiring user session (valid for 24 hours)."""
    creator = db.query(Creator).filter_by(id=creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    session_token = f"sess_{uuid.uuid4().hex}"
    expires_at = datetime.utcnow() + timedelta(hours=24)

    user_session = UserSession(
        id=session_token,
        creator_id=creator.id,
        role=role,
        expires_at=expires_at
    )
    db.add(user_session)
    db.commit()

    return SessionResponse(
        token=session_token,
        creator_id=creator.id,
        role=role,
        expires_at=expires_at
    )

@router.get("/me")
def get_current_creator_info(session: UserSession = Depends(get_current_session)):
    """Returns the authenticated creator profile."""
    creator = session.creator
    return {
        "creator_id": creator.id,
        "business_name": creator.business_name,
        "email": creator.email,
        "role": session.role,
        "session_expires_at": session.expires_at
    }

