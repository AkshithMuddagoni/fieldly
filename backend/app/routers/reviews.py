from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post("/", response_model=schemas.ReviewOut)
def create_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("customer")),
):
    booking = db.query(models.Booking).filter(models.Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(404, "Booking not found")
    if booking.customer_id != user.id:
        raise HTTPException(403, "Not your booking")
    # blueprint §16: only eligible completed bookings can produce reviews.
    if booking.status not in (models.BookingStatus.SERVICE_COMPLETED, models.BookingStatus.PAID):
        raise HTTPException(400, "Can only review a completed job")

    job = db.query(models.Job).filter(models.Job.booking_id == booking.id).first()
    if job.review:
        raise HTTPException(400, "This job has already been reviewed")

    review = models.Review(
        job_id=job.id,
        customer_id=user.id,
        provider_id=booking.provider_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)

    provider = db.query(models.Provider).filter(models.Provider.id == booking.provider_id).first()
    total = provider.avg_rating * provider.rating_count + payload.rating
    provider.rating_count += 1
    provider.avg_rating = round(total / provider.rating_count, 2)

    db.commit()
    db.refresh(review)
    return review
