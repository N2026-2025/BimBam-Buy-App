"""
Core Architecture Review Engine
================================

Main orchestration class for conducting architecture reviews.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import structlog

from .models import (
    ArchitectureReview as ArchitectureReviewModel,
    ReviewConfig,
    SystemArchitecture,
    Document,
    Principle,
    Gap,
    Recommendation,
    Metrics,
    AnalysisResult,
    AnalysisStatus,
    ReportFormat,
    GapSeverity,
    GapCategory,
    Roadmap,
    ExecutiveSummary
)
from .extractor import PDFExtractor, PrincipleExtractor
from .analyzer import SystemAnalyzer, GapAnalyzer, RiskAssessor
from .reporter import ReportGenerator

logger = structlog.get_logger(__name__)


class ArchitectureReview:
    """
    Main orchestrator for BimBam Buy AI Agent architecture reviews.
    
    This class coordinates the entire review process:
    1. Document extraction and processing
    2. Principle extraction from documents
    3. System architecture analysis
    4. Gap identification and classification
    5. Risk assessment
    6. Recommendation generation
    7. Report generation
    """
    
    def __init__(self, config: ReviewConfig):
        self.config = config
        self.result: Optional[AnalysisResult] = None
        self._extractor = PDFExtractor()
        self._principle_extractor = PrincipleExtractor()
        self._system_analyzer = SystemAnalyzer()
        self._gap_analyzer = GapAnalyzer()
        self._risk_assessor = RiskAssessor()
        self._reporter = ReportGenerator()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure structured logging."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    async def run_analysis(
        self,
        include_dependencies: bool = True,
        severity_levels: Optional[List[GapSeverity]] = None,
        generate_reports: bool = True
    ) -> AnalysisResult:
        """
        Execute the complete architecture review analysis.
        
        Args:
            include_dependencies: Whether to analyze cross-component dependencies
            severity_levels: Filter gaps by severity levels
            generate_reports: Whether to generate output reports
            
        Returns:
            AnalysisResult with all findings and metrics
        """
        start_time = time.time()
        self.result = AnalysisResult(
            config=self.config,
            system=SystemArchitecture(
                name="BimBam Buy AI Agent",
                version="2.0.0",
                description="RAG-based customer support system with microservices architecture"
            ),
            status=AnalysisStatus.RUNNING
        )
        
        logger.info("Starting architecture review", system=self.result.system.name)
        
        try:
            # Phase 1: Document Processing
            logger.info("Phase 1: Processing documents")
            await self._process_documents()
            
            # Phase 2: Principle Extraction
            logger.info("Phase 2: Extracting architectural principles")
            await self._extract_principles()
            
            # Phase 3: System Analysis
            logger.info("Phase 3: Analyzing system architecture")
            await self._analyze_system(include_dependencies)
            
            # Phase 4: Gap Identification
            logger.info("Phase 4: Identifying gaps")
            await self._identify_gaps(severity_levels)
            
            # Phase 5: Risk Assessment
            logger.info("Phase 5: Assessing risks")
            await self._assess_risks()
            
            # Phase 6: Generate Recommendations
            logger.info("Phase 6: Generating recommendations")
            await self._generate_recommendations()
            
            # Phase 7: Calculate Metrics
            logger.info("Phase 7: Calculating metrics")
            self._calculate_metrics()
            
            # Phase 8: Generate Reports
            if generate_reports:
                logger.info("Phase 8: Generating reports")
                await self._generate_reports()
            
            self.result.status = AnalysisStatus.COMPLETED
            self.result.completed_at = datetime.now()
            self.result.metrics.analysis_duration_seconds = time.time() - start_time
            
            logger.info(
                "Architecture review completed",
                duration=self.result.metrics.analysis_duration_seconds,
                gaps_found=self.result.metrics.total_gaps,
                alignment_score=self.result.metrics.alignment_score
            )
            
            return self.result
            
        except Exception as e:
            self.result.status = AnalysisStatus.FAILED
            self.result.error = str(e)
            self.result.completed_at = datetime.now()
            logger.error("Architecture review failed", error=str(e))
            raise
    
    async def _process_documents(self) -> None:
        """Process all documents in the configured path."""
        docs_path = Path(self.config.documents_path)
        if not docs_path.exists():
            raise FileNotFoundError(f"Documents path not found: {docs_path}")
        
        pdf_files = list(docs_path.glob("*.pdf"))
        if not pdf_files:
            logger.warning("No PDF files found in documents path")
            return
        
        # Process documents in parallel
        with ThreadPoolExecutor(max_workers=self.config.parallel_jobs) as executor:
            futures = {
                executor.submit(self._extractor.extract, pdf_file): pdf_file
                for pdf_file in pdf_files
            }
            
            for future in as_completed(futures):
                pdf_file = futures[future]
                try:
                    document = future.result()
                    self.result.documents.append(document)
                    logger.info("Processed document", name=document.name, pages=document.page_count)
                except Exception as e:
                    logger.error("Failed to process document", file=str(pdf_file), error=str(e))
    
    async def _extract_principles(self) -> None:
        """Extract architectural principles from processed documents."""
        for document in self.result.documents:
            if document.content:
                principles = self._principle_extractor.extract(
                    document.content,
                    document_id=document.id,
                    document_name=document.name
                )
                self.result.principles.extend(principles)
                logger.info(
                    "Extracted principles",
                    document=document.name,
                    count=len(principles)
                )
    
    async def _analyze_system(self, include_dependencies: bool) -> None:
        """Analyze the current system architecture."""
        system_path = Path(self.config.system_path)
        
        # Load system architecture from configuration and code analysis
        self.result.system = await self._system_analyzer.analyze(
            system_path,
            include_dependencies=include_dependencies
        )
        
        logger.info(
            "System analysis complete",
            components=len(self.result.system.components),
            services=len(self.result.system.services)
        )
    
    async def _identify_gaps(self, severity_levels: Optional[List[GapSeverity]]) -> None:
        """Identify gaps between principles and implementation."""
        filter_severities = severity_levels or self.config.severity_levels
        
        self.result.gaps = await self._gap_analyzer.identify_gaps(
            principles=self.result.principles,
            system=self.result.system,
            severity_filter=filter_severities
        )
        
        logger.info(
            "Gap identification complete",
            total=len(self.result.gaps),
            critical=len([g for g in self.result.gaps if g.severity == GapSeverity.CRITICAL]),
            high=len([g for g in self.result.gaps if g.severity == GapSeverity.HIGH]),
            medium=len([g for g in self.result.gaps if g.severity == GapSeverity.MEDIUM]),
            low=len([g for g in self.result.gaps if g.severity == GapSeverity.LOW])
        )
    
    async def _assess_risks(self) -> None:
        """Assess risks for identified gaps."""
        self.result.gaps = await self._risk_assessor.assess(
            gaps=self.result.gaps,
            system=self.result.system
        )
        
        logger.info("Risk assessment complete")
    
    async def _generate_recommendations(self) -> None:
        """Generate recommendations for addressing gaps."""
        self.result.recommendations = await self._gap_analyzer.generate_recommendations(
            gaps=self.result.gaps,
            system=self.result.system,
            business_metrics_path=self.config.business_metrics_path
        )
        
        logger.info(
            "Recommendations generated",
            count=len(self.result.recommendations)
        )
    
    def _calculate_metrics(self) -> None:
        """Calculate analysis metrics."""
        metrics = Metrics()
        
        metrics.total_principles = len(self.result.principles)
        metrics.total_gaps = len(self.result.gaps)
        metrics.critical_gaps = len([g for g in self.result.gaps if g.severity == GapSeverity.CRITICAL])
        metrics.high_gaps = len([g for g in self.result.gaps if g.severity == GapSeverity.HIGH])
        metrics.medium_gaps = len([g for g in self.result.gaps if g.severity == GapSeverity.MEDIUM])
        metrics.low_gaps = len([g for g in self.result.gaps if g.severity == GapSeverity.LOW])
        metrics.documents_processed = len(self.result.documents)
        metrics.principles_extracted = len(self.result.principles)
        metrics.gaps_identified = len(self.result.gaps)
        metrics.recommendations_generated = len(self.result.recommendations)
        
        # Calculate alignment score (0-100)
        if metrics.total_principles > 0:
            covered_principles = len(set(g.principle_id for g in self.result.gaps if g.severity != GapSeverity.CRITICAL))
            metrics.alignment_score = max(0, 100 - (metrics.critical_gaps * 20) - (metrics.high_gaps * 10) - (metrics.medium_gaps * 5) - (metrics.low_gaps * 1))
        
        # Calculate coverage
        if metrics.total_principles > 0:
            metrics.coverage_percentage = (covered_principles / metrics.total_principles) * 100
        
        self.result.metrics = metrics
    
    async def _generate_reports(self) -> None:
        """Generate output reports in configured formats."""
        for fmt in self.config.output_formats:
            try:
                report_path = self._reporter.generate(
                    result=self.result,
                    format=fmt,
                    output_dir=Path(self.config.output_path),
                    templates_dir=Path(self.config.templates_dir) if self.config.templates_dir else None
                )
                self.result.reports[fmt] = str(report_path)
                logger.info("Report generated", format=fmt.value, path=str(report_path))
            except Exception as e:
                logger.error("Failed to generate report", format=fmt.value, error=str(e))
    
    def generate_implementation_roadmap(
        self,
        timeline_months: int = 12,
        prioritize_business_impact: bool = True
    ) -> Roadmap:
        """
        Generate implementation roadmap from analysis results.
        
        Args:
            timeline_months: Planning horizon in months
            prioritize_business_impact: Whether to prioritize by business impact
            
        Returns:
            Roadmap with phased implementation plan
        """
        if not self.result or self.result.status != AnalysisStatus.COMPLETED:
            raise ValueError("Analysis must be completed before generating roadmap")
        
        # Sort recommendations by priority and business impact
        recommendations = sorted(
            self.result.recommendations,
            key=lambda r: (-r.priority, r.risk_level.value if hasattr(r.risk_level, 'value') else 0)
        )
        
        # Group into phases
        phases = self._create_phases(recommendations, timeline_months)
        
        roadmap = Roadmap(
            analysis_id=self.result.id,
            phases=phases,
            total_estimated_effort=self._estimate_total_effort(recommendations),
            resource_requirements=self._calculate_resource_requirements(recommendations),
            milestones=self._create_milestones(phases),
            risks=self._identify_roadmap_risks(recommendations)
        )
        
        return roadmap
    
    def _create_phases(
        self,
        recommendations: List[Recommendation],
        timeline_months: int
    ) -> List[Dict[str, Any]]:
        """Create phased implementation plan."""
        phases = []
        current_month = 0
        phase_duration = max(1, timeline_months // 3)  # 3 phases
        
        # Quick wins (0 - phase_duration months)
        quick_wins = [r for r in recommendations if r.effort == "quick-win"]
        if quick_wins:
            phases.append({
                "name": "Quick Wins",
                "duration_months": phase_duration,
                "start_month": current_month,
                "end_month": current_month + phase_duration,
                "recommendations": [r.id for r in quick_wins],
                "focus": "Low effort, high impact improvements"
            })
            current_month += phase_duration
        
        # Short-term (phase_duration - 2*phase_duration months)
        short_term = [r for r in recommendations if r.effort == "short-term"]
        if short_term:
            phases.append({
                "name": "Short-term Improvements",
                "duration_months": phase_duration,
                "start_month": current_month,
                "end_month": current_month + phase_duration,
                "recommendations": [r.id for r in short_term],
                "focus": "Strategic improvements with moderate effort"
            })
            current_month += phase_duration
        
        # Long-term (remaining months)
        long_term = [r for r in recommendations if r.effort in ["medium-term", "long-term"]]
        if long_term:
            phases.append({
                "name": "Long-term Enhancements",
                "duration_months": timeline_months - current_month,
                "start_month": current_month,
                "end_month": timeline_months,
                "recommendations": [r.id for r in long_term],
                "focus": "Architectural enhancements and technical debt remediation"
            })
        
        return phases
    
    def _estimate_total_effort(self, recommendations: List[Recommendation]) -> str:
        """Estimate total implementation effort."""
        effort_map = {
            "quick-win": 1,
            "short-term": 3,
            "medium-term": 8,
            "long-term": 16
        }
        total_weeks = sum(effort_map.get(r.effort, 4) for r in recommendations)
        
        if total_weeks <= 4:
            return f"{total_weeks} weeks"
        elif total_weeks <= 52:
            return f"{total_weeks // 4} months"
        else:
            return f"{total_weeks // 52} years"
    
    def _calculate_resource_requirements(self, recommendations: List[Recommendation]) -> Dict[str, Any]:
        """Calculate resource requirements for implementation."""
        roles = {
            "architect": 0,
            "developer": 0,
            "devops": 0,
            "qa": 0,
            "security": 0
        }
        
        for rec in recommendations:
            if "architecture" in rec.title.lower():
                roles["architect"] += 1
            if "implementation" in rec.title.lower() or "code" in rec.description.lower():
                roles["developer"] += 1
            if "deploy" in rec.title.lower() or "infrastructure" in rec.description.lower():
                roles["devops"] += 1
            if "test" in rec.title.lower() or "quality" in rec.description.lower():
                roles["qa"] += 1
            if "security" in rec.title.lower() or "compliance" in rec.description.lower():
                roles["security"] += 1
        
        return {
            "team_composition": roles,
            "estimated_fte": sum(roles.values()) * 0.25,  # 25% allocation per role
            "tools_required": ["CI/CD pipeline", "Monitoring stack", "Security scanner"],
            "infrastructure": ["Development environments", "Staging environment", "Production monitoring"]
        }
    
    def _create_milestones(self, phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create project milestones."""
        milestones = []
        for i, phase in enumerate(phases):
            milestones.append({
                "name": f"Phase {i+1} Complete: {phase['name']}",
                "target_month": phase["end_month"],
                "deliverables": [f"Implement {len(phase['recommendations'])} recommendations"],
                "success_criteria": [
                    "All phase recommendations implemented",
                    "Tests passing",
                    "Documentation updated"
                ]
            })
        return milestones
    
    def _identify_roadmap_risks(self, recommendations: List[Recommendation]) -> List[Dict[str, Any]]:
        """Identify risks for the implementation roadmap."""
        risks = []
        
        critical_count = len([r for r in recommendations if r.risk_level == GapSeverity.CRITICAL])
        if critical_count > 0:
            risks.append({
                "description": f"{critical_count} critical risk recommendations require immediate attention",
                "probability": "high",
                "impact": "critical",
                "mitigation": "Prioritize critical recommendations in first sprint"
            })
        
        if len(recommendations) > 20:
            risks.append({
                "description": "Large number of recommendations may overwhelm team capacity",
                "probability": "medium",
                "impact": "high",
                "mitigation": "Implement strict prioritization and phased approach"
            })
        
        return risks
    
    def generate_executive_summary(self) -> ExecutiveSummary:
        """Generate executive summary for leadership."""
        if not self.result or self.result.status != AnalysisStatus.COMPLETED:
            raise ValueError("Analysis must be completed before generating executive summary")
        
        metrics = self.result.metrics
        
        # Determine overall risk level
        if metrics.critical_gaps > 0:
            risk_level = GapSeverity.CRITICAL
        elif metrics.high_gaps > 0:
            risk_level = GapSeverity.HIGH
        elif metrics.medium_gaps > 0:
            risk_level = GapSeverity.MEDIUM
        else:
            risk_level = GapSeverity.LOW
        
        # Get top recommendations
        top_recs = sorted(
            self.result.recommendations,
            key=lambda r: -r.priority
        )[:5]
        
        return ExecutiveSummary(
            system_name=self.result.system.name,
            analysis_date=datetime.now(),
            overall_alignment_score=metrics.alignment_score,
            critical_findings=metrics.critical_gaps + metrics.high_gaps,
            key_recommendations=[r.title for r in top_recs],
            investment_required=self._estimate_investment(),
            timeline=self._estimate_timeline(),
            risk_level=risk_level,
            next_steps=[
                "Review and approve critical gap remediation",
                "Allocate resources for Phase 1 implementation",
                "Schedule follow-up architecture review in 90 days",
                "Implement monitoring for key metrics"
            ]
        )
    
    def _estimate_investment(self) -> str:
        """Estimate required investment."""
        total_recs = len(self.result.recommendations)
        if total_recs <= 5:
            return "Low ($10K-$50K)"
        elif total_recs <= 15:
            return "Medium ($50K-$200K)"
        else:
            return "High ($200K+)"
    
    def _estimate_timeline(self) -> str:
        """Estimate implementation timeline."""
        effort_map = {
            "quick-win": 1,
            "short-term": 3,
            "medium-term": 8,
            "long-term": 16
        }
        total_weeks = sum(effort_map.get(r.effort, 4) for r in self.result.recommendations)
        
        if total_weeks <= 8:
            return "2-3 months"
        elif total_weeks <= 26:
            return "6-9 months"
        else:
            return "12+ months"
    
    def export_results(self, formats: List[ReportFormat], output_directory: Path) -> Dict[ReportFormat, str]:
        """
        Export analysis results in specified formats.
        
        Args:
            formats: List of output formats
            output_directory: Directory to write output files
            
        Returns:
            Dictionary mapping format to output file path
        """
        if not self.result:
            raise ValueError("No analysis results to export")
        
        output_directory.mkdir(parents=True, exist_ok=True)
        exported = {}
        
        for fmt in formats:
            try:
                report_path = self._reporter.generate(
                    result=self.result,
                    format=fmt,
                    output_dir=output_directory
                )
                exported[fmt] = str(report_path)
            except Exception as e:
                logger.error("Failed to export", format=fmt.value, error=str(e))
        
        return exported


from datetime import datetime