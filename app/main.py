from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.routers import valuation, report, scenarios, health, analytics, live

# ── LOAD ENV VARIABLES (including GROQ_API_KEY) ──────────────────────────────
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    from app.models.database import init_db
    init_db()
    print("[OK] Database initialised")

    # Pre-load RAG index (builds from coefficients on first run, loads from disk after)
    try:
        if not os.path.exists("india_ecosystem_coefficients.json"):
            print("[WARN] Warning: india_ecosystem_coefficients.json not found. RAG index may be empty.")
            
        from app.services.rag_service import get_store
        store = get_store()
        print(f"[OK] RAG index ready: {store.count()} documents")
    except Exception as e:
        print(f"[WARN] RAG index failed to load: {e}")

    yield
    # ── Shutdown ──────────────────────────────────────────────────────────────


app = FastAPI(
    title="EcoValue India API",
    description=(
        "Ecosystem Services Valuation Engine for India.\n\n"
        "Features: Valuation API · Scenario Comparison · RAG-powered AI Narratives · PDF Reports · SQLite/Postgres Storage"
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files so the browser can fetch your CSS and JS
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(health.router,      tags=["Health"])
app.include_router(valuation.router,   prefix="/api/v1", tags=["Valuation"])
app.include_router(scenarios.router,   prefix="/api/v1", tags=["Scenarios"])
app.include_router(report.router,      prefix="/api/v1", tags=["Reports"])
app.include_router(analytics.router,   prefix="/api/v1", tags=["Analytics & History"])
app.include_router(live.router,        prefix="/api/v1", tags=["Live & Impact"])


@app.get("/")
async def serve_root():
    """Serve the landing page at the root URL"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    return FileResponse(html_path, media_type="text/html")


# ── RAG admin endpoints ───────────────────────────────────────────────────────
from fastapi import APIRouter
rag_router = APIRouter(prefix="/api/v1/rag", tags=["RAG Knowledge Base"])

@rag_router.get("/search")
def rag_search(q: str, k: int = 5, ecosystem: str = None, region: str = None):
    """Search the RAG knowledge base directly. Good for debugging what context the AI sees."""
    from app.services.rag_service import get_store, retrieve_context
    store = get_store()
    if not store:
        raise HTTPException(status_code=503, detail="RAG index not initialized")
    results = store.query(q, k=k)
    context = retrieve_context(q, ecosystem, region, k=3)
    preview = (context[:500] + "...") if context else "No relevant context found."
    return {
        "query":        q,
        "total_docs":   store.count(),
        "results":      results,
        "context_preview": preview
    }

@rag_router.post("/rebuild")
def rag_rebuild():
    """Force-rebuild the RAG index from current coefficient data."""
    from app.services.rag_service import build_index
    from app.services.vector_store import VectorStore
    store = VectorStore(persist_path="data/rag_index.json")
    count = build_index(store)
    # Update singleton
    import app.services.rag_service as rag_mod
    rag_mod._store = store
    return {"rebuilt": True, "documents_indexed": count}

@rag_router.get("/stats")
def rag_stats():
    """Show RAG index statistics."""
    from app.services.rag_service import get_store
    store = get_store()
    return {
        "total_documents": store.count(),
        "index_path": "data/rag_index.json",
        "document_types": [
            "ecosystem_overview (9)", "ecosystem_service (50+)",
            "regional_multiplier (9)", "land_use_alternative (6)",
            "carbon_pricing (3)", "case_study (5)", "policy_framework (4)"
        ]
    }

app.include_router(rag_router)


# ── Serve HTML files ──────────────────────────────────────────────────────────
@app.get("/live")
@app.get("/live.html")
async def serve_live_dashboard():
    """Serve the live impact ticker dashboard"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "live.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="live.html not found")

@app.get("/dashboard")
@app.get("/dashboard.html")
async def serve_dashboard():
    """Serve the main ecosystem valuation dashboard"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="dashboard.html not found")

@app.get("/index")
@app.get("/index.html")
async def serve_index():
    """Serve the landing page"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="index.html not found")

@app.get("/history")
@app.get("/history.html")
async def serve_history():
    """Serve the valuation history page"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="history.html not found")

@app.get("/about")
@app.get("/about.html")
async def serve_about():
    """Serve the about page"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "about.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="about.html not found")

@app.get("/ecosystem_dashboard")
@app.get("/ecosystem_dashboard.html")
async def serve_eco_dashboard():
    """Serve the ecosystem dashboard"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ecosystem_dashboard.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    raise HTTPException(status_code=404, detail="ecosystem_dashboard.html not found")
