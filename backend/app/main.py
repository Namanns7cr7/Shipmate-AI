from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.models.schemas import AnalyzeRequest, AnalyzeResponse, RepoSummary
from app.services.analyzer import run_full_analysis
from app.services.repo_service import process_repo_zip, get_sample_repo

app = FastAPI(
    title="ShipMate AI API",
    description="Agentic Engineering Command Center — Production Readiness Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "ShipMate AI",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "agents": ["planner", "repo_analyst", "test_generator", "security_guard", "delivery_manager"]}


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest):
    """
    Run the full 5-agent production analysis swarm.
    
    Accepts a feature request and optional repo context string.
    Returns a complete production readiness report.
    """
    if not request.feature_request or len(request.feature_request.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Feature request must be at least 10 characters long."
        )

    try:
        result = run_full_analysis(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/upload-repo", response_model=RepoSummary)
async def upload_repo(file: UploadFile = File(...)):
    """
    Upload a ZIP file containing a repository.
    
    Extracts file tree, detects tech stack, and reads key files
    (README, package.json, requirements.txt, etc.)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400,
            detail="Only ZIP files are supported. Please compress your repository as a ZIP file."
        )

    # 50MB limit
    MAX_SIZE = 50 * 1024 * 1024
    content = await file.read()

    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum size is 50MB."
        )

    try:
        summary = await process_repo_zip(content)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process repository: {str(e)}")


@app.get("/api/sample", response_model=RepoSummary)
async def get_sample():
    """
    Return a sample repository context for demo purposes.
    
    Returns a realistic e-commerce TypeScript project summary.
    """
    return get_sample_repo()


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
