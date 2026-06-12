# CI/CD setup

The repository now includes:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`

## CI

`ci.yml` runs on every pull request and on pushes to `main`.

It checks:

- backend dependency installation
- backend module import sanity
- frontend production build
- `docker-compose.prod.yml` validation

## CD

`deploy.yml` uploads the repository to the VPS over SSH and runs:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

It triggers on:

- successful `CI` completion for `main`
- manual run from GitHub Actions

## Required GitHub secrets

Add these repository secrets:

- `VPS_HOST`
- `VPS_USER`
- `VPS_SSH_KEY`
- `VPS_PORT`
- `DEPLOY_PATH`
- `BACKEND_ENV_FILE`

`BACKEND_ENV_FILE` should contain the full contents of `backend/.env`, for example:

```env
APP_NAME=Movie Match API
APP_ENV=production
API_V1_PREFIX=/api
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/moviematch
WEB_APP_BASE_URL=https://example.com
AUTH_TOKEN_SECRET=replace-with-long-random-secret
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com
TELEGRAM_BOT_USERNAME=your_bot_name
TELEGRAM_BOT_TOKEN=your_bot_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-lite
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
TMDB_API_KEY=your_tmdb_api_key
TMDB_API_BASE_URL=https://api.themoviedb.org/3
TMDB_IMAGE_BASE_URL=https://image.tmdb.org/t/p/w500
```

## VPS prerequisites

Before the deploy workflow can succeed, the server must already have:

- Docker
- Docker Compose plugin
- target directory from `DEPLOY_PATH`
- `nginx` configured as the public reverse proxy
- updated `BACKEND_ENV_FILE` secret containing `WEB_APP_BASE_URL`, `AUTH_TOKEN_SECRET`, and `CORS_ALLOWED_ORIGINS`

## Recommended release flow

1. Push a branch and open a pull request.
2. Wait for `CI` to pass.
3. Merge into `main`.
4. `Deploy` runs automatically and refreshes the containers on the VPS.

## Important limitation

The current CD flow deploys from GitHub to a single VPS directly.

That is fine for early-stage testing, but for a cleaner production setup you will likely want later:

- pinned image registry releases
- rollback strategy
- database backup job
- healthcheck-based deploy verification
