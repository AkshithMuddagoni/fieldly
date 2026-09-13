import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


def haversine_km(lat1, lng1, lat2, lng2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@router.post("/", response_model=schemas.ProviderOut)
def create_provider(payload: schemas.ProviderCreate, db: Session = Depends(get_db)):
    # NOTE: open in this MVP — matches DEPLOYMENT_GUIDE.md Part 5's
    # ops-led onboarding via /docs (real-world providers rarely self-serve
    # sign up on day one of a pilot; someone on your team enters them).
    # Put this behind admin auth once self-serve provider signup ships.
    #
    # The phone number entered here becomes how this provider logs in
    # later (OTP, same as customers) — without linking a User account now,
    # they'd have no way to authenticate against the booking-lifecycle
    # endpoints, which all require a real provider login.
    user = db.query(models.User).filter(models.User.phone == payload.phone).first()
    if not user:
        user = models.User(phone=payload.phone, name=payload.business_name, role=models.UserRole.provider)
        db.add(user)
        db.flush()
    elif user.role != models.UserRole.provider:
        raise HTTPException(400, f"Phone {payload.phone} is already registered as a {user.role.value}")

    provider = models.Provider(
        user_id=user.id,
        business_name=payload.business_name,
        phone=payload.phone,
        bio=payload.bio,
        state=payload.state,
        city=payload.city,
        lat=payload.lat,
        lng=payload.lng,
        service_radius_km=payload.service_radius_km,
        equipment_summary=payload.equipment_summary,
        years_experience=payload.years_experience,
        walta_rig_registration_number=payload.walta_rig_registration_number,
        verification_status=models.VerificationStatus.PENDING,
    )
    db.add(provider)
    db.flush()

    for slug in payload.service_slugs:
        service = db.query(models.Service).filter(models.Service.slug == slug).first()
        if service:
            db.add(models.ProviderService(provider_id=provider.id, service_id=service.id))

    db.commit()
    db.refresh(provider)
    return provider


@router.get("/", response_model=list[schemas.ProviderOut])
def list_providers(
    state: str | None = None,
    city: str | None = None,
    service_slug: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    verified_only: bool = True,
    db: Session = Depends(get_db),
):
    q = db.query(models.Provider)
    if verified_only:
        q = q.filter(models.Provider.verification_status == models.VerificationStatus.APPROVED)
    if state:
        q = q.filter(models.Provider.state == state)
    if city:
        q = q.filter(models.Provider.city == city)
    if service_slug:
        q = q.join(
            models.ProviderService, models.ProviderService.provider_id == models.Provider.id
        ).join(models.Service, models.Service.id == models.ProviderService.service_id).filter(
            models.Service.slug == service_slug
        )

    providers = q.all()
    results = []
    for p in providers:
        out = schemas.ProviderOut.model_validate(p)
        if lat is not None and lng is not None and p.lat is not None and p.lng is not None:
            out.distance_km = round(haversine_km(lat, lng, p.lat, p.lng), 2)
        results.append(out)

    if lat is not None and lng is not None:
        results.sort(key=lambda p: p.distance_km if p.distance_km is not None else 9e9)
    return results


@router.get("/{provider_id}", response_model=schemas.ProviderOut)
def get_provider(provider_id: str, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    return provider


@router.patch("/{provider_id}/verify", response_model=schemas.ProviderOut)
def verify_provider(provider_id: str, payload: schemas.ProviderVerifyIn, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    status_value = payload.status.upper()
    if status_value not in ("APPROVED", "REJECTED"):
        raise HTTPException(400, "status must be APPROVED or REJECTED")

    if status_value == "APPROVED":
        offers_borewell = any(
            link.service.category.strip().lower() == "borewell" for link in provider.services
        )
        if offers_borewell and not provider.walta_rig_registration_number:
            raise HTTPException(
                400,
                "This provider offers a borewell service and has no "
                "walta_rig_registration_number on file. Add one before approving "
                "(required under Telangana's WALTA Act for groundwater drilling).",
            )

    provider.verification_status = models.VerificationStatus(status_value)
    db.commit()
    db.refresh(provider)
    return provider


@router.patch("/{provider_id}/online", response_model=schemas.ProviderOut)
def set_online(provider_id: str, online: bool, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    if provider.verification_status != models.VerificationStatus.APPROVED:
        raise HTTPException(403, "Provider must be approved before going online")
    provider.is_online = online
    db.commit()
    db.refresh(provider)
    return provider
