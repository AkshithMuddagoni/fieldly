import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/v1/services", tags=["services"])


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@router.get("/", response_model=list[schemas.ServiceOut])
def list_services(db: Session = Depends(get_db)):
    return db.query(models.Service).filter(models.Service.is_active.is_(True)).all()


@router.post("/", response_model=schemas.ServiceOut)
def create_service(payload: schemas.ServiceCreate, db: Session = Depends(get_db)):
    # NOTE: open in this MVP to match DEPLOYMENT_GUIDE.md's Swagger-driven
    # onboarding flow (Part 5). Put this behind admin auth before public
    # launch — anyone who finds /docs can currently create services.
    slug = payload.slug or slugify(payload.name)
    if db.query(models.Service).filter(models.Service.slug == slug).first():
        raise HTTPException(400, f"A service with slug '{slug}' already exists")

    service = models.Service(
        category=payload.category,
        name=payload.name,
        slug=slug,
        description=payload.description,
        requirement_schema=payload.requirement_schema,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.get("/{service_id}", response_model=schemas.ServiceOut)
def get_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(models.Service).filter(models.Service.id == service_id).first()
    if not service:
        raise HTTPException(404, "Service not found")
    return service
