# Deploying Fieldly to the real internet — a first-timer's guide

This assumes you've never deployed a website before. Every step says exactly
what to click or type.

**What changed from the previous version of this guide:** the original
assumed a zero-build, plain HTML/JS frontend, so one Render Python service
could serve everything. The actual frontend (`fieldly-frontend-v4`) is a
Vite/React app that needs a build step Render's Python runtime can't run.
The fix is two separate Render services talking to each other over the
network — this is also how a real production setup would usually look
(frontend on a CDN/static host, API on its own service), not a workaround.

**The four pieces you're connecting:**
- **GitHub** — stores your code online (required so Render can find it)
- **Supabase** — a free, permanent Postgres database in the cloud
- **Render Web Service** — runs the FastAPI backend 24/7, gives it a public URL
- **Render Static Site** — builds and hosts the React frontend, gives it a public URL

None of this costs money at pilot scale.

---

## Part 0 — Before you start

Open a terminal (Mac: `Cmd+Space` → "Terminal"; Windows: Windows key →
"PowerShell"; Linux: you know where it is).

Check you have these installed:
```bash
python3 --version   # need 3.11+
node --version       # need 18+
git --version
```
Missing Python: install from python.org. Missing Node: install from
nodejs.org (get the LTS version). Missing Git: Mac prompts automatically
the first time you type `git`; Windows installs from git-scm.com; Linux is
`sudo apt install git`.

---

## Part 1 — Run the backend on your own computer first

1. Unzip the project, then in your terminal:
   ```bash
   cd fieldly/backend
   python3 -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Start it:
   ```bash
   uvicorn app.main:app --reload
   ```
   You should see `Uvicorn running on http://127.0.0.1:8000`. Leave this
   running.
3. In a **second** terminal, same folder, same venv activated:
   ```bash
   python3 seed.py
   ```
   This creates the borewell/JCB/tractor services and four demo Warangal
   providers, all pre-approved so you can test immediately.
4. Open `http://127.0.0.1:8000/docs` — this is the interactive API explorer.
   Try `GET /api/v1/services/` and `GET /api/v1/providers/` and confirm you
   see the seeded data.

**If something breaks here:** copy the exact error text and fix it before
moving on.

---

## Part 2 — Run the frontend on your own computer

1. In a **third** terminal:
   ```bash
   cd fieldly/frontend
   cp .env.example .env
   npm install
   npm run dev
   ```
2. Open the URL it prints (usually `http://localhost:5173`). Walk through:
   choose a location → Home → tap "Borewell services" → you should see the
   real seeded providers (Sri Sai Borewell Works, etc.) pulled from your
   running backend, not the hardcoded demo list.
3. Tap a provider → "Request service" → sign in with any name and a
   10-digit number → the OTP screen shows a **Test OTP** value directly
   on screen (there's no real SMS provider wired in yet — see Part 7) →
   enter it → send the request.
4. Back in your first terminal (the one running `uvicorn --reload`), you
   should see a line like `[NOTIFY] provider=... new request=... for
   service=Borewell drilling` — that confirms the request reached the
   real database.
5. Open `http://127.0.0.1:8000/provider-dashboard.html` in a new tab —
   this is a small plain-HTML test tool (not the real provider app, which
   this frontend package doesn't include yet). Paste in one of the seeded
   provider IDs (get it from `GET /api/v1/providers/` in `/docs`), load
   requests, and send a quote against the request you just created. This
   proves the full request → quote loop works end to end.

Stop both servers (`Ctrl+C` in each) once you're happy.

---

## Part 3 — Put your code on GitHub

1. github.com → sign up if you haven't.
2. **+** → **New repository** → name it `fieldly` → **Public** → don't
   add a README → **Create repository**. Keep the page open.
3. Back in your terminal, at the top of the `fieldly` folder (containing
   both `backend/` and `frontend/`):
   ```bash
   cd fieldly
   git init
   ```
   Create `.gitignore`:
   ```bash
   cat > .gitignore << 'EOF'
   backend/venv/
   backend/fieldly_dev.db
   backend/__pycache__/
   backend/**/__pycache__/
   *.pyc
   frontend/node_modules/
   frontend/dist/
   frontend/.env
   EOF
   ```
   Commit and push:
   ```bash
   git add .
   git commit -m "Initial Fieldly MVP"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/fieldly.git
   git push -u origin main
   ```

---

## Part 4 — Create your free database on Supabase

1. supabase.com → **Start your project** → sign in with GitHub.
2. **New project** → name `fieldly` → **Generate a password** and save it
   somewhere safe → region **Mumbai (ap-south-1)** (closest to Telangana)
   → **Create new project**, wait ~2 minutes.
3. Once ready: **Connect** button → **Connection string** → **URI** tab →
   copy it. It looks like:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with the real password from step 2. Save the
   complete string — you'll paste it into Render next.

A free Supabase project pauses after a week of no traffic — click
**Resume project** in its dashboard if your live site suddenly stops
responding.

---

## Part 5 — Deploy the backend (Render Web Service)

1. render.com → sign up with GitHub.
2. **New +** → **Web Service** → select your `fieldly` repo.
3. Settings:
   - **Name:** `fieldly-api`
   - **Region:** Singapore
   - **Root Directory:** `backend`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. **Environment Variables:**
   - `DATABASE_URL` → your full Supabase connection string from Part 4
   - `JWT_SECRET` → any long random string (e.g. generate one with
     `python3 -c "import secrets; print(secrets.token_hex(32))"`)
   - `ALLOWED_ORIGINS` → leave blank for now, you'll set this in Part 6
     once you know your frontend's URL
5. **Create Web Service**. Wait for `Your service is live`. Note the URL,
   e.g. `https://fieldly-api-xxxx.onrender.com`.
6. Visit `https://fieldly-api-xxxx.onrender.com/docs` to confirm it's up,
   and `https://fieldly-api-xxxx.onrender.com/provider-dashboard.html` to
   confirm the test tool loads.
7. Run the seed script against this live database once, from your own
   computer:
   ```bash
   cd backend
   export DATABASE_URL="the same connection string you put in Render"
   python3 seed.py
   ```

---

## Part 6 — Deploy the frontend (Render Static Site)

1. **New +** → **Static Site** → same `fieldly` repo.
2. Settings:
   - **Name:** `fieldly`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
3. **Environment Variables:**
   - `VITE_API_URL` → your backend URL from Part 5, e.g.
     `https://fieldly-api-xxxx.onrender.com`
4. **Create Static Site**. Wait for the build, then note its URL, e.g.
   `https://fieldly-xxxx.onrender.com`.
5. Go back to your **backend** service on Render → Environment → set
   `ALLOWED_ORIGINS` to that static site URL exactly (e.g.
   `https://fieldly-xxxx.onrender.com`) → save, which redeploys the
   backend with CORS locked to your real frontend instead of `*`.

---

## Part 7 — Before real customers use this

The seed data and OTP flow are deliberately fake so you can test without
an SMS bill. Before a real pilot:

- **Wire a real SMS provider** (MSG91 or Twilio Verify both work well in
  India) into `backend/app/routers/auth.py`'s `_send_otp()` function, and
  remove the `dev_hint` field from the `/request-otp` response.
- **Lock down `POST /api/v1/services/` and `POST /api/v1/providers/`** —
  they're intentionally open right now so you can create data through
  `/docs` without building an admin UI first, but that also means anyone
  who finds `/docs` can create fake providers. Add an admin API key or
  login before this goes public.
- **Rate-limit `/auth/request-otp`** (e.g. 3 per phone per 10 minutes) —
  not implemented yet, and a real SMS provider will charge you per message
  if this stays open.
- **Onboard your first providers by hand.** With one city and one service
  live, don't wait for self-serve signup — call the providers you already
  know, enter them via `/docs` or the provider-dashboard test tool, and
  verify them yourself. This is the standard way real local-service
  marketplaces solve the cold-start problem.

---

## Troubleshooting quick reference

| Problem | Likely cause |
|---|---|
| Backend build fails on Render | Check `requirements.txt` is committed and `Root Directory` is set to `backend` |
| Frontend build fails on Render | Check `Root Directory` is `frontend` and `Publish Directory` is `dist` |
| Frontend loads but shows demo/fallback providers, not real ones | `VITE_API_URL` isn't set, or doesn't match your backend's exact URL — check the browser console for a failed fetch |
| Backend responds but frontend gets a CORS error | `ALLOWED_ORIGINS` on the backend doesn't match the frontend's exact URL (including `https://`, no trailing slash) |
| Site shows a database error | `DATABASE_URL` on the backend has a leftover `[YOUR-PASSWORD]` placeholder |
| Supabase site stops responding after a quiet week | Go to Supabase dashboard → **Resume project** |
| Render free tier takes 30-60s to load after being idle | Normal — free services sleep after 15 minutes of no traffic |

## Making a change later

```bash
git add .
git commit -m "describe what changed"
git push
```
Both Render services redeploy automatically on every push to `main`.
