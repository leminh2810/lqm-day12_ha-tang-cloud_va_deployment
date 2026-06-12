# Lab 12 - Complete Production Agent

This project combines the Day 12 deployment requirements with the Day 9 legal
multi-agent system design.

The Day 9 source used as inspiration is:

```text
C:\code\LQM-Batch02-Day9_Multi-Agent_MCP-A2A
```

The original Day 9 project runs distributed A2A services:

```text
Customer Agent -> Law Agent -> Tax Agent / Compliance Agent -> Aggregate
```

For this Day 12 final project, the same flow is adapted into an in-process
engine so the service remains small, Docker-friendly, and easy to deploy.

## Checklist

- [x] Multi-stage Dockerfile
- [x] Docker Compose with agent + Redis
- [x] `.dockerignore`
- [x] `GET /health`
- [x] `GET /ready`
- [x] API key authentication
- [x] Rate limiting
- [x] Monthly cost guard
- [x] Config from environment variables
- [x] Structured JSON logging
- [x] Graceful shutdown
- [x] Conversation history with Redis/in-memory fallback
- [x] Day 9 legal multi-agent flow
- [x] Railway and Render config files

## Structure

```text
06-lab-complete/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI entry point
│   ├── config.py        # 12-factor config
│   ├── auth.py          # API key authentication
│   ├── rate_limiter.py  # Redis-backed rate limiting with memory fallback
│   ├── cost_guard.py    # Monthly budget protection
│   ├── session_store.py # Redis-backed conversation history
│   └── legal_agents.py  # Day 9 legal multi-agent flow
├── utils/
│   └── mock_llm.py
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── render.yaml
├── .env.example
├── .dockerignore
└── requirements.txt
```

## Run Locally

PowerShell:

```powershell
cd C:\code\lqm-day12_ha-tang-cloud_va_deployment\06-lab-complete

$env:AGENT_API_KEY = "YOUR_AGENT_API_KEY"
$env:PORT = "8010"
$env:RATE_LIMIT_PER_MINUTE = "10"
$env:MONTHLY_BUDGET_USD = "10.0"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

In another terminal:

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8010/health"
Invoke-RestMethod -Method GET -Uri "http://localhost:8010/ready"
```

Ask the multi-agent legal system:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8010/ask" `
  -Headers @{ "X-API-Key" = "YOUR_AGENT_API_KEY" } `
  -ContentType "application/json" `
  -Body '{"user_id":"student","question":"If a company breaks a contract and avoids taxes, what are the legal and regulatory consequences?"}'
```

Expected response includes:

- `answer`
- `session_id`
- `trace_id`
- `specialists.tax`
- `specialists.compliance`
- `usage.rate_limit`
- `usage.budget`

## Conversation History

Use the returned `session_id`:

```powershell
Invoke-RestMethod -Method GET `
  -Uri "http://localhost:8010/sessions/<session_id>/history" `
  -Headers @{ "X-API-Key" = "YOUR_AGENT_API_KEY" }
```

## Docker Compose

Create `.env.local` from `.env.example`, then run:

```powershell
docker compose up --build
```

Test:

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/health"
```

## Production Readiness Check

```powershell
$env:PYTHONIOENCODING = "utf-8"
python check_production_ready.py
```

Expected:

```text
20/20 checks passed
```

## Deploy

Railway:

```powershell
railway login
railway init
railway variables set AGENT_API_KEY=your-secret-key
railway variables set MONTHLY_BUDGET_USD=10
railway up
railway domain
```

Render:

1. Push the repository to GitHub.
2. Create a Render Blueprint.
3. Connect this repo.
4. Set `AGENT_API_KEY` and other secrets in the dashboard.
5. Deploy.
