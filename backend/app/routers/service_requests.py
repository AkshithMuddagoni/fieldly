from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..database import get_db
from .providers import haversine_km

router = APIRouter(prefix="/api/v1/service-requests", tags=["service-requests"])

FANOUT_SIZE = 5


@router.post("/", response_model=schemas.ServiceRequestOut)
def create_service_request(
    payload: schemas.ServiceRequestCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.require_role("customer")),
):
    service = db.query(models.Service).filter(models.Service.id == payload.service_id).first()
    if not service:
        raise HTTPException(404, "Service not found")

    for field in service.requirement_schema:
        if field.get("required") and field["key"] not in payload.requirements:
            raise HTTPException(422, f"Missing required field: {field['key']}")

    sr = models.ServiceRequest(
        customer_id=user.id,
        service_id=service.id,
        location_label=payload.location_label,
        lat=payload.lat,
        lng=payload.lng,
        requirements=payload.requirements,
        notes=payload.notes,
        status=models.ServiceRequestStatus.submitted,
    )
    db.add(sr)
    db.commit()
    db.refresh(sr)

    _notify_nearby_providers(db, sr, service)
    return sr


def _notify_nearby_providers(db: Session, sr: models.ServiceRequest, service: models.Service) -> None:
    q = (
        db.query(models.Provider)
        .join(models.ProviderService, models.ProviderService.provider_id == models.Provider.id)
        .filter(models.ProviderService.service_id == service.id)
        .filter(models.Provider.verification_status == models.VerificationStatus.APPROVED)
        .filter(models.Provider.is_online.is_(True))
        .all()
    )
    if sr.lat is not None and sr.lng is not None:
        q = sorted(
            [p for p in q if p.lat is not None and p.lng is not None],
            key=lambda p: haversine_km(sr.lat, sr.lng, p.lat, p.lng),
        )
    ranked = q[:FANOUT_SIZE]
    # MVP notification stub — replace with push/SMS dispatch.
    for p in ranked:
        print(f"[NOTIFY] provider={p.id} new request={sr.id} for service={service.name}")


@router.get("/", response_model=list[schemas.ServiceRequestOut])
def list_open_requests_for_provider(provider_id: str, db: Session = Depends(get_db)):
    """
    Requests a given provider can currently quote on: open (submitted or
    already has other quotes but not yet confirmed), for a service the
    provider offers, within the provider's service radius.
    Used by the static provider-dashboard.html test tool.
    """
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    service_ids = [link.service_id for link in provider.services]
    candidates = (
        db.query(models.ServiceRequest)
        .filter(models.ServiceRequest.service_id.in_(service_ids))
        .filter(
            models.ServiceRequest.status.in_(
                [models.ServiceRequestStatus.submitted, models.ServiceRequestStatus.quoted]
            )
        )
        .all()
    )

    if provider.lat is None or provider.lng is None:
        return candidates

    return [
        sr
        for sr in candidates
        if sr.lat is None
        or sr.lng is None
        or haversine_km(sr.lat, sr.lng, provider.lat, provider.lng) <= provider.service_radius_km
    ]


@router.get("/{request_id}", response_model=schemas.ServiceRequestOut)
def get_service_request(
    request_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    sr = db.query(models.ServiceRequest).filter(models.ServiceRequest.id == request_id).first()
    if not sr:
        raise HTTPException(404, "Service request not found")
    if user.role == "customer" and sr.customer_id != user.id:
        raise HTTPException(403, "Not your request")
    return sr


@router.get("/{request_id}/quotes", response_model=list[schemas.QuoteOut])
def list_quotes(
    request_id: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(security.get_current_user),
):
    sr = db.query(models.ServiceRequest).filter(models.ServiceRequest.id == request_id).first()
    if not sr:
        raise HTTPException(404, "Service request not found")
    if user.role == "customer" and sr.customer_id != user.id:
        raise HTTPException(403, "Not your request")
    return sr.quotes
