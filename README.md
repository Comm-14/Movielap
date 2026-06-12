# Movie Match

MVP scaffold for a Telegram Mini App with:

- `frontend`: React + Vite + TypeScript + Tailwind + Telegram Web Apps SDK
- `backend`: FastAPI + SQLAlchemy + Alembic + PostgreSQL

## PostgreSQL via Docker

```bash
docker compose up -d postgres
docker compose ps
```

Backend `.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/moviematch
```

## Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` if the backend is not running on `http://localhost:8000/api`.
