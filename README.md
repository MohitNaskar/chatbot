# Ask Mohit — AI Portfolio Assistant Backend

A lightweight FastAPI backend that powers the **Ask Mohit** chatbot on [mohitnaskar.vercel.app](https://mohitnaskar.vercel.app/). Visitors can ask questions about Mohit's experience, projects, skills and engineering work and receive grounded, context-aware answers.

---

## Architecture

```
Request → FastAPI → Rate limiter → Chat endpoint
                                       ↓
                             Conversation service  ←→  In-memory session store
                                       ↓
                              LLM service (Google Gemini)
                                       ↑
                             System prompt  ←  Context service
                                                     ↑
                                              Knowledge base (JSON + Markdown)
```

The system prompt is built once at startup by injecting the knowledge base into a fixed instruction template. Each request attaches the session's conversation history so the model maintains context across turns.

---

## Tech stack

| Layer | Technology |
|---|---|
| API framework | FastAPI + Uvicorn |
| LLM provider | Google Gemini (via `google-genai`) |
| Session store | In-memory (replace with Redis for multi-instance) |
| Rate limiting | slowapi |
| Validation | Pydantic v2 |
| Testing | pytest + httpx |

---

## Folder structure

```
portfolio-ai-backend/
├── app/
│   ├── main.py                  # FastAPI app, CORS, lifespan
│   ├── config.py                # Settings from env vars
│   ├── rate_limit.py            # Shared slowapi limiter
│   ├── schemas/chat.py          # Pydantic request/response models
│   ├── services/
│   │   ├── context_service.py   # Loads and caches knowledge base
│   │   ├── conversation_service.py  # In-memory session management
│   │   └── llm_service.py       # Google Gemini calls (sync + streaming)
│   ├── prompts/system_prompt.py # System prompt builder
│   └── api/
│       ├── health.py            # GET /health
│       └── chat.py              # POST /chat and POST /chat/stream
├── knowledge/
│   ├── profile.json
│   ├── experience.json
│   ├── skills.json
│   ├── achievements.json
│   ├── education.json
│   ├── projects/
│   │   ├── movie_recommender.json
│   │   ├── llm_experiments.json
│   │   ├── topic_modelling.json
│   │   └── other_projects.json
│   └── technical_notes/
│       ├── machine_learning.md
│       ├── deep_learning.md
│       └── llms.md
└── tests/
    ├── conftest.py
    ├── test_health.py
    └── test_chat.py
```

---

## Local setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd portfolio-ai-backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set LLM_API_KEY
```

Get a free Google Gemini API key at [aistudio.google.com](https://aistudio.google.com/).

### 4. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | — | **Required.** Google Gemini API key |
| `LLM_MODEL` | `gemini-3.8-flash` | Model name |
| `LLM_TEMPERATURE` | `0.7` | Generation temperature |
| `LLM_MAX_OUTPUT_TOKENS` | `1024` | Max tokens per response |
| `PORT` | `8000` | Server port |
| `ALLOWED_ORIGINS` | `localhost + vercel` | Comma-separated CORS origins |
| `MAX_HISTORY_MESSAGES` | `10` | Message pairs kept per session |
| `SESSION_TTL_SECONDS` | `3600` | Idle session expiry (1 hour) |

---

## API endpoints

### `GET /health`

Returns `{"status": "ok", "version": "1.0.0"}`. Used for deployment health checks.

### `POST /chat`

```json
// Request
{ "message": "Tell me about Mohit's projects", "session_id": "optional-uuid" }

// Response
{ "response": "Mohit has worked on...", "session_id": "uuid" }
```

### `POST /chat/stream`

Same request body as `/chat`. Returns a `text/event-stream` response.

Each event is a JSON object on a `data:` line:

```
data: {"type": "chunk", "content": "Mohit"}
data: {"type": "chunk", "content": " has worked on..."}
data: {"type": "done", "session_id": "uuid"}
data: {"type": "error", "message": "..."}  // on failure
```

Rate limits: 20 requests/minute, 100 requests/hour per IP.

---

## Knowledge base

Located in `knowledge/`. All chatbot responses are grounded in this content.

**To update the knowledge base:** Edit the JSON/Markdown files and restart the server (the context is cached at startup).

**Files that need manual completion:**
- `knowledge/education.json` — formal education details not publicly documented
- More technical notes can be added under `knowledge/technical_notes/`

---

## Session management

Sessions are stored in memory in `conversation_service.py`. Each session keeps the last `MAX_HISTORY_MESSAGES` user+model pairs to maintain conversation context.

**Production note:** The in-memory store is wiped on server restart. For persistent sessions across deployments, replace `_sessions` in `conversation_service.py` with a Redis or database-backed implementation — the interface (`get_or_create_session`, `get_history`, `add_exchange`, `reset_session`) is intentionally isolated to that module.

---

## Testing

```bash
pytest tests/ -v
```

LLM calls are mocked in tests — no real API calls are made.

---

## Security

- All user messages validated by Pydantic (max 2000 chars, no blank messages)
- Rate limiting per IP via slowapi
- CORS restricted to configured origins only
- System prompt instructs the model to treat user input as untrusted
- Stack traces never exposed in API responses
- No session data stored beyond conversation history

---

## Deployment on Render

1. Create a new **Web Service** on [render.com](https://render.com)
2. Connect this repository
3. Set the start command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
4. Add environment variables under **Environment**:
   - `LLM_API_KEY` — your Gemini API key
   - `ALLOWED_ORIGINS` — `https://mohitnaskar.vercel.app`
   - Any other overrides from `.env.example`

The `/health` endpoint is suitable for Render's health check configuration.

---

## Vercel integration (portfolio frontend)

In the portfolio's `.env` (or Vercel environment variables), set:

```
VITE_CHATBOT_API_URL=https://your-render-service.onrender.com
```

The chatbot frontend reads this URL from `import.meta.env.VITE_CHATBOT_API_URL`.

---

## Future improvements

- Replace in-memory session store with Redis for multi-instance deployments
- Add RAG: embed knowledge base chunks, retrieve top-k by cosine similarity
- Add conversation export / analytics
- Add `/chat/reset` endpoint for explicit session reset
- Add structured logging (JSON) for production observability
