"""
Server-side booking state machine (blueprint §11, §14, §31).

Rules this module enforces:
- A booking can only move to a state reachable from its current state
  (ALLOWED_TRANSITIONS below) — no client can jump straight to
  SERVICE_COMPLETED or PAID.
- SERVICE_STARTED can only be reached by verifying a hashed, expiring,
  attempt-limited OTP — never by a plain client-side POST (blueprint §13).
- Every transition writes an AuditLog row with actor, from/to status and
  a timestamp (blueprint §31).
"""
import hashlib
import random
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from . import models

OTP_TTL_MINUTES = 15
OTP_MAX_ATTEMPTS = 5

# Map of current status -> set of statuses it may transition to.
# CANCELLED is only reachable before the provider has arrived on site —
# once ARRIVED, a no-show/abort is a DISPUTED case, not a plain cancel,
# because real cost (a trip out) has already been incurred.
ALLOWED_TRANSITIONS: dict[models.BookingStatus, set[models.BookingStatus]] = {
    models.BookingStatus.CONFIRMED: {
        models.BookingStatus.ON_THE_WAY,
        models.BookingStatus.CANCELLED,
    },
    models.BookingStatus.ON_THE_WAY: {
        models.BookingStatus.ARRIVED,
        models.BookingStatus.CANCELLED,
    },
    models.BookingStatus.ARRIVED: {
        models.BookingStatus.SERVICE_STARTED,
        models.BookingStatus.DISPUTED,
    },
    models.BookingStatus.SERVICE_STARTED: {
        models.BookingStatus.SERVICE_COMPLETED,
        models.BookingStatus.DISPUTED,
    },
    models.BookingStatus.SERVICE_COMPLETED: {
        models.BookingStatus.PAID,
        models.BookingStatus.DISPUTED,
    },
    models.BookingStatus.PAID: set(),
    models.BookingStatus.DISPUTED: set(),   # only an admin override can move out of this
    models.BookingStatus.CANCELLED: set(),
}

TIMESTAMP_FIELD = {
    models.BookingStatus.ON_THE_WAY: "on_the_way_at",
    models.BookingStatus.ARRIVED: "arrived_at",
    models.BookingStatus.SERVICE_STARTED: "started_at",
    models.BookingStatus.SERVICE_COMPLETED: "completed_at",
    models.BookingStatus.PAID: "paid_at",
    models.BookingStatus.CANCELLED: "cancelled_at",
}


def transition(
    db: Session,
    booking: models.Booking,
    to_status: models.BookingStatus,
    actor: models.User,
    meta: dict | None = None,
) -> models.Booking:
    allowed = ALLOWED_TRANSITIONS.get(booking.status, set())
    if to_status not in allowed:
        raise HTTPException(
            400,
            f"Cannot move a booking from {booking.status.value} to {to_status.value}. "
            f"Allowed next states: {sorted(s.value for s in allowed) or 'none — this is a final state'}.",
        )

    from_status = booking.status
    booking.status = to_status
    ts_field = TIMESTAMP_FIELD.get(to_status)
    if ts_field:
        setattr(booking, ts_field, datetime.utcnow())

    db.add(
        models.AuditLog(
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role.value if actor else None,
            action="booking_transition",
            entity_type="Booking",
            entity_id=booking.id,
            from_status=from_status.value,
            to_status=to_status.value,
            meta=meta or {},
        )
    )
    return booking


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def generate_and_store_otp(job: models.Job) -> str:
    """Generates a fresh 4-digit OTP, stores only its hash + expiry, resets
    the attempt counter, and returns the plaintext once — to be shown to
    the customer only (never logged, never persisted in plaintext)."""
    otp = f"{random.randint(0, 9999):04d}"
    job.otp_hash = _hash_otp(otp)
    job.otp_expires_at = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)
    job.otp_attempts = 0
    job.otp_generated_at = datetime.utcnow()
    return otp


def verify_otp(job: models.Job, submitted: str) -> None:
    """Raises HTTPException on any failure; returns None on success.
    Uses a constant-time comparison on the hash to avoid timing leaks."""
    if not job.otp_hash or not job.otp_expires_at:
        raise HTTPException(400, "No active start OTP — ask the customer to show the code again")
    if job.otp_attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            423, "Too many incorrect attempts. Ask the customer to generate a new code."
        )
    if datetime.utcnow() > job.otp_expires_at:
        raise HTTPException(400, "This code has expired. Ask the customer to generate a new one.")

    if not secrets.compare_digest(_hash_otp(submitted), job.otp_hash):
        job.otp_attempts += 1
        remaining = OTP_MAX_ATTEMPTS - job.otp_attempts
        if remaining <= 0:
            raise HTTPException(423, "Too many incorrect attempts. Ask the customer for a new code.")
        raise HTTPException(400, f"Incorrect code. {remaining} attempt(s) left.")

    # success — clear it so it can't be replayed
    job.otp_hash = None
    job.otp_expires_at = None
