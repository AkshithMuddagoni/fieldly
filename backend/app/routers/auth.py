from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

DEV_OTP = "482609"


def _send_otp(phone: str) -> None:
    print(f"[DEV OTP] Sending OTP {DEV_OTP} to +91{phone}")


@router.post("/request-otp")
def request_otp(payload: schemas.OTPRequest):
    _send_otp(payload.phone)
    # dev_hint is returned only so the local/demo frontend can autofill it.
    # Remove this field once a real SMS provider is wired in.
    return {"message": "OTP sent", "dev_hint": DEV_OTP}


@router.post("/verify-otp", response_model=schemas.TokenOut)
def verify_otp(payload: schemas.OTPVerify, db: Session = Depends(get_db)):
    if payload.otp != DEV_OTP:
        raise HTTPException(400, "Invalid OTP")
    if payload.role not in ("customer", "provider"):
        raise HTTPException(400, "Invalid role")

    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        user = models.User(phone=payload.phone, name=payload.name, role=payload.role)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif payload.name and not user.name:
        user.name = payload.name
        db.commit()

    token = security.create_access_token(user.id, user.role)
    return schemas.TokenOut(access_token=token, user_id=user.id, role=user.role, name=user.name)
