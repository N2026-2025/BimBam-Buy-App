"""
Configuration Management for BimBam Architecture Review
========================================================

Handles application settings from environment variables, config files, and defaults.
"""

from typing import Optional, List
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = "bimbam-architecture-review"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    # Document Processing
    documents_path: str = "./documents"
    pdf_parallel_jobs: int = 4
    pdf_extraction_timeout: int = 300
    max_document_size_mb: int = 100
    
    # Principle Extraction
    min_principle_length: int = 20
    max_principle_length: int = 1000
    principle_confidence_threshold: float = 0.5
    enable_nlp_extraction: bool = True
    spacy_model: str = "en_core_web_sm"
    
    # Analysis
    system_path: str = "."
    include_dependencies: bool = True
    cross_validate_principles: bool = True
    severity_levels: List[str] = ["critical", "high", "medium", "low"]
    
    # Gap Analysis
    gap_deduplication_threshold: float = 0.85
    max_gaps_per_category: int = 50
    business_impact_weight: float = 0.3
    technical_debt_weight: float = 0.2
    
    # Recommendations
    max_recommendations_per_gap: int = 3
    priority_boost_security: int = 2
    priority_boost_compliance: int = 3
    quick_win_threshold_days: int = 14
    
    # Reporting
    output_path: str = "./reports"
    default_formats: List[str] = ["console", "json", "markdown"]
    templates_dir: Optional[str] = None
    report_retention_days: int = 90
    include_executive_summary: bool = True
    
    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 1
    api_timeout: int = 300
    api_rate_limit: int = 100
    api_cors_origins: List[str] = ["*"]
    
    # Caching
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    cache_dir: str = "./cache"
    
    # Security
    api_key_enabled: bool = False
    api_key_header: str = "X-API-Key"
    jwt_secret: Optional[str] = None
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    
    # External Integrations
    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    teams_webhook_url: Optional[str] = None
    jira_url: Optional[str] = None
    jira_username: Optional[str] = None
    jira_token: Optional[str] = None
    
    # ML/NLP
    use_local_embeddings: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 32
    similarity_threshold: float = 0.75
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return v.upper()
    
    @validator("severity_levels")
    def validate_severity_levels(cls, v):
        valid = ["critical", "high", "medium", "low"]
        for level in v:
            if level not in valid:
                raise ValueError(f"Invalid severity level: {level}. Must be one of {valid}")
        return v
    
    @validator("default_formats")
    def validate_formats(cls, v):
        valid = ["console", "json", "markdown", "html", "pdf"]
        for fmt in v:
            if fmt not in valid:
                raise ValueError(f"Invalid format: {fmt}. Must be one of {valid}")
        return v
    
    @validator("pdf_parallel_jobs")
    def validate_parallel_jobs(cls, v):
        if v < 1 or v > 16:
            raise ValueError("pdf_parallel_jobs must be between 1 and 16")
        return v
    
    @property
    def cache_path(self) -> Path:
        return Path(self.cache_dir)
    
    @property
    def documents_dir(self) -> Path:
        return Path(self.documents_path)
    
    @property
    def output_dir(self) -> Path:
        return Path(self.output_path)
    
    @property
    def templates_path(self) -> Optional[Path]:
        return Path(self.templates_dir) if self.templates_dir else None


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings


def configure_settings(**kwargs) -> Settings:
    """Configure settings programmatically (for testing)."""
    global _settings
    _settings = Settings(**kwargs)
    return _settings