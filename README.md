# KahveCell

KahveCell is a full-stack coffee subscription demo with a FastAPI/SQLAlchemy backend and a React/Vite frontend. It uses SQLite locally and can connect to PostgreSQL in production. Customers can discover Ankara coffee shops, manage a simulated subscription, place orders, and view signed QR codes.

## Project layout

- `backend/` — FastAPI API, SQLAlchemy models, SQLite/PostgreSQL setup, seed scripts, and tests.
- `frontend/` — React application, routing, Leaflet map, and API client.

## Run locally

Start the backend in one PowerShell terminal:

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the frontend at `http://localhost:5173` and the API documentation at `http://localhost:8000/docs`.

The frontend uses `http://localhost:8000/api/v1` by default. Set `VITE_API_BASE_URL` when the API is hosted elsewhere.

## Production deployment

The GitHub repository includes a Render Blueprint for a free FastAPI service and Vercel SPA rewrites for direct page links. Create a free PostgreSQL database with a provider such as Neon, then connect it to Render as `DATABASE_URL`. Render generates the JWT and QR signing secrets from the Blueprint; set `KAHVECELL_CORS_ORIGINS` to the deployed Vercel origin.

Import this repository into Vercel with `frontend/` as the root directory and set `VITE_API_BASE_URL` to the Render API URL ending in `/api/v1`. The free Render service may sleep when idle; its database is external and persists independently.

## Demo behavior

- OTP verification uses a fixed simulated code; no real SMS is sent.
- Subscription payments use test card numbers; no real payment is processed.
- The database and signing keys are local development data and are not included in this repository.
- Seed scripts can be run from the `backend/` directory when demo shop data is needed.
