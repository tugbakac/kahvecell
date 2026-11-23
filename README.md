# KahveCell

KahveCell is a full-stack coffee subscription demo with a FastAPI/SQLite backend and a React/Vite frontend. Customers can discover Ankara coffee shops, manage a simulated subscription, place orders, and view signed QR codes.

## Project layout

- `backend/` — FastAPI API, SQLAlchemy models, SQLite setup, seed scripts, and tests.
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

## Demo behavior

- OTP verification uses a fixed simulated code; no real SMS is sent.
- Subscription payments use test card numbers; no real payment is processed.
- The database and signing keys are local development data and are not included in this repository.
- Seed scripts can be run from the `backend/` directory when demo shop data is needed.

For deployment, host the frontend and API separately. The backend needs a persistent writable location for SQLite and its signing keys; an ephemeral serverless filesystem is not suitable for keeping this demo's data.
