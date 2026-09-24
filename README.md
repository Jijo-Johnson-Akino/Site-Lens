# SiteLens

Website benchmarking and intelligence platform.

## Run locally

Terminal 1 — API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python -m playwright install chromium
uvicorn backend.main:app --reload --port 8001
```

Terminal 2 — app:

```powershell
npm install
npm run dev
```

Open http://localhost:3000

## Health Score

The overall Website Health Score is a weighted aggregation of existing analyzer scores (`backend/scoring/`). Unavailable categories are excluded and remaining weights are renormalized. It is not a prediction of rankings, traffic, revenue, conversions, or business success. See `backend/scoring/README.md`.

## Tests

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```
