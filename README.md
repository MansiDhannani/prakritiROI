# EcoValue India — Prakriti ROI Valuation Engine

FastAPI backend and valuation engine for the India Ecosystem Services Valuation Engine (Prakriti ROI).

---

## Core Features

1. **Ecosystem Valuation Engine**: Computes annual services and 10-year Net Present Value (NPV) using regional multipliers (FSI ISFR, TEEB India Sukhdev, TERI).
2. **Land Use Scenario Comparison**: Compares conservation, restoration, and alternative land uses (e.g., solar farms, infrastructure development) over 10-year horizons.
3. **Pure-Python RAG System**: Custom TF-IDF vector store (`app/services/vector_store.py`) that indexes and searches Indian case studies and coefficients offline.
4. **AI Policy Briefs (Groq AI)**: Automatically retrieves RAG context and uses the `qwen/qwen3.8-27b` model via the official `groq` SDK to generate grounded policy narratives.
5. **Human-Scale Impact Metrics**: Converts monetary valuations into tangible quantities (e.g., "people supplied clean water", "mature trees equivalent").
6. **Real-Time WebSocket Ticker**: Broadcasts live valuation session updates to all connected dashboard instances.
7. **PDF Report Downloader**: Generates print-ready PDF briefs containing valuation charts, scenario breakdowns, and AI narratives via ReportLab.

---

## Quick Start & Setup

### 1. Install Dependencies
Ensure you have Python 3.10+ installed. Install the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy the example environment file:
```bash
cp .env.example .env
```
Open `.env` and configure your credentials:
- `GROQ_API_KEY`: Get a free key at [console.groq.com](https://console.groq.com) (no credit card needed).
- `DATABASE_URL`: Leave blank to automatically use the local SQLite database (`ecovalue.db`).

### 3. Run the Server
Start the Uvicorn ASGI server:
```bash
python run.py
```
- **Web Application**: Access the dashboard at [http://localhost:8000](http://localhost:8000)
- **API Documentation**: Visit the Swagger interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs)

---

## API Endpoints

### HTML & Frontend Routes
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/` / `/index` | Main Landing Page |
| GET    | `/dashboard` | Interactive Valuations Dashboard |
| GET    | `/history` | Past Valuations History Logs |
| GET    | `/about` | Methodology & Framework References |
| GET    | `/live` | Real-Time Viewer & Live WebSocket Feed |
| GET    | `/ecosystem_dashboard` | Comparative Ecosystem Coefficient Explorer |

### REST API v1 Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/health` | Server Health Status |
| GET    | `/api/v1/regions` | Get list of regions and multipliers |
| GET    | `/api/v1/ecosystems` | Get list of ecosystems and services |
| POST   | `/api/v1/valuate` | Run ecosystem NPV & carbon valuation (saves to DB) |
| POST   | `/api/v1/scenarios/compare` | Run NPV comparative analysis across scenarios |
| POST   | `/api/v1/impact` | Convert valuation data into human-scale cards |
| POST   | `/api/v1/report/narrative` | Generate RAG-grounded AI policy brief (Groq AI) |
| POST   | `/api/v1/report/pdf/download` | Direct binary download of ReportLab PDF |
| GET    | `/api/v1/history` | List past valuation records |
| GET    | `/api/v1/analytics` | Get aggregated database stats |
| GET    | `/api/v1/parcels` | List synthetic land parcels for lookup |
| GET    | `/api/v1/parcel/{id}` | Retrieve details for a specific land parcel |

### RAG Administration
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/v1/rag/search` | Search RAG database directly (debugging) |
| GET    | `/api/v1/rag/stats` | View index statistics |
| POST   | `/api/v1/rag/rebuild` | Force-rebuild index from source coefficients |

### WebSockets
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS       | `/api/v1/ws/ticker` | Broadcasts new valuation logs to ticker managers |

---

## Project Structure

```
prakritiROI-main/
├── run.py                      # Server entry point
├── main.py                     # Root FastAPI application & route register
├── live.py                     # WebSockets ticker and /impact router
├── requirements.txt            # Project dependencies
├── .env.example                # Config template
├── index.html                  # Landing page
├── dashboard.html              # Core dashboard
├── history.html                # Valuation history UI
├── about.html                  # Framework overview UI
├── live.html                   # WebSocket ticker visualizer
├── ecosystem_dashboard.html    # Coefficients explorer UI
├── app/
│   ├── data/
│   │   └── coefficients.py     # Indian ecosystem service databases
│   ├── models/
│   │   ├── database.py         # SQLAlchemy database initialization (SQLite/Postgres)
│   │   └── schemas.py          # Pydantic request/response validation schemas
│   └── services/
│       ├── valuation_engine.py # Valuation & NPV math logic
│       ├── narrative_service.py# Groq SDK AI narrator (uses qwen/qwen3.8-27b)
│       ├── pdf_service.py      # ReportLab PDF document builder
│       ├── rag_service.py      # TF-IDF RAG document generator
│       └── vector_store.py     # Custom pure-Python vector search store
└── static/                     # CSS stylesheets and client Javascript files
```

---

## Deployment

- **Railway**: Uses the configured `railway.toml` and database env injections out-of-the-box. Run `railway up`.
- **Render**: Create a Web Service with the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`. Ensure you inject the `GROQ_API_KEY` environment variable.
