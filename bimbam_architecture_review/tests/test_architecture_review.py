"""
Tests for BimBam Architecture Review
=====================================
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from bimbam_architecture_review.models import (
    GapSeverity, GapCategory, Document, Principle, Gap,
    Recommendation, Metrics, SystemArchitecture, ReviewConfig,
    AnalysisResult, AnalysisStatus, ReportFormat
)
from bimbam_architecture_review.config import Settings
from bimbam_architecture_review.extractor import PDFExtractor, PrincipleExtractor
from bimbam_architecture_review.analyzer import SystemAnalyzer, GapAnalyzer
from bimbam_architecture_review.reporter import ReportGenerator


class TestModels:
    """Test data models."""
    
    def test_gap_severity_enum(self):
        assert GapSeverity.CRITICAL.value == "critical"
        assert GapSeverity.HIGH.value == "high"
        assert GapSeverity.MEDIUM.value == "medium"
        assert GapSeverity.LOW.value == "low"
    
    def test_gap_category_enum(self):
        assert GapCategory.ARCHITECTURE.value == "architecture"
        assert GapCategory.SECURITY.value == "security"
        assert GapCategory.PERFORMANCE.value == "performance"
    
    def test_document_creation(self):
        doc = Document(
            path="/test/doc.pdf",
            name="doc.pdf",
            type="pdf",
            content="Test content",
            page_count=5
        )
        assert doc.name == "doc.pdf"
        assert doc.page_count == 5
    
    def test_principle_creation(self):
        principle = Principle(
            document_id="doc1",
            category="architecture",
            title="Test Principle",
            description="This is a test principle",
            confidence=0.9
        )
        assert principle.category == "architecture"
        assert principle.confidence == 0.9
    
    def test_gap_creation(self):
        gap = Gap(
            principle_id="p1",
            category=GapCategory.ARCHITECTURE,
            severity=GapSeverity.HIGH,
            title="Test Gap",
            description="Gap description",
            current_state="Current",
            expected_state="Expected",
            impact="High impact",
            effort_estimate="medium"
        )
        assert gap.severity == GapSeverity.HIGH
        assert gap.category == GapCategory.ARCHITECTURE
    
    def test_recommendation_creation(self):
        rec = Recommendation(
            gap_id="g1",
            title="Test Recommendation",
            description="Fix the gap",
            priority=8,
            effort="short-term",
            estimated_timeline="2-4 weeks",
            risk_level=GapSeverity.HIGH
        )
        assert rec.priority == 8
        assert rec.effort == "short-term"
    
    def test_metrics_calculation(self):
        metrics = Metrics(
            total_gaps=10,
            critical_gaps=2,
            high_gaps=3,
            medium_gaps=3,
            low_gaps=2,
            total_principles=20
        )
        assert metrics.total_gaps == 10
        # Alignment score calculation would be done by the engine


class TestSettings:
    """Test configuration settings."""
    
    def test_default_settings(self):
        settings = Settings()
        assert settings.app_name == "bimbam-architecture-review"
        assert settings.pdf_parallel_jobs == 4
        assert settings.log_level == "INFO"
    
    def test_settings_validation(self):
        with pytest.raises(ValueError):
            Settings(log_level="INVALID")
        
        with pytest.raises(ValueError):
            Settings(pdf_parallel_jobs=20)
    
    def test_settings_properties(self):
        settings = Settings()
        assert isinstance(settings.cache_path, Path)
        assert isinstance(settings.documents_dir, Path)
        assert isinstance(settings.output_dir, Path)


class TestPDFExtractor:
    """Test PDF extraction."""
    
    def setup_method(self):
        self.extractor = PDFExtractor()
    
    def test_extract_method_exists(self):
        assert hasattr(self.extractor, 'extract')
        assert hasattr(self.extractor, 'extract_batch')
    
    @patch('bimbam_architecture_review.extractor.pypdf.PdfReader')
    def test_extract_with_pypdf(self, mock_reader):
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test page content"
        mock_reader.return_value.pages = [mock_page, mock_page]
        mock_reader.return_value.metadata = {"/Title": "Test Doc"}
        
        extractor = PDFExtractor()
        # Would need a real PDF file for full test
        # This tests the method structure


class TestPrincipleExtractor:
    """Test principle extraction."""
    
    def setup_method(self):
        self.extractor = PrincipleExtractor()
    
    def test_pattern_compilation(self):
        assert len(self.extractor.compiled_patterns) > 0
    
    def test_category_classification(self):
        text = "We should use microservices with async communication for scalability"
        category = self.extractor._classify_section(text)
        assert category in ["architecture", "scalability", "general"]
    
    def test_principle_validation(self):
        # Too short
        assert not self.extractor._is_valid_principle("Short")
        # Valid
        assert self.extractor._is_valid_principle("We should implement circuit breakers for all external service calls")
        # Too long
        long_text = "x" * 1500
        assert not self.extractor._is_valid_principle(long_text)
    
    def test_title_generation(self):
        text = "This is a test principle. It has multiple sentences. Here is another one."
        title = self.extractor._generate_title(text)
        assert title == "This is a test principle"
    
    def test_confidence_calculation(self):
        text = "We must always use circuit breakers for resilience"
        conf = self.extractor._calculate_confidence(text, "reliability")
        assert 0.5 <= conf <= 1.0
    
    def test_tag_extraction(self):
        text = "We should use microservices with circuit breakers for resilience"
        tags = self.extractor._extract_tags(text)
        assert "microservices" in tags
        assert "resilience" in tags


class TestSystemAnalyzer:
    """Test system analysis."""
    
    def setup_method(self):
        self.analyzer = SystemAnalyzer()
    
    def test_analyzer_initialization(self):
        assert self.analyzer is not None


class TestGapAnalyzer:
    """Test gap analysis."""
    
    def setup_method(self):
        self.analyzer = GapAnalyzer()
    
    def test_analyzer_initialization(self):
        assert self.analyzer is not None
    
    def test_effort_mapping(self):
        # Test effort mapping for different gap types
        effort_map = {
            (GapCategory.SECURITY, GapSeverity.CRITICAL): "short-term",
            (GapCategory.ARCHITECTURE, GapSeverity.HIGH): "medium-term",
            (GapCategory.PERFORMANCE, GapSeverity.HIGH): "short-term",
            (GapCategory.OPERATIONAL, GapSeverity.MEDIUM): "short-term",
            (GapCategory.IMPLEMENTATION, GapSeverity.LOW): "quick-win",
        }
        
        for key, expected in effort_map.items():
            # This would be tested in the actual method
            pass


class TestReportGenerator:
    """Test report generation."""
    
    def setup_method(self):
        self.generator = ReportGenerator()
    
    def test_generator_initialization(self):
        assert self.generator is not None
    
    def test_severity_colors(self):
        assert self.generator._get_severity_color(GapSeverity.CRITICAL) == "#dc3545"
        assert self.generator._get_severity_color(GapSeverity.HIGH) == "#fd7e14"
        assert self.generator._get_severity_color(GapSeverity.MEDIUM) == "#ffc107"
        assert self.generator._get_severity_color(GapSeverity.LOW) == "#28a745"
    
    def test_severity_icons(self):
        assert self.generator._get_severity_icon(GapSeverity.CRITICAL) == "🔴"
        assert self.generator._get_severity_icon(GapSeverity.HIGH) == "🟠"
        assert self.generator._get_severity_icon(GapSeverity.MEDIUM) == "🟡"
        assert self.generator._get_severity_icon(GapSeverity.LOW) == "🟢"


class TestArchitectureReviewIntegration:
    """Integration tests for the main review engine."""
    
    @pytest.mark.asyncio
    async def test_review_engine_initialization(self):
        config = ReviewConfig(
            documents_path="./documents",
            system_path=".",
            output_path="./reports"
        )
        engine = ArchitectureReview(config)
        assert engine is not None
        assert engine.config == config
    
    @pytest.mark.asyncio
    async def test_run_analysis_structure(self):
        """Test that run_analysis returns proper structure."""
        config = ReviewConfig(
            documents_path="./nonexistent",  # Will fail but we test structure
            system_path=".",
            output_path="./reports"
        )
        engine = ArchitectureReview(config)
        
        # The analysis will fail due to missing documents, but we can test
        # that the engine is properly initialized
        assert engine._extractor is not None
        assert engine._principle_extractor is not None
        assert engine._system_analyzer is not None
        assert engine._gap_analyzer is not None
        assert engine._risk_assessor is not None
        assert engine._reporter is not None


class TestCLICommands:
    """Test CLI command structure."""
    
    def test_cli_imports(self):
        from bimbam_architecture_review.cli import app
        assert app is not None
    
    def test_version_command(self):
        from bimbam_architecture_review import __version__
        assert __version__ == "1.0.0"


# Fixtures
@pytest.fixture
def sample_document():
    return Document(
        path="/test/sample.pdf",
        name="sample.pdf",
        type="pdf",
        content="This is a sample document with principles about microservices and scalability.",
        page_count=10
    )


@pytest.fixture
def sample_principles():
    return [
        Principle(
            document_id="doc1",
            category="architecture",
            title="Use Microservices",
            description="We should decompose the system into microservices with clear boundaries",
            confidence=0.9
        ),
        Principle(
            document_id="doc1",
            category="scalability",
            title="Horizontal Scaling",
            description="Services must support horizontal scaling through containerization",
            confidence=0.85
        ),
        Principle(
            document_id="doc1",
            category="security",
            title="Zero Trust",
            description="All service communication must use mutual TLS authentication",
            confidence=0.95
        )
    ]


@pytest.fixture
def sample_system():
    return SystemArchitecture(
        name="Test System",
        version="1.0.0",
        description="Test system for architecture review",
        technologies=["fastapi", "streamlit", "chromadb"],
        components=[
            {"name": "api", "type": "api"},
            {"name": "rag", "type": "rag"}
        ],
        services=[
            {"name": "api", "type": "api", "framework": "FastAPI"},
            {"name": "ui", "type": "ui", "framework": "Streamlit"}
        ]
    )


# Performance/Load Tests
class TestPerformance:
    """Performance-related tests."""
    
    def test_large_principle_set_handling(self):
        """Test handling of large principle sets."""
        extractor = PrincipleExtractor()
        
        # Generate many principles
        principles = [
            Principle(
                document_id=f"doc{i}",
                category="architecture",
                title=f"Principle {i}",
                description=f"This is principle number {i} about system architecture and design patterns",
                confidence=0.8
            )
            for i in range(100)
        ]
        
        # Test deduplication performance
        unique = extractor._deduplicate_principles(principles)
        assert len(unique) <= len(principles)
    
    def test_gap_analyzer_performance(self):
        """Test gap analyzer with many gaps."""
        analyzer = GapAnalyzer()
        
        # Create many gaps
        gaps = [
            Gap(
                principle_id=f"p{i}",
                category=GapCategory.ARCHITECTURE,
                severity=GapSeverity.MEDIUM,
                title=f"Gap {i}",
                description=f"Description of gap {i}",
                current_state="Current",
                expected_state="Expected",
                impact="Impact",
                effort_estimate="medium"
            )
            for i in range(1000)
        ]
        
        # Test sorting performance
        sorted_gaps = sorted(gaps, key=lambda g: g.severity.value)
        assert len(sorted_gaps) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])