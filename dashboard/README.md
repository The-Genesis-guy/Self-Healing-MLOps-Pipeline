# Dashboard

This is the React 19 + TypeScript + Vite frontend for the GUARDIAN self-healing pipeline.

## What It Shows

- Live pipeline state and execution controls
- Drift radar, performance history, model registry, and event logs
- Prometheus metrics summaries fetched from `/metrics/json`

## Runtime Requirements

- Node.js 20.19+ for local development and Docker compose
- The dashboard uses the Vite dev server on port 5173 by default

## API Flow

The dashboard polls the backend every 2 seconds for:

- `/pipeline/status`
- `/pipeline/history`
- `/models`
- `/metrics/json`

The raw `/metrics` endpoint remains available for external Prometheus scraping.

## Local Development

```bash
cd dashboard
npm install
npm run dev
```

## Build

```bash
cd dashboard
npm run build
```

## Notes

- If the Vite build complains about missing native bindings, reinstall dependencies with `npm install` in the dashboard directory.
- The compose setup should use Node 20.19 or newer for the dashboard container.
