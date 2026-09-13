from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/v1/quotes", tags=["quotes"])


@router.post("/", response_model=schemas.QuoteOut)
def submit_quote(
    payload: schemas.QuoteCreate,
    provider_id: str,
    db: Session = Depends(get_db),
):
    # provider_id passed explicitly for MVP simplicity — once provider
    # self-serve login exists, resolve this from the auth token instead
    # (require_role("provider") + look up the caller's Provider row),
    # the same way service_requests.py resolves the customer.
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider or provider.verification_status != models.VerificationStatus.APPROVED:
        raise HTTPException(403, "Provider not found or not approved")

    sr = (
        db.query(models.ServiceRequest)
        .filter(models.ServiceRequest.id == payload.service_request_id)
        .first()
    )
    if not sr:
        raise HTTPException(404, "Service request not found")
    if sr.status not in (models.ServiceRequestStatus.submitted, models.ServiceRequestStatus.quoted):
        raise HTTPException(400, "This request is no longer open for quotes")

    quote = models.Quote(
        service_request_id=sr.id,
        provider_id=provider.id,
        price=payload.price,
        message=payload.message,
    )
    db.add(quote)
    sr.status = models.ServiceRequestStatus.quoted
    db.commit()
    db.refresh(quote)
    return quote


@router.post("/{quote_id}/accept", response_model=schemas.BookingOut)
def accept_quote(
    quote_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("customer")),
):
    quote = db.query(models.Quote).filter(models.Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")

    sr = (
        db.query(models.ServiceRequest)
        .filter(models.ServiceRequest.id == quote.service_request_id)
        .first()
    )
    if sr.customer_id != user.id:
        raise HTTPException(403, "Not your service request")
    if sr.status == models.ServiceRequestStatus.confirmed:
        raise HTTPException(400, "This request is already booked")

    quote.status = models.QuoteStatus.accepted
    sr.status = models.ServiceRequestStatus.confirmed
    for other in sr.quotes:
        if other.id != quote.id and other.status == models.QuoteStatus.pending:
            other.status = models.QuoteStatus.declined

    booking = models.Booking(
        service_request_id=sr.id,
        quote_id=quote.id,
        provider_id=quote.provider_id,
        customer_id=user.id,
        status=models.BookingStatus.CONFIRMED,
    )
    db.add(booking)
    db.flush()

    job = models.Job(booking_id=booking.id)
    db.add(job)

    db.add(
        models.AuditLog(
            actor_user_id=user.id,
            actor_role=user.role.value,
            action="booking_created",
            entity_type="Booking",
            entity_id=booking.id,
            to_status=models.BookingStatus.CONFIRMED.value,
        )
    )

    db.commit()
    db.refresh(booking)
    return booking
