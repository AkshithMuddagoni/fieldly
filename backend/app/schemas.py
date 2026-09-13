from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class OTPRequest(BaseModel):
    phone: str = Field(..., min_length=8, max_length=15)


class OTPVerify(BaseModel):
    phone: str
    otp: str
    name: Optional[str] = None
    role: str = "customer"


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    name: Optional[str] = None


class ServiceCreate(BaseModel):
    category: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    requirement_schema: list[dict[str, Any]] = []


class ServiceOut(BaseModel):
    id: str
    category: str
    name: str
    slug: str
    description: Optional[str]
    requirement_schema: list[dict[str, Any]]

    class Config:
        from_attributes = True


class ProviderCreate(BaseModel):
    business_name: str
    phone: str
    bio: Optional[str] = None
    state: str
    city: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    service_radius_km: float = 25.0
    equipment_summary: Optional[str] = None
    years_experience: Optional[int] = None
    walta_rig_registration_number: Optional[str] = None
    service_slugs: list[str] = []


class ProviderOut(BaseModel):
    id: str
    business_name: str
    phone: str
    bio: Optional[str]
    state: str
    city: str
    lat: Optional[float]
    lng: Optional[float]
    service_radius_km: float
    equipment_summary: Optional[str]
    years_experience: Optional[int]
    walta_rig_registration_number: Optional[str]
    verification_status: str
    is_online: bool
    avg_rating: float
    rating_count: int
    jobs_completed: int
    distance_km: Optional[float] = None

    class Config:
        from_attributes = True


class ProviderVerifyIn(BaseModel):
    status: str  # "APPROVED" | "REJECTED"


class ServiceRequestCreate(BaseModel):
    service_id: str
    location_label: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    requirements: dict[str, Any] = {}
    notes: Optional[str] = None


class ServiceRequestOut(BaseModel):
    id: str
    customer_id: str
    service_id: str
    location_label: str
    requirements: dict[str, Any]
    notes: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class QuoteCreate(BaseModel):
    service_request_id: str
    price: Optional[float] = None
    message: Optional[str] = None


class QuoteOut(BaseModel):
    id: str
    service_request_id: str
    provider_id: str
    price: Optional[float]
    message: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class BookingOut(BaseModel):
    id: str
    service_request_id: str
    quote_id: str
    provider_id: str
    customer_id: str
    status: str
    scheduled_at: Optional[datetime]
    confirmed_at: Optional[datetime]
    on_the_way_at: Optional[datetime]
    arrived_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    paid_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    dispute_reason: Optional[str]
    final_amount: Optional[float]
    payment_method: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StartOtpOut(BaseModel):
    otp: str
    expires_in_minutes: int


class BookingStartIn(BaseModel):
    otp: str


class DisputeIn(BaseModel):
    reason: str


class JobCompleteIn(BaseModel):
    final_amount: float
    payment_method: str


class ReviewCreate(BaseModel):
    booking_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: str
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
