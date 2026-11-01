"""
REST API Server for BimBam Architecture Review
===============================================

Provides HTTP API for integrating architecture review into CI/CD pipelines.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from .core import ArchitectureReview
from .models import (
    ReviewConfig, AnalysisResult, AnalysisStatus, GapSeverity,
    ReportFormat, Roadmap, ExecutiveSummary
)
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# API Key security (optional)
api_key_header = APIKeyHeader(name=settings.api_key_header, auto_error=False)


async def verify_api_key(api_key: str = Depends(api_key_header)) -> Optional[str]:
    """Verify API key if enabled."""
    if settings.api_key_enabled:
        # In production, validate against stored keys
        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")
        # Simple validation - replace with proper key management
        if api_key != settings.jwt_secret:
            raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


# Global review engine instance
_review_engine: Optional[ArchitectureReview] = None
_analysis_cache: Dict[str, AnalysisResult] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global _review_engine
    logger.info("Starting Architecture Review API")
    yield
    logger.info("Shutting down Architecture Review API")


app = FastAPI(
    title="BimBam Architecture Review API",
    description="REST API for BimBam Buy AI Agent Architecture Review",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class ReviewRequest(BaseModel):
    """Request model for starting a review."""
    system: str = "bimbam-buy-ai-agent"
    documents_path: str = "./documents"
    system_path: str = "."
    output_path: str = "./reports"
    severity_levels: List[GapSeverity] = [
        GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW
    ]
    output_formats: List[ReportFormat] = [
        ReportFormat.CONSOLE, ReportFormat.JSON, ReportFormat.MARKDOWN
    ]
    parallel_jobs: int = 4
    business_metrics_path: Optional[str] = None
    templates_dir: Optional[str] = None


class ReviewResponse(BaseModel):
    """Response model for review operations."""
    review_id: str
    status: AnalysisStatus
    message: str
    started_at: datetime


class ReviewStatusResponse(BaseModel):
    """Response model for review status."""
    review_id: str
    status: AnalysisStatus
    progress: Optional[float] = None
    current_phase: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    reports: Optional[Dict[str, str]] = None


class GapFilterRequest(BaseModel):
    """Request model for filtering gaps."""
    severity: Optional[List[GapSeverity]] = None
    category: Optional[List[str]] = None
    min_risk_score: Optional[float] = None


class RoadmapRequest(BaseModel):
    """Request model for roadmap generation."""
    review_id: str
    timeline_months: int = 12
    prioritize_business_impact: bool = True


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "bimbam-architecture-review",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "cache_size": len(_analysis_cache),
        "timestamp": datetime.now().isoformat()
    }


# Review management endpoints
@app.post("/api/v1/reviews", response_model=ReviewResponse)
async def start_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Start a new architecture review."""
    global _review_engine
    
    config = ReviewConfig(
        documents_path=request.documents_path,
        system_path=request.system_path,
        output_path=request.output_path,
        severity_levels=request.severity_levels,
        output_formats=request.output_formats,
        parallel_jobs=request.parallel_jobs,
        business_metrics_path=request.business_metrics_path,
        templates_dir=request.templates_dir
    )
    
    _review_engine = ArchitectureReview(config)
    
    # Generate review ID
    review_id = f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Start review in background
    background_tasks.add_task(_run_review_background, review_id, _review_engine)
    
    return ReviewResponse(
        review_id=review_id,
        status=AnalysisStatus.PENDING,
        message="Architecture review started",
        started_at=datetime.now()
    )


async def _run_review_background(review_id: str, engine: ArchitectureReview):
    """Run review in background and cache results."""
    try:
        result = await engine.run_analysis(generate_reports=True)
        _analysis_cache[review_id] = result
        logger.info(f"Review {review_id} completed with status {result.status}")
    except Exception as e:
        logger.error(f"Review {review_id} failed: {e}")
        # Create failed result
        from .models import AnalysisResult, ReviewConfig, SystemArchitecture, AnalysisStatus
        failed_result = AnalysisResult(
            config=engine.config,
            system=SystemArchitecture(name="unknown", version="unknown", description=""),
            status=AnalysisStatus.FAILED,
            error=str(e),
            completed_at=datetime.now()
        )
        _analysis_cache[review_id] = failed_result


@app.get("/api/v1/reviews/{review_id}", response_model=ReviewStatusResponse)
async def get_review_status(
    review_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get status of a review."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    
    # Calculate progress
    progress_map = {
        "pending": 0.0,
        "running": 0.5,
        "completed": 1.0,
        "failed": 0.0,
        "cancelled": 0.0
    }
    
    phase_map = {
        "pending": "Initializing",
        "running": "Analyzing",
        "completed": "Complete",
        "failed": "Failed",
        "cancelled": "Cancelled"
    }
    
    metrics = {}
    if result.metrics:
        metrics = {
            "alignment_score": result.metrics.alignment_score,
            "total_gaps": result.metrics.total_gaps,
            "critical_gaps": result.metrics.critical_gaps,
            "high_gaps": result.metrics.high_gaps,
            "recommendations": result.metrics.recommendations_generated
        }
    
    return ReviewStatusResponse(
        review_id=review_id,
        status=result.status,
        progress=progress_map.get(result.status.value, 0.0),
        current_phase=phase_map.get(result.status.value, "Unknown"),
        metrics=metrics,
        error=result.error,
        started_at=result.started_at,
        completed_at=result.completed_at,
        reports=result.reports
    )


@app.get("/api/v1/reviews")
async def list_reviews(
    status: Optional[AnalysisStatus] = None,
    limit: int = 50,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
):
    """List all reviews with optional filtering."""
    reviews = []
    
    for rid, result in _analysis_cache.items():
        if status and result.status != status:
            continue
        
        reviews.append({
            "review_id": rid,
            "status": result.status.value,
            "started_at": result.started_at.isoformat(),
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
            "total_gaps": result.metrics.total_gaps if result.metrics else 0,
            "alignment_score": result.metrics.alignment_score if result.metrics else 0
        })
    
    # Sort by start time descending
    reviews.sort(key=lambda x: x["started_at"], reverse=True)
    
    return {
        "total": len(reviews),
        "reviews": reviews[offset:offset + limit]
    }


@app.delete("/api/v1/reviews/{review_id}")
async def delete_review(
    review_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Delete a review and its cached results."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    del _analysis_cache[review_id]
    return {"message": f"Review {review_id} deleted"}


# Gap analysis endpoints
@app.get("/api/v1/reviews/{review_id}/gaps")
async def get_gaps(
    review_id: str,
    severity: Optional[List[GapSeverity]] = None,
    category: Optional[List[str]] = None,
    limit: int = 100,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
):
    """Get gaps for a review with optional filtering."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    gaps = result.gaps
    
    # Apply filters
    if severity:
        gaps = [g for g in gaps if g.severity in severity]
    if category:
        gaps = [g for g in gaps if g.category.value in category]
    
    # Sort by severity and risk
    severity_order = {
        "critical": 0, "high": 1, "medium": 2, "low": 3
    }
    gaps.sort(key=lambda g: (severity_order.get(g.severity.value, 4), -g.metadata.get('risk_score', 0) if g.metadata else 0))
    
    total = len(gaps)
    paginated = gaps[offset:offset + limit]
    
    return {
        "total": total,
        "gaps": [
            {
                "id": g.id,
                "principle_id": g.principle_id,
                "category": g.category.value,
                "severity": g.severity.value,
                "title": g.title,
                "description": g.description,
                "current_state": g.current_state,
                "expected_state": g.expected_state,
                "impact": g.impact,
                "effort_estimate": g.effort_estimate,
                "business_impact": g.business_impact,
                "risk_score": g.metadata.get('risk_score') if g.metadata else None,
                "detected_at": g.detected_at.isoformat()
            }
            for g in paginated
        ]
    }


@app.get("/api/v1/reviews/{review_id}/gaps/summary")
async def get_gaps_summary(
    review_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get gap summary statistics."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    
    # Group by category and severity
    summary = {}
    for gap in result.gaps:
        cat = gap.category.value
        sev = gap.severity.value
        
        if cat not in summary:
            summary[cat] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
        
        summary[cat][sev] += 1
        summary[cat]["total"] += 1
    
    return {
        "review_id": review_id,
        "total_gaps": len(result.gaps),
        "by_category": summary,
        "by_severity": {
            "critical": sum(1 for g in result.gaps if g.severity == GapSeverity.CRITICAL),
            "high": sum(1 for g in result.gaps if g.severity == GapSeverity.HIGH),
            "medium": sum(1 for g in result.gaps if g.severity == GapSeverity.MEDIUM),
            "low": sum(1 for g in result.gaps if g.severity == GapSeverity.LOW)
        }
    }


# Recommendations endpoints
@app.get("/api/v1/reviews/{review_id}/recommendations")
async def get_recommendations(
    review_id: str,
    effort: Optional[List[str]] = None,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """Get recommendations for a review."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    recommendations = result.recommendations
    
    if effort:
        recommendations = [r for r in recommendations if r.effort in effort]
    
    # Sort by priority
    recommendations.sort(key=lambda r: -r.priority)
    
    return {
        "total": len(recommendations),
        "recommendations": [
            {
                "id": r.id,
                "gap_id": r.gap_id,
                "title": r.title,
                "description": r.description,
                "priority": r.priority,
                "effort": r.effort,
                "resources": r.resources,
                "dependencies": r.dependencies,
                "success_criteria": r.success_criteria,
                "estimated_timeline": r.estimated_timeline,
                "risk_level": r.risk_level.value
            }
            for r in recommendations[:limit]
        ]
    }


# Reports endpoints
@app.get("/api/v1/reviews/{review_id}/reports")
async def list_reports(
    review_id: str,
    api_key: str = Depends(verify_api_key)
):
    """List available reports for a review."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    return {
        "review_id": review_id,
        "reports": result.reports
    }


@app.get("/api/v1/reviews/{review_id}/reports/{format}")
async def download_report(
    review_id: str,
    format: ReportFormat,
    api_key: str = Depends(verify_api_key)
):
    """Download a specific report format."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    
    if format.value not in result.reports:
        raise HTTPException(status_code=404, detail=f"Report in {format.value} format not available")
    
    report_path = result.reports[format.value]
    
    # Determine media type
    media_types = {
        ReportFormat.JSON: "application/json",
        ReportFormat.MARKDOWN: "text/markdown",
        ReportFormat.HTML: "text/html",
        ReportFormat.PDF: "application/pdf",
        ReportFormat.CONSOLE: "text/plain"
    }
    
    return FileResponse(
        report_path,
        media_type=media_types.get(format, "application/octet-stream"),
        filename=Path(report_path).name
    )


# Roadmap endpoints
@app.post("/api/v1/reviews/{review_id}/roadmap", response_model=Dict[str, Any])
async def generate_roadmap(
    review_id: str,
    request: RoadmapRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generate implementation roadmap for a review."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    
    # Create a temporary engine to generate roadmap
    engine = ArchitectureReview(result.config)
    engine.result = result
    
    roadmap = engine.generate_implementation_roadmap(
        timeline_months=request.timeline_months,
        prioritize_business_impact=request.prioritize_business_impact
    )
    
    return {
        "roadmap_id": roadmap.id,
        "phases": roadmap.phases,
        "total_estimated_effort": roadmap.total_estimated_effort,
        "resource_requirements": roadmap.resource_requirements,
        "milestones": roadmap.milestones,
        "risks": roadmap.risks,
        "created_at": roadmap.created_at.isoformat()
    }


# Executive summary endpoint
@app.get("/api/v1/reviews/{review_id}/executive-summary")
async def get_executive_summary(
    review_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get executive summary for a review."""
    if review_id not in _analysis_cache:
        raise HTTPException(status_code=404, detail="Review not found")
    
    result = _analysis_cache[review_id]
    engine = ArchitectureReview(result.config)
    engine.result = result
    
    summary = engine.generate_executive_summary()
    
    return {
        "system_name": summary.system_name,
        "analysis_date": summary.analysis_date.isoformat(),
        "overall_alignment_score": summary.overall_alignment_score,
        "critical_findings": summary.critical_findings,
        "key_recommendations": summary.key_recommendations,
        "investment_required": summary.investment_required,
        "timeline": summary.timeline,
        "risk_level": summary.risk_level.value,
        "next_steps": summary.next_steps
    }


# Document management endpoints
@app.post("/api/v1/documents/upload")
async def upload_documents(
    files: List[UploadFile] = File(...),
    api_key: str = Depends(verify_api_key)
):
    """Upload PDF documents for analysis."""
    upload_dir = Path(settings.documents_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    uploaded = []
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail=f"Only PDF files allowed: {file.filename}")
        
        file_path = upload_dir / file.filename
        content = await file.read()
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        uploaded.append({
            "filename": file.filename,
            "size": len(content),
            "path": str(file_path)
        })
    
    return {
        "uploaded": len(uploaded),
        "files": uploaded
    }


@app.get("/api/v1/documents")
async def list_documents(
    api_key: str = Depends(verify_api_key)
):
    """List available documents."""
    docs_dir = Path(settings.documents_path)
    if not docs_dir.exists():
        return {"documents": []}
    
    documents = []
    for file in docs_dir.glob("*.pdf"):
        stat = file.stat()
        documents.append({
            "name": file.name,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    
    return {"documents": documents}


# Metrics endpoints
@app.get("/api/v1/metrics")
async def get_metrics(api_key: str = Depends(verify_api_key)):
    """Get system metrics."""
    return {
        "cache": {
            "reviews_cached": len(_analysis_cache),
            "cache_enabled": settings.cache_enabled
        },
        "settings": {
            "documents_path": settings.documents_path,
            "output_path": settings.output_path,
            "parallel_jobs": settings.pdf_parallel_jobs
        }
    }


# Configuration endpoints
@app.get("/api/v1/config")
async def get_config(api_key: str = Depends(verify_api_key)):
    """Get current configuration (sanitized)."""
    config = settings.model_dump()
    # Remove sensitive values
    sensitive = ["jwt_secret", "github_token", "gitlab_token", "slack_webhook_url", 
                 "teams_webhook_url", "jira_token", "api_key"]
    for key in sensitive:
        if key in config:
            config[key] = "***REDACTED***" if config[key] else None
    return config


# Async task status (for long-running operations)
@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get status of async task."""
    # In a real implementation, this would query a task queue (Celery, etc.)
    return {
        "task_id": task_id,
        "status": "not_implemented",
        "message": "Task queue integration not implemented"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "bimbam_architecture_review.api:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )