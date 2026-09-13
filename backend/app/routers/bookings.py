"""
Booking lifecycle endpoints — every transition goes through
state_machine.transition() so illegal jumps are rejected server-side
(blueprint §31: never trust client-side state transitions).

Who can trigger what:
- on-the-way / arrived / start / complete: provider only (they're the one
  physically doing these things)
- start-otp (viewing the code): customer only
- cancel: either party, only while still CONFIRMED or ON_THE_WAY
- dispute: either party, from ARRIVED onward
- mark-paid: either party (a real payment gateway webhook would trigger
  this in production instead of a manual call — see DEPLOYMENT_GUIDE.md)
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security, state_machine
from ..database import get_db

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


def _get_booking(db: Session, booking_id: str) -> models.Booking:
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    return booking


def _require_customer(booking: models.Booking, user: models.User) -> None:
    if user.role == "customer" and booking.customer_id != user.id:
        raise HTTPException(403, "Not your booking")


def _require_provider(db: Session, booking: models.Booking, user: models.User) -> models.Provider:
    provider = db.query(models.Provider).filter(models.Provider.user_id == user.id).first()
    if not provider or booking.provider_id != provider.id:
        raise HTTPException(403, "Not your booking")
    return provider


@router.get("/{booking_id}", response_model=schemas.BookingOut)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    booking = _get_booking(db, booking_id)
    _require_customer(booking, user)
    if user.role == "provider":
        _require_provider(db, booking, user)
    return booking


@router.post("/{booking_id}/on-the-way", response_model=schemas.BookingOut)
def mark_on_the_way(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("provider")),
):
    booking = _get_booking(db, booking_id)
    _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.ON_THE_WAY, user)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/arrived", response_model=schemas.BookingOut)
def mark_arrived(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("provider")),
):
    booking = _get_booking(db, booking_id)
    _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.ARRIVED, user)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/{booking_id}/start-otp", response_model=schemas.StartOtpOut)
def show_start_otp(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("customer")),
):
    """Customer-only. Generates (or regenerates) the start OTP once the
    provider has arrived, and returns it in plaintext exactly once — this
    is the only place the plaintext code ever appears. The customer reads
    it aloud to the provider, who enters it via POST /{id}/start."""
    booking = _get_booking(db, booking_id)
    _require_customer(booking, user)
    if booking.status != models.BookingStatus.ARRIVED:
        raise HTTPException(400, "Start OTP is only available once the provider has arrived")

    job = db.query(models.Job).filter(models.Job.booking_id == booking.id).first()
    otp = state_machine.generate_and_store_otp(job)
    db.commit()
    return schemas.StartOtpOut(otp=otp, expires_in_minutes=state_machine.OTP_TTL_MINUTES)


@router.post("/{booking_id}/start", response_model=schemas.BookingOut)
def start_service(
    booking_id: str,
    payload: schemas.BookingStartIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("provider")),
):
    booking = _get_booking(db, booking_id)
    _require_provider(db, booking, user)
    if booking.status != models.BookingStatus.ARRIVED:
        raise HTTPException(400, f"Cannot start service from status {booking.status.value}")

    job = db.query(models.Job).filter(models.Job.booking_id == booking.id).first()
    state_machine.verify_otp(job, payload.otp)  # raises on failure

    state_machine.transition(db, booking, models.BookingStatus.SERVICE_STARTED, user)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/complete", response_model=schemas.BookingOut)
def complete_service(
    booking_id: str,
    payload: schemas.JobCompleteIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("provider")),
):
    booking = _get_booking(db, booking_id)
    provider = _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.SERVICE_COMPLETED, user)

    booking.final_amount = payload.final_amount
    booking.payment_method = payload.payment_method
    provider.jobs_completed += 1

    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/mark-paid", response_model=schemas.BookingOut)
def mark_paid(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    booking = _get_booking(db, booking_id)
    _require_customer(booking, user)
    if user.role == "provider":
        _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.PAID, user)
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/dispute", response_model=schemas.BookingOut)
def raise_dispute(
    booking_id: str,
    payload: schemas.DisputeIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    booking = _get_booking(db, booking_id)
    _require_customer(booking, user)
    if user.role == "provider":
        _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.DISPUTED, user, meta={"reason": payload.reason})
    booking.dispute_reason = payload.reason
    db.commit()
    db.refresh(booking)
    return booking


@router.post("/{booking_id}/cancel", response_model=schemas.BookingOut)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    booking = _get_booking(db, booking_id)
    _require_customer(booking, user)
    if user.role == "provider":
        _require_provider(db, booking, user)
    state_machine.transition(db, booking, models.BookingStatus.CANCELLED, user)
    db.commit()
    db.refresh(booking)
    return booking
