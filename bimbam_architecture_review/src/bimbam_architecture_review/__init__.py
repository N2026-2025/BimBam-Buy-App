"""
BimBam Architecture Review - Main Package
==========================================

A comprehensive architecture review tool for BimBam Buy AI Agent that analyzes
system architecture against software engineering and AI engineering principles
extracted from PDF documents.
"""

from .core import ArchitectureReview
from .models import (
    Document,
    Principle,
    Gap,
    GapSeverity,
    AnalysisResult,
    ReviewConfig,
    SystemArchitecture,
    Recommendation,
    Roadmap,
    Metrics
)
from .extractor import PDFExtractor, PrincipleExtractor
from .analyzer import SystemAnalyzer, GapAnalyzer, RiskAssessor
from .reporter import ReportGenerator, ReportFormat
from .cli import main

__version__ = "1.0.0"
__author__ = "BimBam Buy Team"
__email__ = "team@bimbam-buy.com"

__all__ = [
    "ArchitectureReview",
    "Document",
    "Principle",
    "Gap",
    "GapSeverity",
    "AnalysisResult",
    "ReviewConfig",
    "SystemArchitecture",
    "Recommendation",
    "Roadmap",
    "Metrics",
    "PDFExtractor",
    "PrincipleExtractor",
    "SystemAnalyzer",
    "GapAnalyzer",
    "RiskAssessor",
    "ReportGenerator",
    "ReportFormat",
    "main",
]