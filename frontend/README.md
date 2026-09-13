# Fieldly Frontend V4

A polished marketplace-style customer/provider frontend prototype for Fieldly.

## What changed in V4
- Location setup is now a first-time setup step, not the Home screen.
- After selecting a service location, the user lands on a real marketplace Home.
- Rich Home includes:
  - search / natural-language job entry
  - persistent service location
  - popular services
  - nearby provider discovery
  - trust signals
  - simple "how it works" flow
  - provider CTA
- Header logo returns to Home after location is selected.
- Service selection now has an explicit "Back to home" action.
- Existing V3 request → provider → booking → tracking → completion flow remains intact.

## Run
```bash
npm install
npm run dev
```

This is still a frontend prototype. Maps, GPS, OTP, notifications, payments, provider availability and backend APIs are mocked and should be connected to the FastAPI/PostgreSQL platform later.
