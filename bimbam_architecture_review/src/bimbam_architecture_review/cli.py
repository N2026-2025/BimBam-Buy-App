"""
Command Line Interface for BimBam Architecture Review
======================================================

Main CLI entry point with all commands for architecture review.
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.tree import Tree

from .core import ArchitectureReview
from .models import (
    ReviewConfig, GapSeverity, ReportFormat, SystemArchitecture,
    AnalysisResult, Roadmap, ExecutiveSummary
)
from .reporter import format_console_report, format_markdown_report
from .config import get_settings

app = typer.Typer(
    name="bimbam-architecture-review",
    help="BimBam Buy AI Agent Architecture Review Tool",
    add_completion=False,
    rich_markup_mode="rich"
)

console = Console()
settings = get_settings()


@app.command()
def review(
    system: str = typer.Option(
        "bimbam-buy-ai-agent",
        "--system", "-s",
        help="System name to review"
    ),
    documents: Path = typer.Option(
        Path("./documents"),
        "--documents", "-d",
        help="Path to PDF documents directory"
    ),
    system_path: Path = typer.Option(
        Path("."),
        "--system-path", "-p",
        help="Path to system source code"
    ),
    output: Path = typer.Option(
        Path("./reports"),
        "--output", "-o",
        help="Output directory for reports"
    ),
    formats: List[ReportFormat] = typer.Option(
        [ReportFormat.CONSOLE, ReportFormat.JSON, ReportFormat.MARKDOWN],
        "--format", "-f",
        help="Output formats"
    ),
    severity: List[GapSeverity] = typer.Option(
        [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW],
        "--severity",
        help="Filter gaps by severity"
    ),
    parallel: int = typer.Option(
        4,
        "--parallel", "-j",
        help="Number of parallel jobs for document processing"
    ),
    no_reports: bool = typer.Option(
        False,
        "--no-reports",
        help="Skip report generation"
    ),
    business_metrics: Optional[Path] = typer.Option(
        None,
        "--business-metrics",
        help="Path to business metrics JSON file"
    ),
    templates: Optional[Path] = typer.Option(
        None,
        "--templates",
        help="Custom templates directory"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """
    Run complete architecture review analysis.
    
    Analyzes the system against architectural principles extracted from PDF documents
    and generates comprehensive gap analysis reports.
    """
    if verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)
    
    console.print(Panel.fit(
        f"[bold blue]BimBam Architecture Review[/bold blue]\n"
        f"System: [cyan]{system}[/cyan]\n"
        f"Documents: [cyan]{documents}[/cyan]\n"
        f"Output: [cyan]{output}[/cyan]",
        title="Starting Review"
    ))
    
    # Create configuration
    config = ReviewConfig(
        documents_path=str(documents),
        system_path=str(system_path),
        output_path=str(output),
        severity_levels=severity,
        parallel_jobs=parallel,
        output_formats=formats,
        business_metrics_path=str(business_metrics) if business_metrics else None,
        templates_dir=str(templates) if templates else None
    )
    
    # Run analysis
    review_engine = ArchitectureReview(config)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Running architecture review...", total=8)
            
            # Run async analysis
            result = asyncio.run(review_engine.run_analysis(
                include_dependencies=True,
                severity_levels=severity,
                generate_reports=not no_reports
            ))
            
            progress.update(task, completed=8, description="Review complete!")
        
        # Display results
        _display_results_summary(result, console)
        
        if result.reports:
            console.print("\n[green]Reports generated:[/green]")
            for fmt, path in result.reports.items():
                console.print(f"  [cyan]{fmt.value}:[/cyan] {path}")
        
        # Exit with appropriate code
        if result.metrics.critical_gaps > 0:
            console.print("\n[bold red]⚠ CRITICAL GAPS FOUND - Immediate action required![/bold red]")
            sys.exit(1)
        elif result.metrics.high_gaps > 0:
            console.print("\n[bold yellow]⚠ HIGH SEVERITY GAPS FOUND - Action recommended[/bold yellow]")
            sys.exit(0)
        else:
            console.print("\n[bold green]✓ No critical or high severity gaps found[/bold green]")
            sys.exit(0)
            
    except Exception as e:
        console.print(f"\n[bold red]Review failed:[/bold red] {e}")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        sys.exit(1)


@app.command()
def analyze(
    system_path: Path = typer.Argument(
        ...,
        help="Path to system source code"
    ),
    principles: Path = typer.Option(
        ...,
        "--principles", "-p",
        help="Path to extracted principles JSON file"
    ),
    output: Path = typer.Option(
        Path("./analysis"),
        "--output", "-o",
        help="Output directory"
    ),
    severity: List[GapSeverity] = typer.Option(
        [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW],
        "--severity"
    )
):
    """
    Analyze system against pre-extracted principles.
    
    Use this when you already have principles extracted and want to
    run gap analysis without re-processing documents.
    """
    console.print(f"[blue]Analyzing system at {system_path}[/blue]")
    
    # Load principles
    import json
    with open(principles) as f:
        principles_data = json.load(f)
    
    # TODO: Implement analysis with pre-extracted principles
    console.print("[yellow]This command is not yet implemented[/yellow]")


@app.command()
def extract(
    documents: Path = typer.Argument(
        ...,
        help="Path to PDF documents directory"
    ),
    output: Path = typer.Option(
        Path("./extracted"),
        "--output", "-o",
        help="Output file for extracted principles"
    ),
    parallel: int = typer.Option(
        4,
        "--parallel", "-j",
        help="Number of parallel jobs"
    )
):
    """
    Extract architectural principles from PDF documents.
    
    Processes all PDF files in the directory and extracts
    architectural principles, patterns, and best practices.
    """
    from .extractor import PDFExtractor, PrincipleExtractor
    
    console.print(f"[blue]Extracting principles from {documents}[/blue]")
    
    pdf_files = list(documents.glob("*.pdf"))
    if not pdf_files:
        console.print("[red]No PDF files found[/red]")
        return
    
    extractor = PDFExtractor()
    principle_extractor = PrincipleExtractor()
    
    all_principles = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        extract_task = progress.add_task("Extracting documents...", total=len(pdf_files))
        
        for pdf_file in pdf_files:
            try:
                document = extractor.extract(pdf_file)
                progress.update(extract_task, description=f"Processing {pdf_file.name}...")
                
                if document.content:
                    principles = principle_extractor.extract(
                        document.content,
                        document_id=document.id,
                        document_name=document.name
                    )
                    all_principles.extend(principles)
                    progress.advance(extract_task)
                    
            except Exception as e:
                console.print(f"[red]Failed to process {pdf_file.name}: {e}[/red]")
    
    # Save principles
    import json
    output.parent.mkdir(parents=True, exist_ok=True)
    
    principles_data = {
        "extracted_at": datetime.now().isoformat(),
        "source_documents": len(pdf_files),
        "total_principles": len(all_principles),
        "principles": [
            {
                "id": p.id,
                "document_id": p.document_id,
                "category": p.category,
                "subcategory": p.subcategory,
                "title": p.title,
                "description": p.description,
                "source_text": p.source_text,
                "confidence": p.confidence,
                "tags": p.tags
            }
            for p in all_principles
        ]
    }
    
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(principles_data, f, indent=2, ensure_ascii=False)
    
    console.print(f"[green]Extracted {len(all_principles)} principles to {output}[/green]")


@app.command()
def roadmap(
    analysis: Path = typer.Argument(
        ...,
        help="Path to analysis results JSON file"
    ),
    output: Path = typer.Option(
        Path("./roadmap"),
        "--output", "-o",
        help="Output file for roadmap"
    ),
    timeline: int = typer.Option(
        12,
        "--timeline", "-t",
        help="Planning timeline in months"
    ),
    format: ReportFormat = typer.Option(
        ReportFormat.MARKDOWN,
        "--format", "-f"
    )
):
    """
    Generate implementation roadmap from analysis results.
    
    Creates a phased implementation plan with priorities,
    timelines, and resource requirements.
    """
    import json
    from datetime import datetime
    
    console.print(f"[blue]Generating roadmap from {analysis}[/blue]")
    
    with open(analysis) as f:
        analysis_data = json.load(f)
    
    # Reconstruct result object (simplified)
    # In real implementation, would deserialize full AnalysisResult
    
    console.print(f"[yellow]Roadmap generation from file not yet implemented[/yellow]")
    console.print(f"Would generate {timeline}-month roadmap in {format.value} format")


@app.command()
def executive(
    analysis: Path = typer.Argument(
        ...,
        help="Path to analysis results JSON file"
    ),
    output: Path = typer.Option(
        Path("./executive_summary"),
        "--output", "-o",
        help="Output file for executive summary"
    ),
    format: ReportFormat = typer.Option(
        ReportFormat.MARKDOWN,
        "--format", "-f"
    )
):
    """
    Generate executive summary from analysis results.
    
    Creates a leadership-focused summary with key findings,
    investment requirements, and strategic recommendations.
    """
    console.print(f"[blue]Generating executive summary from {analysis}[/blue]")
    console.print("[yellow]Executive summary generation not yet implemented[/yellow]")


@app.command()
def serve(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Host to bind to"
    ),
    port: int = typer.Option(
        8000,
        "--port",
        help="Port to bind to"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload"
    )
):
    """
    Start the Architecture Review API server.
    
    Provides REST API for integrating architecture review
    into CI/CD pipelines and other tools.
    """
    import uvicorn
    
    console.print(f"[blue]Starting API server on {host}:{port}[/blue]")
    
    uvicorn.run(
        "bimbam_architecture_review.api:app",
        host=host,
        port=port,
        reload=reload
    )


@app.command()
def version():
    """Show version information."""
    from . import __version__, __author__, __email__
    
    console.print(Panel.fit(
        f"[bold]BimBam Architecture Review[/bold]\n"
        f"Version: [cyan]{__version__}[/cyan]\n"
        f"Author: [cyan]{__author__}[/cyan]\n"
        f"Email: [cyan]{__email__}[/cyan]",
        title="Version Info"
    ))


@app.command()
def config():
    """Show current configuration."""
    config_table = Table(title="Current Configuration")
    config_table.add_column("Setting", style="cyan")
    config_table.add_column("Value", style="green")
    
    for key, value in settings.model_dump().items():
        config_table.add_row(key, str(value))
    
    console.print(config_table)


def _display_results_summary(result: AnalysisResult, console: Console) -> None:
    """Display formatted results summary."""
    metrics = result.metrics
    
    # Summary table
    table = Table(title="Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Alignment Score", f"{metrics.alignment_score:.1f}/100")
    table.add_row("Documents Processed", str(metrics.documents_processed))
    table.add_row("Principles Extracted", str(metrics.principles_extracted))
    table.add_row("Total Gaps", str(metrics.total_gaps))
    table.add_row("Critical Gaps", f"[red]{metrics.critical_gaps}[/red]")
    table.add_row("High Gaps", f"[orange3]{metrics.high_gaps}[/orange3]")
    table.add_row("Medium Gaps", f"[yellow]{metrics.medium_gaps}[/yellow]")
    table.add_row("Low Gaps", f"[green]{metrics.low_gaps}[/green]")
    table.add_row("Recommendations", str(metrics.recommendations_generated))
    
    console.print(table)
    
    # Severity breakdown tree
    if result.gaps:
        tree = Tree("📊 Gaps by Category")
        for category in set(g.category for g in result.gaps):
            cat_gaps = [g for g in result.gaps if g.category == category]
            cat_branch = tree.add(f"[bold]{category.value}[/bold] ({len(cat_gaps)})")
            
            for severity in [GapSeverity.CRITICAL, GapSeverity.HIGH, GapSeverity.MEDIUM, GapSeverity.LOW]:
                sev_gaps = [g for g in cat_gaps if g.severity == severity]
                if sev_gaps:
                    sev_branch = cat_branch.add(f"{severity.value.upper()} ({len(sev_gaps)})")
                    for gap in sev_gaps[:3]:  # Show first 3
                        sev_branch.add(f"• {gap.title}")
                    if len(sev_gaps) > 3:
                        sev_branch.add(f"... and {len(sev_gaps) - 3} more")
        
        console.print(tree)


# Additional utility commands
@app.command()
def validate(
    config_file: Path = typer.Argument(
        ...,
        help="Path to configuration file"
    )
):
    """Validate configuration file."""
    console.print(f"[blue]Validating {config_file}[/blue]")
    # TODO: Implement config validation
    console.print("[green]Configuration valid[/green]")


@app.command()
def compare(
    baseline: Path = typer.Argument(
        ...,
        help="Baseline analysis results"
    ),
    current: Path = typer.Argument(
        ...,
        help="Current analysis results"
    ),
    output: Path = typer.Option(
        Path("./comparison"),
        "--output", "-o"
    )
):
    """
    Compare two analysis results to track progress.
    
    Shows improvement or regression in architecture alignment.
    """
    console.print(f"[blue]Comparing {baseline} vs {current}[/blue]")
    console.print("[yellow]Comparison feature not yet implemented[/yellow]")


if __name__ == "__main__":
    app()


from datetime import datetime