# Fieldly — local services & equipment marketplace

A borewell-drilling-first marketplace (expanding to JCB, tractor, crane,
tankers): customers post a job, nearby verified providers quote, customer
books and tracks the job through a server-enforced lifecycle to completion,
payment and review.

## What's in this package

```
fieldly/
  backend/     FastAPI + SQLAlchemy API — Postgres (Supabase) in prod, SQLite locally
  frontend/    React/Vite customer app, wired end-to-end to the API
  DEPLOYMENT_GUIDE.md   Step-by-step Render + Supabase deployment
```

## What's real, end to end

**The full customer journey hits the real database and a real server-side
state machine — nothing here fakes a state transition client-side:**

1. **Location → service → provider list** — services and providers are
   fetched live from the API (falls back to demo data only if the backend
   is unreachable).
2. **OTP login** — real `/auth/request-otp` + `/auth/verify-otp`, JWT
   session stored and sent on every subsequent request.
3. **Send service request** — creates a real `ServiceRequest` row.
4. **Waiting for quotes** — the customer app polls
   `GET /service-requests/{id}/quotes` every few seconds. Use
   `provider-dashboard.html` (a plain-HTML test tool, log in as the
   provider via the same OTP flow) to send a real quote — the customer
   app picks it up automatically and accepts it, creating a real
   `Booking` + `Job`.
5. **Live tracking** — polls `GET /bookings/{id}` for real status.
   Provider-side actions (`on-the-way`, `arrived`, `start`, `complete`)
   happen from `provider-dashboard.html`; the customer screen updates on
   its next poll — it never lets the browser claim a transition itself.
6. **Start OTP** — only becomes available once the booking is genuinely
   `ARRIVED`. The code is generated fresh, hashed (never stored in
   plaintext), expires in 15 minutes, and locks after 5 wrong attempts.
   The provider enters it in the dashboard; the job only starts once the
   server verifies it.
7. **Completion → payment → review** — once the provider marks the job
   `SERVICE_COMPLETED`, the customer sees the real final amount, confirms
   payment (`POST /bookings/{id}/mark-paid`), and submits a review tied to
   the real booking.

**Still simulated / not built** (being direct about the boundary):
- Live GPS map rendering — the tracking map is a static illustration, not
  a real maps SDK feed
- Call / chat buttons in the tracking screen are decorative
- The provider's own polished app — `provider-dashboard.html` is a
  functional test tool (OTP login, requests, quotes, full booking
  lifecycle), not a production provider product surface
- Push notifications, SMS delivery, and the payment gateway itself (OTP
  and "payment" are both recorded server-side but nothing external is
  actually contacted yet)
- Admin console, dispute resolution UI, and the general Compliance Pack
  system beyond the borewell/WALTA case

## Server-side booking state machine

`backend/app/state_machine.py` is the core of the booking lifecycle:

```
CONFIRMED -> ON_THE_WAY -> ARRIVED -> SERVICE_STARTED -> SERVICE_COMPLETED -> PAID
                                    \-> DISPUTED (from ARRIVED onward)
     \-> CANCELLED (only before ARRIVED)
```

- Every transition is checked against an explicit allow-list — no client
  can jump straight to `PAID`.
- Every transition writes an `AuditLog` row (actor, role, from/to status,
  timestamp).
- The start-OTP is never persisted in plaintext — only a SHA-256 hash, an
  expiry, and an attempt counter.

## Two real-world corrections made while building this

1. **The original deployment guide assumed no frontend build step.** This
   frontend is Vite/React, so it needs `npm run build`. Fixed by deploying
   backend and frontend as two separate Render services (see
   `DEPLOYMENT_GUIDE.md`) rather than trying to serve everything from one
   Python service.
2. **WALTA registration is borewell-specific, not universal.** A JCB or
   tractor provider has no such requirement under Telangana's WALTA Act —
   `PATCH /providers/{id}/verify` only enforces it when the provider
   offers a service in the "Borewell" category.

## Quick start

See `DEPLOYMENT_GUIDE.md` Parts 1–2 for running both pieces locally
(includes the full test walkthrough: create a request, send a quote from
the provider dashboard, watch it flow through to a real booking), or
Parts 3–6 for a full Render + Supabase deployment.




psT7s469cgyX9t1H          postgresql://postgres.vufkdebbysbippzzzntb:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:5432/postgres



https://fieldly-ihsr.onrender.com/   backend


https://fieldly-zv78.onrender.com/ frontend