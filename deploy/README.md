# Deployment files

This directory contains two deployment approaches for the current project.

CI/CD workflow files are documented in `docs/ci-cd.md`.

## Option 1: Docker Compose

Use:

- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- host `nginx` with `deploy/nginx/movielap.conf`

Recommended flow:

1. Copy the repo to `/opt/movielap`.
2. Create `backend/.env`.
3. Build and run:

```bash
cd /opt/movielap
docker compose -f docker-compose.prod.yml up -d --build
```

4. The compose file already binds:

- frontend to `127.0.0.1:8080`
- backend to `127.0.0.1:8000`

For a simple VPS setup, host `nginx` is still the easiest edge layer.

## Option 2: Host backend via systemd

Use:

- `deploy/systemd/movielap-backend.service`
- host `nginx`
- frontend built into static files

This is simpler when you want:

- backend logs in `journalctl`
- direct `alembic` usage on the host
- fewer moving parts during early testing

## Important note

The included `deploy/nginx/movielap.conf` assumes:

- backend is reachable at `127.0.0.1:8000`
- frontend is reachable at `127.0.0.1:8080`

Adjust those upstreams to match the deployment mode you actually choose.
