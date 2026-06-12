# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. Hardcoded secrets in source code: `OPENAI_API_KEY` and `DATABASE_URL` are written directly in `app.py`.
2. Secret is printed to logs: the app prints `OPENAI_API_KEY` during each `/ask` request.
3. No proper config management: values such as `DEBUG` and `MAX_TOKENS` are hardcoded instead of read from environment variables.
4. Fixed port: the app always uses port `8000` instead of reading `PORT` from the environment.
5. Localhost-only binding: the app binds to `localhost`, so it is not suitable for containers/cloud platforms.
6. Debug reload enabled: `reload=True` is useful for local development but should not be enabled in production.
7. No health check endpoint: cloud platforms cannot reliably detect whether the service is healthy.
8. No graceful shutdown handling: the app does not explicitly handle shutdown lifecycle events.

### Exercise 1.2: Basic version test result
The basic version was run from `01-localhost-vs-production/develop`.

Ask endpoint:

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/ask?question=Hello"
```

Result: the agent returned a mock answer successfully.

Health endpoint:

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/health"
```

Result: `404 Not Found`, because the basic version does not implement a health check.

### Exercise 1.3: Comparison table
| Feature | Basic | Advanced | Why Important? |
|---------|-------|----------|----------------|
| Config | Hardcoded values | Environment variables via `config.py` | Allows different config per environment without code changes. |
| Secrets | Hardcoded and logged | Read from environment and not logged | Prevents accidental secret leaks in GitHub/logs. |
| Host binding | `localhost` | `0.0.0.0` | Required for containers and cloud routing. |
| Port | Fixed `8000` | Reads `PORT` env var | Cloud platforms inject the runtime port dynamically. |
| Health check | Missing | `/health` endpoint | Platforms can detect and restart unhealthy services. |
| Readiness check | Missing | `/ready` endpoint | Load balancers can avoid routing traffic before startup finishes. |
| Logging | `print()` debug logs | Structured JSON logging | Easier to search, parse, and monitor in production. |
| Shutdown | No lifecycle handling | Lifespan startup/shutdown and SIGTERM handler | Allows graceful cleanup during deploys or restarts. |

### Checkpoint 1
- Hardcoded secrets are dangerous because they can leak through Git history, logs, or public repositories.
- Environment variables separate deploy-time configuration from source code.
- Health checks let platforms know whether the service should stay running or be restarted.
- Graceful shutdown gives the app time to finish in-flight work before exiting.

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image: `python:3.11`.
2. Working directory: `/app`.
3. `requirements.txt` is copied before source code so Docker can cache the dependency installation layer. If only app code changes, Docker does not need to reinstall dependencies.
4. `CMD` provides the default command for a container and can be overridden at `docker run` time. `ENTRYPOINT` defines the main executable and is harder to override; it is usually used when the container should always run a specific program.

### Exercise 2.2: Build and run
Develop image build command:

```powershell
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
```

Run command:

```powershell
docker run -d -p 8000:8000 --name my-agent-develop-lab my-agent:develop
```

Test results:

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8000/health"
Invoke-RestMethod -Method POST -Uri "http://localhost:8000/ask?question=What%20is%20Docker%3F"
```

Result: `/health` returned `status: ok`; `/ask` returned a mock Docker explanation.

Image size:

```text
my-agent:develop: 1.66GB disk usage, 424MB content size
```

### Exercise 2.3: Multi-stage build
Stage 1, `builder`, installs build dependencies and Python packages. This stage may include tools such as `gcc` and `libpq-dev`.

Stage 2, `runtime`, starts from a smaller `python:3.11-slim` image, creates a non-root user, copies only installed packages and application files, and runs the app.

The image is smaller because build tools and temporary build layers are not included in the final runtime image.

Build command:

```powershell
docker build -f 02-docker/production/Dockerfile -t my-agent:advanced .
```

Image size comparison:

```text
Develop: 1.66GB disk usage, 424MB content size
Advanced: 236MB disk usage, 56.6MB content size
```

Approximate disk usage reduction: about 86%.

### Exercise 2.4: Docker Compose stack
Services started:

```text
agent
redis
qdrant
nginx
```

Architecture:

```text
Client
  |
  v
Nginx reverse proxy / load balancer
  |
  v
FastAPI agent
  | \
  |  \-- Qdrant vector database
  |
  \-- Redis cache / rate limiting store
```

Communication:
- The client talks only to Nginx on ports `80` and `443`.
- Nginx proxies requests to the internal `agent` service on port `8000`.
- The agent can connect to Redis using `redis://redis:6379/0`.
- The agent can connect to Qdrant using `http://qdrant:6333`.
- All services share the internal Docker network.

Compose test results:

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost/health"
Invoke-RestMethod -Method POST -Uri "http://localhost/ask" -ContentType "application/json; charset=utf-8" -Body '{"question":"Explain microservices"}'
```

Result: both requests succeeded through Nginx.

### Checkpoint 2
- A Dockerfile packages the app, dependencies, runtime, and startup command.
- Multi-stage builds reduce final image size by excluding build-only tools.
- Docker Compose can orchestrate multiple services and a shared network.
- Useful debug commands include `docker logs`, `docker ps`, `docker exec`, and `docker compose ps`.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
Public URL:

```text
https://thriving-reverence-production.up.railway.app
```

Health check:

```powershell
Invoke-RestMethod -Method GET -Uri "https://thriving-reverence-production.up.railway.app/health"
```

Result:

```text
status: ok
platform: Railway
```

Agent endpoint:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "https://thriving-reverence-production.up.railway.app/ask" `
  -ContentType "application/json; charset=utf-8" `
  -Body '{"question":"Am I on the cloud?"}'
```

Result: the app returned a mock answer with `platform: Railway`.

Screenshot: to be added in `screenshots/` before final submission.

### Exercise 3.2: Render vs Railway
| Feature | Railway | Render |
|---------|---------|--------|
| Config file | `railway.toml` | `render.yaml` |
| Build config | Uses Nixpacks via `builder = "NIXPACKS"` | Uses explicit `buildCommand` |
| Start command | `uvicorn app:app --host 0.0.0.0 --port $PORT` | Same style, defined as `startCommand` |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Secrets | Set through Railway variables/dashboard | Set through Render dashboard or generated values |
| Extra services | Not defined in this file | Defines both web service and Redis service |
| Deployment flow | CLI or dashboard deploy | GitHub Blueprint deploy |

### Exercise 3.3: Cloud Run notes
`cloudbuild.yaml` defines a CI/CD pipeline:

1. Run tests with Python.
2. Build Docker image.
3. Push image to Google Container Registry.
4. Deploy image to Cloud Run.

`service.yaml` defines the Cloud Run service:

- Public ingress.
- Autoscaling from 1 to 10 instances.
- Container port `8000`.
- CPU and memory limits.
- Environment variables and secrets from Secret Manager.
- `/health` liveness probe and `/ready` startup probe.

### Checkpoint 3
- Railway deployment is live.
- Public URL is accessible.
- Environment variables can be set through platform CLI/dashboard.
- Logs are viewed from the platform dashboard or CLI.

## Part 4: API Security

### Exercise 4.1: API Key authentication
The API key is checked in `04-api-gateway/develop/app.py` by the `verify_api_key` dependency.

Where it checks:

```python
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
```

The `/ask` endpoint depends on:

```python
_key: str = Depends(verify_api_key)
```

Behavior:
- Missing key returns `401`.
- Wrong key returns `403`.
- Correct key allows the request.

To rotate the key, change the `AGENT_API_KEY` environment variable and restart/redeploy the service. Clients must then send the new value in the `X-API-Key` header.

Local test key:

```text
YOUR_AGENT_API_KEY
```

Test results on port `8001`:

```text
GET /health: 200 OK
POST /ask without key: 401
POST /ask with X-API-Key: YOUR_AGENT_API_KEY: 200 OK
```

### Exercise 4.2: JWT authentication
JWT flow:

1. Client sends username/password to `/auth/token`.
2. Server validates credentials in `authenticate_user`.
3. Server creates a signed JWT using `create_token`.
4. Client sends the token in `Authorization: Bearer <token>`.
5. `verify_token` decodes and verifies the token on protected endpoints.

Demo credentials:

```text
student / demo123 -> role: user
teacher / teach456 -> role: admin
```

Test result on port `8003`:

```text
POST /ask without token: 401
POST /auth/token with student/demo123: token returned
POST /ask with Bearer token: 200 OK
```

### Exercise 4.3: Rate limiting
Algorithm: sliding window counter.

Implementation:
- Each user has a deque of request timestamps.
- Old timestamps outside the 60 second window are removed.
- If active timestamps exceed the limit, the app returns `429 Too Many Requests`.

Limits:

```text
User: 10 requests/minute
Admin: 100 requests/minute
```

Admin bypass is implemented by selecting a different limiter:

```python
limiter = rate_limiter_admin if role == "admin" else rate_limiter_user
```

Rate limit test result for `student`:

```text
1: 200
2: 200
3: 200
4: 200
5: 200
6: 200
7: 200
8: 200
9: 200
10: 429
11: 429
12: 429
```

Some quota was already used before the loop, so the 10th loop request hit the limit.

### Exercise 4.4: Cost guard implementation
The repository already includes an in-memory cost guard in `04-api-gateway/production/cost_guard.py`.

Current behavior:
- Per-user daily budget: `$1/day`.
- Global daily budget: `$10/day`.
- Tracks input tokens, output tokens, request count, and estimated cost.
- Blocks user when daily budget is exceeded with `402`.
- Blocks globally when service budget is exceeded with `503`.

Test result:

```text
GET /me/usage returned usage for student:
requests: 1
cost_usd: 0.000021
budget_usd: 1.0
budget_remaining_usd: 0.999979
```

Production note: this demo uses in-memory storage. A real production deployment should move usage records to Redis or a database so the limit works across multiple replicas.

### Checkpoint 4
- API key authentication works.
- JWT login and Bearer token verification work.
- Sliding-window rate limiting works.
- Cost guard tracks estimated usage and budget.

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks
The develop app implements:

```text
GET /health -> liveness probe
GET /ready  -> readiness probe
```

Local test on port `8004`:

```text
GET /health: 200 OK, status: ok
GET /ready: 200 OK, ready: true
POST /ask?question=Long%20task: 200 OK
```

`/health` returns uptime, version, environment, timestamp, and dependency checks. `/ready` returns `503` when the app is not ready and `200` when it can receive traffic.

### Exercise 5.2: Graceful shutdown
The develop app uses FastAPI lifespan and signal handlers:

- On startup, it loads dependencies and sets `_is_ready = True`.
- Middleware tracks `_in_flight_requests`.
- On shutdown, it sets `_is_ready = False`.
- It waits up to 30 seconds for in-flight requests to finish.
- Uvicorn runs with `timeout_graceful_shutdown=30`.

This allows platforms to stop routing new traffic while the app finishes active requests.

### Exercise 5.3: Stateless design
The production app stores conversation state outside the app process:

```text
session:{session_id} -> Redis
```

Why this matters:
- With in-memory state, each replica has its own separate history.
- With Redis, any replica can read/write the same session.
- This makes horizontal scaling safe.

The app falls back to in-memory storage if Redis is unavailable, but that mode is marked as not scalable.

### Exercise 5.4: Load balancing
Docker Compose was run with:

```powershell
docker compose -p scaling up -d --scale agent=3
```

The stack includes:

```text
nginx -> 3 agent replicas -> redis
```

Nginx exposes port `8080` and proxies requests to the agent replicas.

### Exercise 5.5: Test stateless
The stateless test was run with UTF-8 output:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python test_stateless.py
```

Result:

```text
Total requests: 5
Instances used: {'instance-0a14de', 'instance-d3e639', 'instance-f66c04'}
All requests served despite different instances.
Total messages: 10
Session history preserved across all instances via Redis.
```

The first attempt failed only because Windows console encoding `cp1252` could not print Vietnamese characters. Re-running with `PYTHONIOENCODING=utf-8` fixed the output.

### Checkpoint 5
- Health and readiness checks work.
- Graceful shutdown is implemented through FastAPI lifespan and Uvicorn shutdown timeout.
- Session state is stored in Redis, not process memory.
- Nginx load balances traffic across 3 agent replicas.
- Stateless behavior was validated by `test_stateless.py`.

## Part 6: Final Project

### Production-ready validation
The final project in `06-lab-complete` was checked with:

```powershell
$env:PYTHONIOENCODING = "utf-8"
python check_production_ready.py
```

Result:

```text
20/20 checks passed (100%)
PRODUCTION READY
```

### Runtime fixes
The final project was missing `utils/mock_llm.py`, while `app/main.py` imports `utils.mock_llm` and the Dockerfile copies `utils/`. A local mock LLM file was added so the final project runs independently.

The request middleware also used `response.headers.pop(...)`, but Starlette `MutableHeaders` does not support `.pop()`. It was fixed to:

```python
if "server" in response.headers:
    del response.headers["server"]
```

### Local final project test
The final app was run on port `8010` with:

```text
AGENT_API_KEY=YOUR_AGENT_API_KEY
RATE_LIMIT_PER_MINUTE=5
```

Test results:

```text
GET /health: 200 OK
GET /ready: 200 OK
POST /ask without X-API-Key: 401
POST /ask with X-API-Key: YOUR_AGENT_API_KEY: 200 OK
Rate limit test: later requests returned 429
```

### Final project notes
- API key authentication is implemented.
- Rate limiting is implemented.
- Cost guard is implemented.
- Health and readiness checks are implemented.
- Graceful shutdown uses SIGTERM handling and Uvicorn graceful timeout.
- Structured JSON logging is implemented.
- Multi-stage Dockerfile and `.dockerignore` are present.
