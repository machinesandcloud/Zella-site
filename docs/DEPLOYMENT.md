# Deployment Guide

## Local / Docker

### Backend
- `uvicorn main:app --reload` from `backend/`
  - Defaults to mock IBKR (`USE_MOCK_IBKR=true`) until you install the IBKR API.
  - To use SQLite for persistent local testing: set `USE_SQLITE=true`.

### Frontend
- `npm run dev` from `frontend/`

### Docker Compose
- `docker-compose up --build`
  - Includes Postgres for persistent storage and optional Prometheus + Grafana for monitoring.

## Netlify (Frontend)

This repository is a monorepo. Configure Netlify to build from the `frontend` directory.

Suggested settings:
- Base directory: `frontend`
- Build command: `npm run build` (or `vite build`)
- Publish directory: `dist`

Environment variables (set in Netlify UI):
- `VITE_API_URL` (e.g., the public URL of your backend)
- `VITE_WS_URL` (e.g., `wss://your-backend/ws`)

If you use a custom Node version, define it in Netlify UI or `netlify.toml`.

Optionally, you can add a `netlify.toml` with:

```
[build]
base = "frontend"
command = "npm run build"
publish = "dist"
```

### Can Netlify host the backend too?
Netlify is optimized for static frontends and serverless functions with execution limits. The IBKR trading engine needs a long‑running process with persistent socket connections and WebSockets, which is not a fit for Netlify Functions/Edge Functions. Use a backend host that supports always‑on services (Render, Fly.io, ECS, EC2, etc.), and point the Netlify frontend to that API.

## Backend Hosting

Deploy the backend using a container host (Dockerfile in repo root) or a PaaS that supports Python (Render, Fly.io, ECS, etc.). Ensure the backend is accessible over HTTPS and update `VITE_API_URL` and `VITE_WS_URL` accordingly.

## Render (Backend - Free)

This repo includes a `render.yaml` with a free web service + free Postgres. Deploy by connecting the repo in Render (or via Render CLI) and selecting the `render.yaml` blueprint. The service runs:

- `rootDir: backend`
- `buildCommand: pip install -r requirements.txt`
- `startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT`

After the backend is live, set frontend env vars:
- `VITE_API_URL=https://<render-backend-url>`
- `VITE_WS_URL=wss://<render-backend-url>`

## Monitoring (Free Stack)

The Docker compose file includes a free monitoring stack:
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (user: `admin`, password: `admin`)

Prometheus scrapes the API at `/metrics`.
