# TestPilot

AI-powered web automation testing. LLMs execute browser tests through visual perception (screenshots) and intelligent decision-making.

## Quick Start

### Prerequisites

- Python 3.11+, Node 18+
- [Playwright browsers](https://playwright.dev/docs/intro)

```bash
# Backend
pip install -r requirements.txt
playwright install chromium
cp .env.example .env        # edit your API keys — DB & tables created automatically
uvicorn src.adapters.api.app:create_app --factory --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                 # → http://localhost:5173
```

### Environment

```env
# LLM API keys (at least one)
MISTRAL_API_KEY=
GOOGLE_API_KEY=
OPENROUTER_API_KEY=

# Optional
DATABASE_PATH=data/web_agent.db
CORS_ORIGINS=http://localhost:5173   # comma-separated for multiple
LOG_LEVEL=INFO
```

## Architecture

```
ADAPTERS          CLI │ FastAPI REST API │ WebSocket │ Database Listener
SERVICES          ExecutionService │ EventBus
AGENT GRAPH       InitStep → Observe → Plan → Execute → Verify → Recover
INFRASTRUCTURE    Browser (Playwright) │ LLM Providers │ Database (SQLite)
```

Data flows: **CLI/API** → `ExecutionService` → `LangGraph` agent → **Browser** + **LLM**.
Events stream back via **EventBus** → **WebSocket** (real-time UI) + **Database Listener** (persistence).

## API

| Method  | Endpoint                                        | Description                    |
| ------- | ----------------------------------------------- | ------------------------------ |
| POST    | `/api/projects`                                 | Create project                 |
| GET     | `/api/projects`                                 | List projects (paginated)      |
| GET     | `/api/projects/{id}`                            | Get project                    |
| PUT     | `/api/projects/{id}`                            | Update project                 |
| DELETE  | `/api/projects/{id}`                            | Delete project                 |
| GET     | `/api/projects/{id}/stats`                      | Project statistics             |
| GET     | `/api/projects/{id}/test-cases`                 | List test cases (paginated)    |
| GET     | `/api/projects/{id}/test-runs`                  | List runs across all cases     |
| POST    | `/api/test-cases`                               | Create test case               |
| GET     | `/api/test-cases`                               | List test cases by project     |
| GET     | `/api/test-cases/{id}`                          | Get test case                  |
| PUT     | `/api/test-cases/{id}`                          | Update test case               |
| DELETE  | `/api/test-cases/{id}`                          | Delete test case               |
| POST    | `/api/test-cases/{id}/run`                      | Execute (sync)                 |
| POST    | `/api/test-cases/{id}/stop`                     | Stop running execution         |
| GET     | `/api/test-cases/{id}/runs`                     | List runs (paginated)          |
| WS      | `/api/test-cases/{id}/execute`                  | Stream execution in real-time  |
| GET     | `/api/test-runs/{id}`                           | Get run details                |
| DELETE  | `/api/test-runs/{id}`                           | Delete run                     |
| GET     | `/api/test-runs/{id}/screenshots`               | List screenshots               |
| GET     | `/api/test-runs/{id}/screenshots/{screenshot_id}` | Download screenshot          |
| GET     | `/api/test-runs/{id}/logs`                      | Get execution logs             |

Pagination: `?page=1&page_size=20` → `{ items, total, page, page_size, pages }`.

### Quick workflow

Test cases are defined with action/assertion step pairs:

```json
{
  "project_id": "{project_id}",
  "name": "Search Test",
  "type": "P",
  "target_url": "https://example.com",
  "steps": [
    {"action": "Type 'hello' in search", "assertion": "Results appear"},
    {"action": "Click first result",     "assertion": "Detail page loads"}
  ]
}
```

```bash
# Create project
P=$(curl -s -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"Demo"}')
PID=$(echo $P | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Create test case
TC=$(curl -s -X POST http://localhost:8000/api/test-cases \
  -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PID\",\"name\":\"Search\",\"type\":\"P\",\"target_url\":\"https://example.com\",\"steps\":[{\"action\":\"Type 'hello'\",\"assertion\":\"Results appear\"}]}")
TCID=$(echo $TC | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Run
curl -s -X POST "http://localhost:8000/api/test-cases/$TCID/run" \
  -H "Content-Type: application/json" \
  -d '{"provider":"mistral","headless":true}' | jq .
```

## WebSocket Events

Connect and stream execution in real-time:

```bash
wscat -c "ws://localhost:8000/api/test-cases/{test_case_id}/execute"

# Optional first message — config:
{"provider": "mistral", "headless": true}
```

| Type | Description |
| ---- | ----------- |
| `execution.started` | Run began |
| `step.started` | Step started |
| `agent.observation` | Page state observed |
| `agent.tool.called` | LLM invoked a tool |
| `agent.tool.result` | Tool returned |
| `verification` | Assertion result |
| `recovery` | Retry decision |
| `step.completed` | Step done |
| `execution.completed` | All steps done |
| `error` | Error occurred |
| `done` | Final summary (WebSocket only) |

Connect via WebSocket to `/api/test-cases/{id}/execute`, optionally send a JSON config as the first message.

## Configuration

### LLM Providers

| Provider    | API key required | Default model (stored per-provider in localStorage) |
| ----------- | ---------------- | --------------------------------------------------- |
| `mistral`   | `MISTRAL_API_KEY`| `mistral-large-2512`                                |
| `google`    | `GOOGLE_API_KEY` | `gemini-3-flash-preview`                            |
| `ollama`    | —                | `gemma4:31b-cloud` (local)                          |
| `openrouter`| `OPENROUTER_API_KEY` | `sourceful/riverflow-v2-pro`                    |
| `llama_cpp` | —                | — (uses `http://127.0.0.1:8080/v1`)                 |

Provider, model, and headless toggle are persisted in `localStorage` per session.

### CORS

`CORS_ORIGINS` env var (default `http://localhost:5173`). Comma-separated for multiple origins.

## Project Structure

```
src/
├── adapters/api/         FastAPI routes, schemas, execution manager
├── domain/               Events, test case model, enums
├── graph/                LangGraph agent: nodes (observe, plan, execute, verify, recover)
├── infrastructure/       Browser (Playwright), LLM providers, database
└── services/             ExecutionService, EventBus
frontend/
├── src/
│   ├── api/              API client functions
│   ├── components/       React components (RunControls, EventFeed, StepTracker, …)
│   ├── hooks/            useLocalStorage, useRunWebSocket
│   └── pages/            Projects, RunDetail
```
