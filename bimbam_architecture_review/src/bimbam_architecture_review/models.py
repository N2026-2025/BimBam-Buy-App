"""
Data Models for BimBam Architecture Review
===========================================

Core data structures for architecture review analysis.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid


class GapSeverity(str, Enum):
    """Severity levels for identified gaps."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GapCategory(str, Enum):
    """Categories of gaps identified during analysis."""
    ARCHITECTURE = "architecture"
    IMPLEMENTATION = "implementation"
    OPERATIONAL = "operational"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"


class DocumentType(str, Enum):
    """Types of source documents."""
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


class AnalysisStatus(str, Enum):
    """Status of analysis execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReportFormat(str, Enum):
    """Supported report output formats."""
    CONSOLE = "console"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class Document(BaseModel):
    """Represents a source document for analysis."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    path: str
    name: str
    type: DocumentType
    content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    extracted_at: Optional[datetime] = None
    size_bytes: int = 0
    page_count: int = 0
    
    class Config:
        use_enum_values = True


class Principle(BaseModel):
    """Represents an architectural principle extracted from documents."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    category: str
    subcategory: Optional[str] = None
    title: str
    description: str
    source_text: str
    page_reference: Optional[int] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    related_principles: List[str] = Field(default_factory=list)
    
    class Config:
        use_enum_values = True


class Gap(BaseModel):
    """Represents a gap between theoretical principles and actual implementation."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    principle_id: str
    category: GapCategory
    severity: GapSeverity
    title: str
    description: str
    current_state: str
    expected_state: str
    impact: str
    effort_estimate: str  # "low", "medium", "high"
    business_impact: Optional[str] = None
    technical_debt: bool = False
    dependencies: List[str] = Field(default_factory=list)
    related_gaps: List[str] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class Recommendation(BaseModel):
    """Represents a recommendation for addressing a gap."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    gap_id: str
    title: str
    description: str
    priority: int = Field(default=1, ge=1, le=10)
    effort: str  # "quick-win", "short-term", "medium-term", "long-term"
    resources: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    estimated_timeline: str  # e.g., "2-4 weeks"
    risk_level: GapSeverity
    
    class Config:
        use_enum_values = True


class Metrics(BaseModel):
    """Metrics for tracking analysis quality and system health."""
    alignment_score: float = Field(default=0.0, ge=0.0, le=100.0)
    total_principles: int = 0
    total_gaps: int = 0
    critical_gaps: int = 0
    high_gaps: int = 0
    medium_gaps: int = 0
    low_gaps: int = 0
    coverage_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    analysis_duration_seconds: float = 0.0
    documents_processed: int = 0
    principles_extracted: int = 0
    gaps_identified: int = 0
    recommendations_generated: int = 0
    
    class Config:
        use_enum_values = True


class SystemArchitecture(BaseModel):
    """Represents the current system architecture being analyzed."""
    name: str
    version: str
    description: str
    components: List[Dict[str, Any]] = Field(default_factory=list)
    services: List[Dict[str, Any]] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    data_flows: List[Dict[str, Any]] = Field(default_factory=list)
    deployment: Dict[str, Any] = Field(default_factory=dict)
    monitoring: Dict[str, Any] = Field(default_factory=dict)
    security: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReviewConfig(BaseModel):
    """Configuration for architecture review execution."""
    documents_path: str
    system_path: str
    output_path: str
    severity_levels: List[GapSeverity] = Field(
        default_factory=lambda: [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW]
    )
    include_dependencies: bool = True
    cross_validate: bool = True
    parallel_jobs: int = 4
    output_formats: List[ReportFormat] = Field(
        default_factory=lambda: [ReportFormat.CONSOLE, ReportFormat.JSON, ReportFormat.MARKDOWN]
    )
    templates_dir: Optional[str] = None
    business_metrics_path: Optional[str] = None
    language: str = "en"
    cache_enabled: bool = True
    
    class Config:
        use_enum_values = True


class AnalysisResult(BaseModel):
    """Complete results of an architecture review analysis."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    config: ReviewConfig
    system: SystemArchitecture
    documents: List[Document] = Field(default_factory=list)
    principles: List[Principle] = Field(default_factory=list)
    gaps: List[Gap] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    metrics: Metrics = Field(default_factory=Metrics)
    status: AnalysisStatus = AnalysisStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    reports: Dict[ReportFormat, str] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


class Roadmap(BaseModel):
    """Implementation roadmap for addressing identified gaps."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    analysis_id: str
    phases: List[Dict[str, Any]] = Field(default_factory=list)
    total_estimated_effort: str
    total_estimated_cost: Optional[str] = None
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        use_enum_values = True


class ExecutiveSummary(BaseModel):
    """Executive summary for leadership presentation."""
    system_name: str
    analysis_date: datetime
    overall_alignment_score: float
    critical_findings: int
    key_recommendations: List[str]
    investment_required: str
    timeline: str
    risk_level: GapSeverity
    next_steps: List[str]
    
    class Config:
        use_enum_values = True