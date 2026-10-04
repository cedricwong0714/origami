# Deploy the ORIGAMI studio (Vercel + Render)

The live calculator is two pieces:

1. **Studio UI** — Next.js in this folder (`web/structural`).
2. **Calculator API** — Python FastAPI (`origami.api.structural`), started locally with `python host_sa.py`.

Vercel hosts the UI. Vercel does **not** run this Python API. You run the API on Render (free tier works for demos), then point the UI at it.

---

## Overview

```text
Browser  →  your-app.vercel.app  →  /api/* rewritten  →  your-api.onrender.com/api/*
```

You will:

1. Deploy the API on Render and copy its URL.
2. Deploy this Next.js app on Vercel with `STRUCTURAL_API_URL` set to that URL.
3. Smoke-test melt, design sweep, and docking in the browser.

---

## Part A — API on Render

### A1. Repository

Push this git tree to **GitHub** (public or private). Render and Vercel both connect to GitHub.

If the code only lives on Cursor Origin today, add a GitHub remote and push the branch you want to deploy (for example `cursor/software-exports-a70b` or `main` after merge).

### A2. Create the web service

1. Sign in at [https://render.com](https://render.com).
2. **New +** → **Web Service** → connect the GitHub repository.
3. Use these settings:

| Field | Value |
|--------|--------|
| **Name** | `origami-structural-api` (or any name) |
| **Region** | closest to you |
| **Branch** | branch you deploy |
| **Root Directory** | *(leave empty — repo root)* |
| **Runtime** | **Python 3** |
| **Build Command** | `pip install ".[ui]"` |
| **Start Command** | `uvicorn origami.api.structural:app --host 0.0.0.0 --port $PORT` |

4. **Instance type:** Free (fine for ISEF demos; sleeps when idle).

5. **Advanced → Health Check Path:** `/api/meta/dependencies`

6. Create the service and wait until the deploy is **Live**.

### A3. Copy the API URL

Render shows something like:

`https://origami-structural-api.onrender.com`

No trailing slash. Test it:

```bash
curl -s "https://YOUR-SERVICE.onrender.com/api/stability/curve?t_assay_C=37" | head -c 200
```

You should see JSON with `"points"` and `"calibrated": false`.

**Cold start:** on the free plan the service sleeps. The first request after idle can take 30–60 seconds. Wake it once before a demo.

### A4. Optional — Blueprint

The repo root includes `render.yaml` with a second service definition `origami-structural-api`. You can use **New + → Blueprint** and point at this repo if you prefer infrastructure-as-code over the form above.

---

## Part B — Studio on Vercel

### B1. Import the project

1. Sign in at [https://vercel.com](https://vercel.com).
2. **Add New… → Project** → import the same GitHub repository.
3. **Root Directory:** click **Edit** and set **`web/structural`**. This step is required.
4. Framework Preset: **Next.js** (auto-detected).

### B2. Environment variable

Before the first deploy, open **Environment Variables** and add:

| Name | Value | Environments |
|------|--------|----------------|
| `STRUCTURAL_API_URL` | `https://YOUR-SERVICE.onrender.com` | Production, Preview, Development |

Use your Render URL from Part A. **No trailing slash.**

On Vercel, `VERCEL=1` is set automatically. The build **does not** use static export; Next.js rewrites proxy `/api/*` to `STRUCTURAL_API_URL`.

You do **not** need `NEXT_PUBLIC_SA_API` if rewrites work (default). The app calls `/api/...` on the same Vercel origin.

### B3. Build settings

Leave defaults unless you changed them:

- **Build Command:** `npm run build`
- **Install Command:** `npm install`
- **Output Directory:** *(leave empty — Vercel runs Next.js, not a manual `out/` upload)*

### B4. Deploy

Click **Deploy**. When the build finishes, open the production URL (for example `https://origami-structural.vercel.app`).

### B5. CLI alternative

From your laptop, with Node installed:

```bash
cd web/structural
npm install
npx vercel login
npx vercel link          # pick team, link to project
npx vercel env add STRUCTURAL_API_URL production   # paste Render URL
npm run build
npx vercel --prod
```

---

## Part C — Smoke test

On your Vercel URL:

1. **Structural analysis → Screw** — 3D or helix view loads.
2. **Stability → Melting temperature** — curve from n = 3 to 24 appears.
3. **Structural analysis → Choose a length** — colored strip and charts after load.
4. **Docking → Affinity check** — n = 8, Kd 0.19 nM returns a verdict.

Open DevTools → **Network**. Requests should go to `https://your-app.vercel.app/api/...` with status **200**. If you see **502** or **504**, the API is down, still waking, or `STRUCTURAL_API_URL` is wrong.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|----------------|-----|
| UI loads, all models error | API not set or asleep | Check `STRUCTURAL_API_URL`; curl Render URL |
| 404 on `/api/...` | Wrong Vercel root | Root must be `web/structural` |
| Build fails on Render | Missing deps | Build command must be `pip install ".[ui]"` |
| Build fails on Vercel | Node version | Use Node 20+ in Project Settings |
| CORS errors | Direct API URL in browser | Use rewrites only; leave `NEXT_PUBLIC_SA_API` unset |

---

## What not to deploy for the full studio

- **`web/modelling-static/`** — old static lookup, not the live SSDK studio.
- **`host_sa.py` on Vercel** — Python API must stay on Render/Railway/Fly, not Vercel.

---

## Updating after code changes

1. Push to GitHub.
2. Render and Vercel redeploy automatically if auto-deploy is on.
3. Re-run the Part C smoke test after API schema or route changes.
