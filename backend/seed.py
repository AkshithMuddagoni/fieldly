"""
Seeds demo data so the app isn't empty on first run.

Run from the backend/ directory (after activating your venv):
    python3 seed.py

Safe to re-run — it skips anything that already exists by slug/phone.
"""
from app.database import Base, SessionLocal, engine
from app.models import Provider, Service, ServiceRequest, User, UserRole, VerificationStatus

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Slugs are set explicitly to match the ids the frontend's SERVICES list
# already uses ("borewell", "jcb", "tractor", ...) so the React app can
# match a fetched service to its local icon/description by slug without
# a separate lookup table. Only these three are seeded as "live" — the
# rest of the frontend's category tiles stay visible but show "Coming
# soon", matching the spec's own principle of launching one vertical at
# a time instead of all categories at once.
SERVICES = [
    {
        "category": "Borewell",
        "name": "Borewell drilling",
        "slug": "borewell",
        "description": "Drilling, rigs, compressors and operators.",
        "requirement_schema": [
            {"key": "purpose", "label": "What is this borewell for?", "type": "select",
             "options": ["Home", "Farm", "Construction", "Business"], "required": True},
            {"key": "depth_ft", "label": "Expected depth (if known)", "type": "number", "required": False},
            {"key": "site_access", "label": "Site access", "type": "select",
             "options": ["Easy access", "Narrow road", "Difficult terrain"], "required": True},
        ],
    },
    {
        "category": "JCB",
        "name": "JCB & excavators",
        "slug": "jcb",
        "description": "Digging, earthwork and site clearing.",
        "requirement_schema": [
            {"key": "work_type", "label": "What work is needed?", "type": "select",
             "options": ["Digging", "Earthwork", "Site clearing", "Loading"], "required": True},
            {"key": "operator_required", "label": "Operator required?", "type": "boolean", "required": True},
        ],
    },
    {
        "category": "Tractor",
        "name": "Tractor services",
        "slug": "tractor",
        "description": "Farm work, hauling and implements.",
        "requirement_schema": [
            {"key": "notes", "label": "What should the provider know?", "type": "text", "required": False},
        ],
    },
]

PROVIDERS = [
    dict(business_name="Sri Sai Borewell Works", phone="9000000001", state="Telangana", city="Warangal",
         lat=17.9689, lng=79.5941, equipment_summary="Hydraulic Rig - 1000 ft", years_experience=11,
         walta_rig_registration_number="TS-WALTA-WGL-00214", service_categories=["Borewell"]),
    dict(business_name="Lakshmi Drilling & Services", phone="9000000002", state="Telangana", city="Warangal",
         lat=17.9784, lng=79.6006, equipment_summary="Drilling Rig - 800 ft", years_experience=7,
         walta_rig_registration_number="TS-WALTA-WGL-00389", service_categories=["Borewell"]),
    dict(business_name="Reddy Earth & Borewell", phone="9000000003", state="Telangana", city="Hanamkonda",
         lat=18.0072, lng=79.5570, equipment_summary="Rotary Rig - 1200 ft", years_experience=15,
         walta_rig_registration_number="TS-WALTA-HNK-00097", service_categories=["Borewell"]),
    dict(business_name="Anand JCB Works", phone="9000000004", state="Telangana", city="Warangal",
         lat=17.9500, lng=79.6100, equipment_summary="3 excavators", years_experience=12,
         walta_rig_registration_number=None, service_categories=["JCB"]),
]


def run():
    service_by_category = {}
    for s in SERVICES:
        slug = s["slug"]
        existing = db.query(Service).filter(Service.slug == slug).first()
        if existing:
            service_by_category[s["category"]] = existing
            continue
        svc = Service(category=s["category"], name=s["name"], slug=slug,
                       description=s["description"], requirement_schema=s["requirement_schema"])
        db.add(svc)
        db.flush()
        service_by_category[s["category"]] = svc
        print(f"created service: {svc.name} ({svc.id})")

    for p in PROVIDERS:
        existing = db.query(Provider).filter(Provider.phone == p["phone"]).first()
        if existing:
            continue
        categories = p.pop("service_categories")
        provider_user = User(phone=p["phone"], name=p["business_name"], role=UserRole.provider)
        db.add(provider_user)
        db.flush()
        provider = Provider(
            user_id=provider_user.id,
            business_name=p["business_name"], phone=p["phone"], state=p["state"], city=p["city"],
            lat=p["lat"], lng=p["lng"], equipment_summary=p["equipment_summary"],
            years_experience=p["years_experience"],
            walta_rig_registration_number=p["walta_rig_registration_number"],
            verification_status=VerificationStatus.APPROVED,
            is_online=True,
        )
        db.add(provider)
        db.flush()
        from app.models import ProviderService
        for cat in categories:
            svc = service_by_category.get(cat)
            if svc:
                db.add(ProviderService(provider_id=provider.id, service_id=svc.id))
        print(f"created provider: {provider.business_name} ({provider.id})")

    db.commit()
    print("\nSeed complete.")


if __name__ == "__main__":
    run()
