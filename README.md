# Chat With Multiple PDFs

**Agentic RAG with isolated long-term memory.**

Create multiple independent **sets**, each with its own uploaded PDFs, document retrieval, and conversation memory. Nothing is shared across sets, similar to the concept of Claude Projects.

## Architecture

### Backend — FastAPI

* **SQLite** stores sets and recent chat messages. Messages act as a short-term buffer.
* **Qdrant** uses two isolated collections per set:

  * `<set_id>_docs` — document chunks
  * `<set_id>_memory` — compacted conversation memory
* **NVIDIA embeddings** are used for both documents and memory.
* Retrieval is **agentic** using a LangChain ReAct agent with two tools:

  * Document search
  * Long-term memory search
* The agent and tools are built **fresh for every request**, preventing cross-set state reuse.
* **Gemini** handles chat responses, while **Groq** is used for memory compaction.
* The agent is strictly grounded in retrieved tool output and must state when the required information is unavailable.

### Long-Term Memory

Memory uses a tiered approach:

1. The latest `RECENT_MESSAGES_LIMIT` messages remain in SQLite and are included directly in the prompt.
2. When the limit is exceeded, the oldest **3/4 of the stored messages** are summarized in one LLM call.
3. The summary is embedded into the set's `<set_id>_memory` collection.
4. The summarized messages are then removed from SQLite.

Compaction is **synchronous by design**, trading some response time for a simpler architecture.

### Document Capacity

Each set is limited to **150 chunks**, enforced server-side before embedding.

The limit applies to **chunks**, not files or character count. Since chunks are the retrieval unit and the system uses `top_k=3` without reranking, the cap keeps each set bounded.

When a set reaches the limit, create a new set for additional material.

### Frontend — Streamlit

* **Left sidebar:** theme toggle, set switcher, and new-set form.
* **Center panel:** chat interface for the active set.
* **Right panel:** chunk-capacity gauge, PDF upload, and document cards.
* All backend communication uses **HTTP requests**; the frontend does not import backend modules.
* Chat history is maintained in Streamlit `session_state` for the current browser session.
* Chat remains hidden until the active set contains at least one document.

## Tech Stack

**FastAPI · SQLite · Qdrant · LangChain · Gemini · Groq · NVIDIA Embeddings · Streamlit**

## Project Structure

```text
.
├── main.py                     # FastAPI entrypoint
├── config.py                   # Environment configuration
├── api/
│   └── routes.py               # HTTP endpoints
├── agent/
│   ├── build_agent.py          # ReAct agent factory
│   ├── chat.py                 # Chat orchestration
│   ├── compaction.py           # Memory compaction
│   ├── prompt.py               # Prompt templates
│   └── tools.py                # Retrieval tools
├── vectorstore/
│   ├── qdrant_client.py        # On-disk Qdrant client
│   ├── collections.py          # Collection lifecycle
│   └── ingest.py               # PDF chunking and ingestion
├── db/
│   ├── database.py              # SQLite schema
│   └── crud.py                  # Database operations
├── frontend/
│   ├── app.py                   # Streamlit application
│   ├── api_client.py            # Backend HTTP client
│   └── styles.py                # Theme styling
├── .streamlit/
│   └── config.toml
├── data/                        # SQLite + Qdrant storage
├── requirements.txt
└── .env.example
```

## Setup

### 1. Clone and install

```bash
git clone <your-repo-url>
cd chat-with-multiple-pdfs

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Add your:

```text
GROQ_API_KEY
NVIDIA_API_KEY
GEMINI_API_KEY
```

Configure the model and embedding settings as required.

`QDRANT_PATH` and `SQLITE_CONNECTION_PATH` already point to `./data/` by default.

### 3. Run the backend

```bash
python -m uvicorn main:app
```

Run a **single backend process**. The on-disk Qdrant storage should not be shared across multiple workers or backend instances using the same data directory.

### 4. Run the frontend

In a second terminal:

```bash
python -m streamlit run frontend/app.py
```

Run it from the repository root so Streamlit resolves `.streamlit/config.toml` correctly.

For a remote backend, set:

```text
BACKEND_URL=<backend-url>
```

## API Reference

| Method | Endpoint                   | Purpose                                       |
| ------ | -------------------------- | --------------------------------------------- |
| `POST` | `/sets`                    | Create a set                                  |
| `GET`  | `/sets`                    | List sets                                     |
| `POST` | `/sets/{set_id}/documents` | Upload a PDF                                  |
| `GET`  | `/sets/{set_id}/documents` | List uploaded documents                       |
| `POST` | `/sets/{set_id}/chat`      | Send a message and receive the agent response |
| `GET`  | `/sets/{set_id}/status`    | Get message count, chunk count, and capacity  |

## Limitations

* **150 chunks per set** limits the amount of document content that can be indexed.
* **Retrieval uses `top_k=3` without reranking**, so highly distributed information may not always be retrieved together.
* **Memory compaction is synchronous**, which can increase response time when summarization is triggered.
* **Session-based chat history** is limited to the current Streamlit browser session; long-term memory is stored separately in Qdrant.
* **On-disk Qdrant** is intended for a single backend process rather than horizontally scaled workers.
