# CloudFlow frontend

React + Vite interface for the real FastAPI/LangGraph workflow. No mock pipeline data is used.

```bash
npm ci
npm run dev
```

Start FastAPI at `127.0.0.1:8000`; Vite forwards `/api` requests to it. The root project launcher starts both services. Optional API configuration belongs in `frontend/.env` (copy `.env.example`).

Routes: `/new-run`, `/pipeline/:runId`, `/history`, `/experiments`, `/settings`. One API client handles uploads, preview, polling, review, cancellation, experiments, artifacts and inference. Plotly is dynamically loaded only for result charts.

```bash
npm run lint
npm run build
npx playwright test
```

Browser tests require the running backend/worker and Vite, plus Microsoft Edge (or an adjusted Playwright channel). See the root README and `docs/API.md` for contracts and setup.
