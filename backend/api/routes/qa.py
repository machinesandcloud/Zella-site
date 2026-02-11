from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.db import get_db
from models import User
from api.routes.auth import hash_password

router = APIRouter(prefix="/api/qa", tags=["qa"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/seed-user")
def seed_user(db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.username == "qa_user").first()
    if not user:
        user = User(username="qa_user", email="qa@example.com", password_hash=hash_password("qa"))
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"id": user.id, "username": user.username}
