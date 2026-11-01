"""
Report Generator for Architecture Review
=========================================

Generates reports in multiple formats: console, JSON, Markdown, HTML, PDF.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import (
    AnalysisResult, ReportFormat, Gap, GapSeverity, GapCategory,
    Recommendation, Metrics, SystemArchitecture, Roadmap, ExecutiveSummary
)
from .config import get_settings

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates architecture review reports in multiple formats.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self._setup_templates()
    
    def _setup_templates(self) -> None:
        """Setup Jinja2 template environment."""
        template_dir = Path(__file__).parent / "templates"
        if template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None
    
    def generate(
        self,
        result: AnalysisResult,
        format: ReportFormat,
        output_dir: Path,
        templates_dir: Optional[Path] = None
    ) -> Path:
        """
        Generate report in specified format.
        
        Args:
            result: Analysis results
            format: Output format
            output_dir: Output directory
            templates_dir: Custom templates directory
            
        Returns:
            Path to generated report file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if format == ReportFormat.CONSOLE:
            return self._generate_console(result, output_dir, timestamp)
        elif format == ReportFormat.JSON:
            return self._generate_json(result, output_dir, timestamp)
        elif format == ReportFormat.MARKDOWN:
            return self._generate_markdown(result, output_dir, timestamp)
        elif format == ReportFormat.HTML:
            return self._generate_html(result, output_dir, timestamp, templates_dir)
        elif format == ReportFormat.PDF:
            return self._generate_pdf(result, output_dir, timestamp)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_console(
        self,
        result: AnalysisResult,
        output_dir: Path,
        timestamp: str
    ) -> Path:
        """Generate console-friendly text report."""
        output_file = output_dir / f"architecture_review_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self._format_console_report(result))
        
        # Also print to console
        print(self._format_console_report(result))
        
        return output_file
    
    def _format_console_report(self, result: AnalysisResult) -> str:
        """Format report for console output."""
        lines = []
        metrics = result.metrics
        
        lines.append("=" * 80)
        lines.append("BIMBAM BUY AI AGENT - ARCHITECTURE REVIEW REPORT")
        lines.append("=" * 80)
        lines.append(f"System: {result.system.name} v{result.system.version}")
        lines.append(f"Analysis Date: {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration: {metrics.analysis_duration_seconds:.1f}s")
        lines.append("")
        
        # Executive Summary
        lines.append("-" * 80)
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        lines.append(f"Overall Alignment Score: {metrics.alignment_score:.1f}/100")
        lines.append(f"Documents Analyzed: {metrics.documents_processed}")
        lines.append(f"Principles Extracted: {metrics.principles_extracted}")
        lines.append(f"Gaps Identified: {metrics.total_gaps}")
        lines.append(f"  Critical: {metrics.critical_gaps}")
        lines.append(f"  High:     {metrics.high_gaps}")
        lines.append(f"  Medium:   {metrics.medium_gaps}")
        lines.append(f"  Low:      {metrics.low_gaps}")
        lines.append(f"Recommendations: {metrics.recommendations_generated}")
        lines.append("")
        
        # Critical Gaps
        critical_gaps = [g for g in result.gaps if g.severity == GapSeverity.CRITICAL]
        if critical_gaps:
            lines.append("-" * 80)
            lines.append("CRITICAL GAPS (IMMEDIATE ACTION REQUIRED)")
            lines.append("-" * 80)
            for i, gap in enumerate(critical_gaps, 1):
                lines.append(f"\n{i}. {gap.title}")
                lines.append(f"   Category: {gap.category.value}")
                lines.append(f"   Description: {gap.description}")
                lines.append(f"   Current: {gap.current_state}")
                lines.append(f"   Expected: {gap.expected_state}")
                lines.append(f"   Impact: {gap.impact}")
                lines.append(f"   Effort: {gap.effort_estimate}")
        
        # High Gaps
        high_gaps = [g for g in result.gaps if g.severity == GapSeverity.HIGH]
        if high_gaps:
            lines.append(f"\n{'=' * 80}")
            lines.append("HIGH SEVERITY GAPS")
            lines.append("=" * 80)
            for i, gap in enumerate(high_gaps, 1):
                lines.append(f"\n{i}. {gap.title}")
                lines.append(f"   Category: {gap.category.value}")
                lines.append(f"   Impact: {gap.impact}")
                lines.append(f"   Effort: {gap.effort_estimate}")
        
        # Top Recommendations
        top_recs = sorted(result.recommendations, key=lambda r: -r.priority)[:10]
        if top_recs:
            lines.append(f"\n{'=' * 80}")
            lines.append("TOP RECOMMENDATIONS")
            lines.append("=" * 80)
            for i, rec in enumerate(top_recs, 1):
                lines.append(f"\n{i}. {rec.title} [Priority: {rec.priority}]")
                lines.append(f"   Effort: {rec.effort} | Timeline: {rec.estimated_timeline}")
                lines.append(f"   {rec.description[:150]}...")
        
        # Technology Stack
        lines.append(f"\n{'=' * 80}")
        lines.append("TECHNOLOGY STACK")
        lines.append("=" * 80)
        for tech in sorted(result.system.technologies):
            lines.append(f"  - {tech}")
        
        lines.append(f"\n{'=' * 80}")
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)
    
    def _generate_json(
        self,
        result: AnalysisResult,
        output_dir: Path,
        timestamp: str
    ) -> Path:
        """Generate JSON report."""
        output_file = output_dir / f"architecture_review_{timestamp}.json"
        
        # Convert to serializable dict
        data = {
            "metadata": {
                "system": result.system.name,
                "version": result.system.version,
                "analysis_date": result.started_at.isoformat(),
                "duration_seconds": result.metrics.analysis_duration_seconds,
                "status": result.status.value
            },
            "metrics": {
                "alignment_score": result.metrics.alignment_score,
                "documents_processed": result.metrics.documents_processed,
                "principles_extracted": result.metrics.principles_extracted,
                "total_gaps": result.metrics.total_gaps,
                "gaps_by_severity": {
                    "critical": result.metrics.critical_gaps,
                    "high": result.metrics.high_gaps,
                    "medium": result.metrics.medium_gaps,
                    "low": result.metrics.low_gaps
                },
                "recommendations_generated": result.metrics.recommendations_generated
            },
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
                    "technical_debt": g.technical_debt,
                    "detected_at": g.detected_at.isoformat()
                }
                for g in result.gaps
            ],
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
                for r in result.recommendations
            ],
            "system": {
                "name": result.system.name,
                "version": result.system.version,
                "technologies": result.system.technologies,
                "components_count": len(result.system.components),
                "services_count": len(result.system.services)
            }
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def _generate_markdown(
        self,
        result: AnalysisResult,
        output_dir: Path,
        timestamp: str
    ) -> Path:
        """Generate Markdown report."""
        output_file = output_dir / f"architecture_review_{timestamp}.md"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(self._format_markdown_report(result))
        
        return output_file
    
    def _format_markdown_report(self, result: AnalysisResult) -> str:
        """Format report as Markdown."""
        lines = []
        metrics = result.metrics
        
        # Header
        lines.append(f"# Architecture Review: {result.system.name} v{result.system.version}")
        lines.append("")
        lines.append(f"**Analysis Date:** {result.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Duration:** {metrics.analysis_duration_seconds:.1f}s")
        lines.append(f"**Status:** {result.status.value}")
        lines.append("")
        
        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(f"- **Overall Alignment Score:** {metrics.alignment_score:.1f}/100")
        lines.append(f"- **Documents Analyzed:** {metrics.documents_processed}")
        lines.append(f"- **Principles Extracted:** {metrics.principles_extracted}")
        lines.append(f"- **Total Gaps Identified:** {metrics.total_gaps}")
        lines.append(f"  - **Critical:** {metrics.critical_gaps}")
        lines.append(f"  - **High:** {metrics.high_gaps}")
        lines.append(f"  - **Medium:** {metrics.medium_gaps}")
        lines.append(f"  - **Low:** {metrics.low_gaps}")
        lines.append(f"- **Recommendations Generated:** {metrics.recommendations_generated}")
        lines.append("")
        
        # Gaps by Severity
        for severity in [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW]:
            severity_gaps = [g for g in result.gaps if g.severity == severity]
            if severity_gaps:
                lines.append(f"## {severity.value.upper()} Gaps ({len(severity_gaps)})")
                lines.append("")
                for gap in severity_gaps:
                    lines.append(f"### {gap.title}")
                    lines.append("")
                    lines.append(f"- **Category:** {gap.category.value}")
                    lines.append(f"- **Severity:** {gap.severity.value}")
                    lines.append(f"- **Description:** {gap.description}")
                    lines.append(f"- **Current State:** {gap.current_state}")
                    lines.append(f"- **Expected State:** {gap.expected_state}")
                    lines.append(f"- **Impact:** {gap.impact}")
                    lines.append(f"- **Effort Estimate:** {gap.effort_estimate}")
                    if gap.business_impact:
                        lines.append(f"- **Business Impact:** {gap.business_impact}")
                    lines.append("")
        
        # Recommendations
        if result.recommendations:
            lines.append("## Recommendations")
            lines.append("")
            for rec in sorted(result.recommendations, key=lambda r: -r.priority):
                lines.append(f"### {rec.title} (Priority: {rec.priority})")
                lines.append("")
                lines.append(f"- **Effort:** {rec.effort}")
                lines.append(f"- **Timeline:** {rec.estimated_timeline}")
                lines.append(f"- **Risk Level:** {rec.risk_level.value}")
                lines.append(f"- **Description:** {rec.description}")
                lines.append(f"- **Resources:** {', '.join(rec.resources) if rec.resources else 'TBD'}")
                lines.append(f"- **Success Criteria:**")
                for criterion in rec.success_criteria:
                    lines.append(f"  - {criterion}")
                lines.append("")
        
        # Technology Stack
        lines.append("## Technology Stack")
        lines.append("")
        for tech in sorted(result.system.technologies):
            lines.append(f"- {tech}")
        lines.append("")
        
        # Components
        if result.system.components:
            lines.append("## System Components")
            lines.append("")
            for comp in result.system.components:
                lines.append(f"- **{comp.get('name', 'Unknown')}** ({comp.get('type', 'unknown')})")
        lines.append("")
        
        # Data Flows
        if result.system.data_flows:
            lines.append("## Data Flows")
            lines.append("")
            for flow in result.system.data_flows:
                lines.append(f"### {flow.get('name', 'Data Flow')}")
                lines.append(f"- **Source:** {flow.get('source', 'N/A')}")
                lines.append(f"- **Destination:** {flow.get('destination', 'N/A')}")
                lines.append(f"- **Transformation:** {flow.get('transformation', 'N/A')}")
                lines.append("")
        
        # Footer
        lines.append("---")
        lines.append(f"*Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        
        return "\n".join(lines)
    
    def _generate_html(
        self,
        result: AnalysisResult,
        output_dir: Path,
        timestamp: str,
        templates_dir: Optional[Path] = None
    ) -> Path:
        """Generate HTML report using Jinja2 template."""
        output_file = output_dir / f"architecture_review_{timestamp}.html"
        
        # Prepare template data
        template_data = self._prepare_template_data(result)
        
        # Use custom template if available, otherwise use built-in
        if templates_dir and (templates_dir / "report.html.j2").exists():
            env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=select_autoescape(['html', 'xml'])
            )
            template = env.get_template("report.html.j2")
        elif self.jinja_env:
            try:
                template = self.jinja_env.get_template("report.html.j2")
            except Exception:
                template = self._get_builtin_html_template()
        else:
            template = self._get_builtin_html_template()
        
        html_content = template.render(**template_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def _prepare_template_data(self, result: AnalysisResult) -> Dict[str, Any]:
        """Prepare data for template rendering."""
        return {
            "system": result.system,
            "metrics": result.metrics,
            "gaps": result.gaps,
            "recommendations": sorted(result.recommendations, key=lambda r: -r.priority),
            "generated_at": datetime.now(),
            "analysis_date": result.started_at,
            "duration": result.metrics.analysis_duration_seconds,
            "GapSeverity": GapSeverity,
            "GapCategory": GapCategory,
            "get_severity_color": self._get_severity_color,
            "get_severity_icon": self._get_severity_icon
        }
    
    def _get_severity_color(self, severity: GapSeverity) -> str:
        """Get color for severity level."""
        colors = {
            GapSeverity.CRITICAL: "#dc3545",
            GapSeverity.HIGH: "#fd7e14",
            GapSeverity.MEDIUM: "#ffc107",
            GapSeverity.LOW: "#28a745"
        }
        return colors.get(severity, "#6c757d")
    
    def _get_severity_icon(self, severity: GapSeverity) -> str:
        """Get icon for severity level."""
        icons = {
            GapSeverity.CRITICAL: "🔴",
            GapSeverity.HIGH: "🟠",
            GapSeverity.MEDIUM: "🟡",
            GapSeverity.LOW: "🟢"
        }
        return icons.get(severity, "⚪")
    
    def _get_builtin_html_template(self):
        """Get built-in HTML template as string."""
        from jinja2 import Template
        
        template_str = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Architecture Review: {{ system.name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 3px solid #007bff; padding-bottom: 10px; }
        h2 { color: #444; margin-top: 30px; }
        h3 { color: #555; }
        .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .metric-card { background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #007bff; }
        .metric-label { color: #666; font-size: 0.9em; }
        .gap { border-left: 4px solid; padding: 15px; margin: 15px 0; background: #f8f9fa; border-radius: 4px; }
        .gap.critical { border-color: #dc3545; }
        .gap.high { border-color: #fd7e14; }
        .gap.medium { border-color: #ffc107; }
        .gap.low { border-color: #28a745; }
        .severity-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; color: white; }
        .severity-critical { background: #dc3545; }
        .severity-high { background: #fd7e14; }
        .severity-medium { background: #ffc107; color: #333; }
        .severity-low { background: #28a745; }
        .recommendation { background: #e7f3ff; border-left: 4px solid #007bff; padding: 15px; margin: 15px 0; border-radius: 4px; }
        .tech-stack { display: flex; flex-wrap: wrap; gap: 8px; }
        .tech-tag { background: #e9ecef; padding: 4px 12px; border-radius: 20px; font-size: 0.85em; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Architecture Review: {{ system.name }} v{{ system.version }}</h1>
        <p><strong>Analysis Date:</strong> {{ analysis_date.strftime('%Y-%m-%d %H:%M:%S') }} | <strong>Duration:</strong> {{ duration|round(1) }}s</p>
        
        <h2>Executive Summary</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-value">{{ "%.1f"|format(metrics.alignment_score) }}/100</div>
                <div class="metric-label">Alignment Score</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ metrics.total_gaps }}</div>
                <div class="metric-label">Total Gaps</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ metrics.critical_gaps + metrics.high_gaps }}</div>
                <div class="metric-label">Critical/High</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ metrics.recommendations_generated }}</div>
                <div class="metric-label">Recommendations</div>
            </div>
        </div>
        
        <h2>Gap Analysis</h2>
        {% for severity in [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW] %}
            {% set severity_gaps = gaps|selectattr('severity', 'equalto', severity)|list %}
            {% if severity_gaps %}
                <h3>{{ severity.value.upper }} Gaps ({{ severity_gaps|length }})</h3>
                {% for gap in severity_gaps %}
                    <div class="gap {{ severity.value }}">
                        <h4>{{ gap.title }} <span class="severity-badge severity-{{ severity.value }}">{{ severity.value.upper }}</span></h4>
                        <p><strong>Category:</strong> {{ gap.category.value }}</p>
                        <p>{{ gap.description }}</p>
                        <p><strong>Current:</strong> {{ gap.current_state }}</p>
                        <p><strong>Expected:</strong> {{ gap.expected_state }}</p>
                        <p><strong>Impact:</strong> {{ gap.impact }}</p>
                        <p><strong>Effort:</strong> {{ gap.effort_estimate }}</p>
                    </div>
                {% endfor %}
            {% endif %}
        {% endfor %}
        
        <h2>Top Recommendations</h2>
        {% for rec in recommendations[:10] %}
            <div class="recommendation">
                <h4>{{ rec.title }} <span class="severity-badge severity-{{ rec.risk_level.value }}">Priority: {{ rec.priority }}</span></h4>
                <p>{{ rec.description }}</p>
                <p><strong>Effort:</strong> {{ rec.effort }} | <strong>Timeline:</strong> {{ rec.estimated_timeline }}</p>
            </div>
        {% endfor %}
        
        <h2>Technology Stack</h2>
        <div class="tech-stack">
            {% for tech in system.technologies|sort %}
                <span class="tech-tag">{{ tech }}</span>
            {% endfor %}
        </div>
        
        <div class="footer">
            <p>Report generated on {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            <p>BimBam Buy AI Agent Architecture Review Tool v1.0.0</p>
        </div>
    </div>
</body>
</html>
        """
        return Template(template_str)
    
    def _generate_pdf(
        self,
        result: AnalysisResult,
        output_dir: Path,
        timestamp: str
    ) -> Path:
        """Generate PDF report via HTML conversion."""
        # First generate HTML
        html_file = self._generate_html(result, output_dir, timestamp)
        
        # Convert to PDF using weasyprint
        try:
            from weasyprint import HTML
            pdf_file = output_dir / f"architecture_review_{timestamp}.pdf"
            HTML(str(html_file)).write_pdf(str(pdf_file))
            return pdf_file
        except ImportError:
            logger.warning("weasyprint not available, returning HTML file instead")
            return html_file
        except Exception as e:
            logger.error("PDF generation failed", error=str(e))
            return html_file


# Also export the console formatter for direct use
def format_console_report(result: AnalysisResult) -> str:
    """Format analysis result as console report."""
    generator = ReportGenerator()
    return generator._format_console_report(result)


def format_markdown_report(result: AnalysisResult) -> str:
    """Format analysis result as Markdown report."""
    generator = ReportGenerator()
    return generator._format_markdown_report(result)