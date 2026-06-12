# Deployment Information

## Public URL

https://thriving-reverence-production.up.railway.app

## Platform

Railway

## Test Commands

### Health Check

```powershell
Invoke-RestMethod -Method GET `
  -Uri "https://thriving-reverence-production.up.railway.app/health"
```

Expected:

```text
status: ok
platform: Railway
```

### Agent Test

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://thriving-reverence-production.up.railway.app/ask" `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"question":"Am I on the cloud?"}'
```

Expected:

```text
platform: Railway
```

### Local Final Project Test With Authentication

```powershell
cd C:\code\lqm-day12_ha-tang-cloud_va_deployment\06-lab-complete

$env:AGENT_API_KEY = "YOUR_AGENT_API_KEY"
$env:PORT = "8010"

python -m uvicorn app.main:app --host 0.0.0.0 --port 8010
```

In another terminal:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "http://localhost:8010/ask" `
  -Headers @{ "X-API-Key" = "YOUR_AGENT_API_KEY" } `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"question":"Hello"}'
```

## Environment Variables

- `PORT`
- `AGENT_API_KEY`
- `JWT_SECRET`
- `RATE_LIMIT_PER_MINUTE`
- `DAILY_BUDGET_USD`
- `ALLOWED_ORIGINS`
- `REDIS_URL`

## Screenshots

Screenshots should be added before final submission:

- `screenshots/dashboard.png`
- `screenshots/running.png`
- `screenshots/test.png`
