"""
Core database models.

Field choices here follow DEPLOYMENT_GUIDE.md's example payloads
(category/name/description/requirement_schema on Service;
walta_rig_registration_number + PATCH .../verify with a status body on
Provider) so the API this backend exposes matches what that guide's
curl/Swagger steps expect.

One correction to the guide's assumption: WALTA registration (Telangana's
Water, Land and Trees Act — the law governing groundwater extraction and
borewell drilling) is only relevant to *borewell* providers. A JCB or
tractor provider has no WALTA obligation, so verification only requires
walta_rig_registration_number when the provider offers a service in the
"Borewell" category (see routers/providers.py:verify_provider). Requiring
it universally would incorrectly block every non-borewell provider.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_id() -> str:
    return uuid.uuid4().hex


class UserRole(str, enum.Enum):
    customer = "customer"
    provider = "provider"
    admin = "admin"


class VerificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ServiceRequestStatus(str, enum.Enum):
    submitted = "submitted"
    quoted = "quoted"
    confirmed = "confirmed"
    cancelled = "cancelled"
    expired = "expired"


class QuoteStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"
    withdrawn = "withdrawn"


class BookingStatus(str, enum.Enum):
    """
    Blueprint §11/§14 lifecycle. Every transition is validated server-side
    in state_machine.py — this enum only names the states; it doesn't
    enforce order (that's the point of having a separate transition table
    instead of trusting whatever status a client sends).
    """
    CONFIRMED = "CONFIRMED"
    ON_THE_WAY = "ON_THE_WAY"
    ARRIVED = "ARRIVED"
    SERVICE_STARTED = "SERVICE_STARTED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    PAID = "PAID"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.customer)
    created_at = Column(DateTime, default=datetime.utcnow)

    provider_profile = relationship("Provider", back_populates="user", uselist=False)


class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, default=gen_id)
    category = Column(String, nullable=False)     # e.g. "Borewell"
    name = Column(String, nullable=False)          # e.g. "Borewell drilling"
    slug = Column(String, unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

    # Dynamic requirement schema: a JSON list of field definitions consumed
    # by the frontend's Requirements screen and validated server-side when
    # a ServiceRequest is submitted.
    requirement_schema = Column(JSON, nullable=False, default=list)

    provider_links = relationship("ProviderService", back_populates="service")


class Provider(Base):
    __tablename__ = "providers"

    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=True)

    business_name = Column(String, nullable=False)
    phone = Column(String, nullable=False, index=True)
    bio = Column(Text, nullable=True)

    state = Column(String, nullable=False)
    city = Column(String, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    service_radius_km = Column(Float, nullable=False, default=25.0)

    equipment_summary = Column(String, nullable=True)  # e.g. "Hydraulic Rig - 1000 ft"
    years_experience = Column(Integer, nullable=True)
    walta_rig_registration_number = Column(String, nullable=True)

    verification_status = Column(
        Enum(VerificationStatus), nullable=False, default=VerificationStatus.PENDING
    )
    is_online = Column(Boolean, default=False)

    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    jobs_completed = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="provider_profile")
    services = relationship("ProviderService", back_populates="provider")


class ProviderService(Base):
    __tablename__ = "provider_services"

    id = Column(String, primary_key=True, default=gen_id)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)

    provider = relationship("Provider", back_populates="services")
    service = relationship("Service", back_populates="provider_links")


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id = Column(String, primary_key=True, default=gen_id)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)

    location_label = Column(String, nullable=False)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    requirements = Column(JSON, nullable=False, default=dict)
    notes = Column(Text, nullable=True)

    status = Column(Enum(ServiceRequestStatus), default=ServiceRequestStatus.submitted)
    created_at = Column(DateTime, default=datetime.utcnow)

    quotes = relationship("Quote", back_populates="service_request")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String, primary_key=True, default=gen_id)
    service_request_id = Column(String, ForeignKey("service_requests.id"), nullable=False)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)

    price = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    status = Column(Enum(QuoteStatus), default=QuoteStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)

    service_request = relationship("ServiceRequest", back_populates="quotes")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String, primary_key=True, default=gen_id)
    service_request_id = Column(String, ForeignKey("service_requests.id"), nullable=False)
    quote_id = Column(String, ForeignKey("quotes.id"), nullable=False)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)

    status = Column(Enum(BookingStatus), default=BookingStatus.CONFIRMED, nullable=False)
    scheduled_at = Column(DateTime, nullable=True)

    # Operational timestamps — set only by the transition that reaches
    # that state, never client-supplied (blueprint §31: never trust
    # client-side state transitions).
    confirmed_at = Column(DateTime, default=datetime.utcnow)
    on_the_way_at = Column(DateTime, nullable=True)
    arrived_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    dispute_reason = Column(Text, nullable=True)

    final_amount = Column(Float, nullable=True)
    payment_method = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="booking", uselist=False)


class Job(Base):
    """
    Holds the start-OTP verification record for a booking. Never stores
    the OTP itself (blueprint §13) — only its hash, an expiry, and a
    failed-attempt counter, so a leaked database row can't be used to
    fake a service start.
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=gen_id)
    booking_id = Column(String, ForeignKey("bookings.id"), unique=True, nullable=False)

    otp_hash = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)
    otp_attempts = Column(Integer, default=0)
    otp_generated_at = Column(DateTime, nullable=True)

    booking = relationship("Booking", back_populates="job")
    review = relationship("Review", back_populates="job", uselist=False)


class AuditLog(Base):
    """Every booking state transition writes one row here (blueprint §31:
    'emit auditable domain events for major state changes')."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_id)
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String, nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(String, primary_key=True, default=gen_id)
    job_id = Column(String, ForeignKey("jobs.id"), unique=True, nullable=False)
    customer_id = Column(String, ForeignKey("users.id"), nullable=False)
    provider_id = Column(String, ForeignKey("providers.id"), nullable=False)

    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="review")
