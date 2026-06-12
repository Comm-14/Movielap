# VPS deployment checklist

This project currently has:

- `frontend`: Vite/React static build
- `backend`: FastAPI
- `postgres`: available via `docker-compose.yml`

It does not yet have production `Dockerfile`s, reverse proxy config, or `systemd` units, so deployment should start with a simple, explicit setup.

Production scaffolding is now available in the repository:

- `docker-compose.prod.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `deploy/nginx/movielap.conf`
- `deploy/systemd/movielap-backend.service`
- `deploy/README.md`

## 1. Prepare the VPS

Install the base packages:

```bash
sudo apt update
sudo apt install -y git nginx python3 python3-venv python3-pip nodejs npm certbot python3-certbot-nginx docker.io docker-compose-plugin
```

Open the required ports in the VPS firewall/security group:

- `22` for SSH
- `80` for HTTP
- `443` for HTTPS

## 2. Point the domain to the server

Create DNS records:

- `A` record for `example.com` -> your VPS public IP
- `A` record for `www.example.com` -> your VPS public IP

Wait until DNS resolves correctly before setting up TLS.

## 3. Clone the project on the server

```bash
git clone <repo-url> /opt/movielap
cd /opt/movielap
```

## 4. Start PostgreSQL

```bash
docker compose up -d postgres
docker compose ps
```

By default the database is exposed on host port `5433`.

If you use the production compose file instead, it will run:

- `postgres` in Docker
- `backend` on `127.0.0.1:8000`
- `frontend` on `127.0.0.1:8080`

Command:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 5. Configure backend environment

Create `backend/.env` from `backend/.env.example`.

Required values for this project:

- `DATABASE_URL`
- `TELEGRAM_BOT_USERNAME`
- `TELEGRAM_BOT_TOKEN`
- `GEMINI_API_KEY`
- `TMDB_API_KEY`

Recommended production adjustments:

```env
APP_ENV=production
API_V1_PREFIX=/api
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/moviematch
TELEGRAM_BOT_USERNAME=your_bot_name
TELEGRAM_BOT_TOKEN=your_bot_token
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-lite
TMDB_API_KEY=your_tmdb_api_key
```

Important:

- In `production`, the backend will reject the development fallback auth flow.
- Telegram Mini App auth depends on a valid `TELEGRAM_BOT_TOKEN`.

## 6. Run backend

```bash
cd /opt/movielap/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Quick checks:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/sessions/nonexistent
```

The first endpoint should return `{"status":"ok"}`.

If you want process persistence on the host, use:

```bash
sudo cp deploy/systemd/movielap-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now movielap-backend
```

## 7. Build frontend

The frontend expects `VITE_API_BASE_URL`. For production, point it to your HTTPS domain:

```bash
cd /opt/movielap/frontend
printf 'VITE_API_BASE_URL=https://example.com/api\n' > .env.production
npm install
npm run build
```

The build output will be in `frontend/dist`.

## 8. Configure Nginx

Create `/etc/nginx/sites-available/movielap`:

```nginx
server {
    server_name example.com www.example.com;

    root /opt/movielap/frontend/dist;
    index index.html;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri /index.html;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/movielap /etc/nginx/sites-enabled/movielap
sudo nginx -t
sudo systemctl reload nginx
```

You can also start from the repository template:

```bash
sudo cp deploy/nginx/movielap.conf /etc/nginx/sites-available/movielap
```

## 9. Enable HTTPS

```bash
sudo certbot --nginx -d example.com -d www.example.com
```

Telegram Mini Apps should be served over HTTPS in production.

## 10. Make backend persistent

Create a `systemd` service later if you do not want to keep `uvicorn` in a shell session. At minimum, move backend startup to `systemd` before broader testing.

## 11. Test in this order

1. DNS resolves to the VPS IP.
2. `https://example.com/health` does not exist, but `https://example.com/api/...` routes are reachable through Nginx.
3. `https://example.com` opens the frontend.
4. Browser devtools show frontend requests going to `https://example.com/api`.
5. WebSocket connections to `/ws/sessions/{id}` upgrade successfully.
6. Telegram Mini App opens from the bot and passes valid `initData`.

## 12. Telegram-specific production step

In BotFather:

- set the Mini App URL to `https://example.com`
- make sure the bot username matches `TELEGRAM_BOT_USERNAME`

Without this, Telegram auth and embedded launch testing will be misleading.

## Current gaps before a cleaner production rollout

The repository still needs:

- backend `systemd` unit or Dockerfile
- frontend deployment automation
- production-ready `docker-compose` for app services, not only PostgreSQL
- tighter CORS policy instead of `allow_origins=["*"]`
- secret management strategy for `.env`
