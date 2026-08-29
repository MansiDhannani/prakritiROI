from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
import pandas as pd
from dotenv import load_dotenv
import os

# Import Version 2.0.0 Services
from app.services import valuation_engine, narrative_service, pdf_service, db_service, rag_service
from app.models.schemas import ValuationRequest, ScenarioCompareRequest, NarrativeRequest
from app.models.database import SessionLocal, engine, Base
from live import router as live_router

# Initialize Database
Base.metadata.create_all(bind=engine)

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check for API Key
    if os.getenv("GROQ_API_KEY"):
        print("[OK] GROQ_API_KEY found in environment")
    else:
        print("[FAIL] GROQ_API_KEY NOT found. AI features will be disabled.")

    # Pre-load RAG index on startup
    try:
        from app.services.rag_service import get_store
        store = get_store()
        print(f"[OK] RAG index ready: {store.count()} documents")
    except Exception as e:
        print(f"[WARN] RAG index failed to load: {e}")
    yield

app = FastAPI(
    title="EcoValue India",
    description="Ecosystem Services Valuation Engine for India.",
    version="2.0.0",
    docs_url="/docs",
    lifespan=lifespan
)

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mount static files (your CSS, JS files)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Load data
DATA_PATH = "india_ecosystem_coefficients.json"
CSV_PATH = "PrakritiROI_Synthetic_Dataset_2000 (1).csv"

# Load synthetic dataset for parcel lookups
if os.path.exists(CSV_PATH):
    df_parcels = pd.read_csv(CSV_PATH)
else:
    df_parcels = pd.DataFrame()

# Helper to get absolute path to HTML files
def get_html_path(filename: str):
    return os.path.join(os.path.dirname(__file__), filename)

@app.get("/")
async def serve_frontend():
    return FileResponse(get_html_path("index.html"))

@app.get("/index")
@app.get("/index.html")
async def serve_index():
    return FileResponse(get_html_path("index.html"))

@app.get("/dashboard")
@app.get("/dashboard.html")
async def serve_dashboard():
    return FileResponse(get_html_path("dashboard.html"))

@app.get("/history")
@app.get("/history.html")
async def serve_history():
    return FileResponse(get_html_path("history.html"))

@app.get("/about")
@app.get("/about.html")
async def serve_about():
    return FileResponse(get_html_path("about.html"))

@app.get("/live")
@app.get("/live.html")
async def serve_live():
    return FileResponse(get_html_path("live.html"))

@app.get("/ecosystem_dashboard")
@app.get("/ecosystem_dashboard.html")
async def serve_eco_dashboard():
    return FileResponse(get_html_path("ecosystem_dashboard.html"))

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0"}

# --- API V1 Endpoints ---

@app.get("/api/v1/ecosystems")
def get_ecosystems():
    from app.data.coefficients import ECOSYSTEMS
    return ECOSYSTEMS

@app.post("/api/v1/valuate")
def valuate(request: ValuationRequest, db: Session = Depends(get_db)):
    result = valuation_engine.compute_valuation(request)
    db_service.save_valuation(db, result.dict(), request.dict())
    return result

@app.post("/api/v1/scenarios/compare")
def compare_scenarios(request: ScenarioCompareRequest):
    return valuation_engine.compute_scenario_comparison(request)

@app.post("/api/v1/report/narrative")
def generate_narrative(request: NarrativeRequest):
    return narrative_service.generate_narrative(
        valuation_result=request.valuation_result,
        scenario_results=request.scenario_results,
        location_name=request.location_name
    )

@app.post("/api/v1/report/pdf/download")
def generate_pdf_report(request: dict):
    pdf_bytes, filename = pdf_service.generate_pdf(
        valuation_result=request.get("valuation_result"),
        narrative=request.get("narrative"),
        location_name=request.get("location_name")
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/v1/history")
def get_history(
    ecosystem_type: Optional[str] = None,
    region: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    results = db_service.list_valuations(db, ecosystem_type, region, limit, offset)
    return {
        "results": results,
        "total": len(results),
        "valuations": results  # Support both frontend formats
    }

@app.get("/api/v1/analytics")
def get_analytics(db: Session = Depends(get_db)):
    return db_service.get_analytics(db)

@app.get("/api/v1/rag/search")
def rag_search(q: str = Query(..., description="Search query for ecosystem data")):
    return {"context": rag_service.retrieve_context(q)}

@app.post("/api/v1/rag/rebuild")
def rag_rebuild():
    store = rag_service.get_store()
    count = rag_service.build_index(store)
    return {"status": "success", "documents_indexed": count}

@app.get("/api/v1/rag/stats")
def rag_stats():
    store = rag_service.get_store()
    return {"total_documents": store.count(), "index_path": "data/rag_index.json"}

# Include WebSocket Ticker
app.include_router(live_router, prefix="/api/v1")

@app.get("/api/v1/parcels")
def list_parcels():
    return df_parcels[["Parcel_ID", "State", "Land_Use_Type"]].to_dict(orient="records")

@app.get("/api/v1/parcel/{parcel_id}")
def get_parcel(parcel_id: int):
    if df_parcels.empty:
        raise HTTPException(status_code=404, detail="Parcel dataset not loaded")
    result = df_parcels[df_parcels["Parcel_ID"] == parcel_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Parcel not found")
    return result.iloc[0].to_dict()

@app.get("/api/v1/regions")
def get_regions():
    from app.data.coefficients import REGIONAL_MULTIPLIERS
    return REGIONAL_MULTIPLIERS

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)