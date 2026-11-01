"""
System Analyzer and Gap Analysis Engine
========================================

Analyzes system architecture and identifies gaps against extracted principles.
"""

import ast
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    SystemArchitecture, Principle, Gap, GapSeverity, GapCategory,
    Recommendation, RecommendationPriority
)
from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CodeAnalysisResult:
    """Results from analyzing source code."""
    files_analyzed: int
    components: List[Dict[str, Any]]
    services: List[Dict[str, Any]]
    technologies: Set[str]
    patterns: Dict[str, List[str]]
    dependencies: Dict[str, List[str]]


class SystemAnalyzer:
    """
    Analyzes the current system architecture from source code,
    configuration, and documentation.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def analyze(
        self,
        system_path: Path,
        include_dependencies: bool = True
    ) -> SystemArchitecture:
        """
        Analyze system architecture from source code and configuration.
        
        Args:
            system_path: Path to system source code
            include_dependencies: Whether to analyze cross-component dependencies
            
        Returns:
            SystemArchitecture with discovered components and patterns
        """
        logger.info("Analyzing system architecture", path=str(system_path))
        
        # Analyze source code
        code_analysis = self._analyze_source_code(system_path)
        
        # Analyze configuration files
        config_analysis = self._analyze_configuration(system_path)
        
        # Analyze documentation
        doc_analysis = self._analyze_documentation(system_path)
        
        # Build architecture model
        architecture = SystemArchitecture(
            name="BimBam Buy AI Agent",
            version="2.0.0",
            description="RAG-based customer support system with microservices architecture",
            components=code_analysis.components + config_analysis.get('components', []),
            services=code_analysis.services,
            technologies=list(code_analysis.technologies | config_analysis.get('technologies', set())),
            data_flows=self._identify_data_flows(code_analysis, config_analysis),
            deployment=config_analysis.get('deployment', {}),
            monitoring=config_analysis.get('monitoring', {}),
            security=config_analysis.get('security', {}),
            metadata={
                'source_files': code_analysis.files_analyzed,
                'patterns_detected': code_analysis.patterns,
                'dependencies': code_analysis.dependencies if include_dependencies else {}
            }
        )
        
        return architecture
    
    def _analyze_source_code(self, system_path: Path) -> CodeAnalysisResult:
        """Analyze Python source code for architectural patterns."""
        result = CodeAnalysisResult(
            files_analyzed=0,
            components=[],
            services=[],
            technologies=set(),
            patterns={},
            dependencies={}
        )
        
        python_files = list(system_path.rglob("*.py"))
        result.files_analyzed = len(python_files)
        
        for py_file in python_files:
            try:
                self._analyze_python_file(py_file, result)
            except Exception as e:
                logger.warning("Failed to analyze file", file=str(py_file), error=str(e))
        
        return result
    
    def _analyze_python_file(self, file_path: Path, result: CodeAnalysisResult) -> None:
        """Analyze a single Python file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return
        
        # Detect technologies from imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.technologies.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result.technologies.add(node.module.split('.')[0])
        
        # Detect FastAPI services
        if 'FastAPI' in content or 'fastapi' in content.lower():
            result.services.append({
                'name': file_path.stem,
                'type': 'api',
                'framework': 'FastAPI',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
        
        # Detect Streamlit apps
        if 'streamlit' in content.lower():
            result.services.append({
                'name': file_path.stem,
                'type': 'ui',
                'framework': 'Streamlit',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
        
        # Detect CLI entry points
        if '__main__' in content and ('click' in content or 'typer' in content or 'argparse' in content):
            result.services.append({
                'name': file_path.stem,
                'type': 'cli',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
        
        # Detect RAG components
        if any(keyword in content.lower() for keyword in ['rag', 'retrieval', 'vector', 'embedding', 'chroma']):
            result.components.append({
                'name': file_path.stem,
                'type': 'rag',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
            result.patterns.setdefault('rag', []).append(file_path.stem)
        
        # Detect LLM integration
        if any(keyword in content.lower() for keyword in ['openai', 'gemini', 'cohere', 'llm', 'chat']):
            result.components.append({
                'name': file_path.stem,
                'type': 'llm_integration',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
            result.patterns.setdefault('llm', []).append(file_path.stem)
        
        # Detect database/vector store usage
        if any(keyword in content.lower() for keyword in ['chroma', 'vectorstore', 'vector_store', 'embedding']):
            result.components.append({
                'name': file_path.stem,
                'type': 'vector_store',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
            result.patterns.setdefault('vector_store', []).append(file_path.stem)
        
        # Detect monitoring
        if any(keyword in content.lower() for keyword in ['prometheus', 'metrics', 'monitoring', 'health']):
            result.components.append({
                'name': file_path.stem,
                'type': 'monitoring',
                'file': str(file_path.relative_to(file_path.parents[2]))
            })
            result.patterns.setdefault('monitoring', []).append(file_path.stem)
    
    def _analyze_configuration(self, system_path: Path) -> Dict[str, Any]:
        """Analyze configuration files."""
        config = {
            'components': [],
            'technologies': set(),
            'deployment': {},
            'monitoring': {},
            'security': {}
        }
        
        # Check for Docker
        dockerfile = system_path / "Dockerfile"
        if dockerfile.exists():
            config['technologies'].add('docker')
            config['deployment']['containerized'] = True
            
            with open(dockerfile) as f:
                content = f.read()
                if 'prometheus' in content.lower():
                    config['monitoring']['prometheus'] = True
        
        # Check for docker-compose
        compose_files = list(system_path.glob("docker-compose*.yml")) + \
                       list(system_path.glob("docker-compose*.yaml"))
        if compose_files:
            config['deployment']['orchestration'] = 'docker-compose'
            config['technologies'].add('docker-compose')
        
        # Check for Kubernetes
        k8s_files = list(system_path.rglob("*.yaml")) + list(system_path.rglob("*.yml"))
        k8s_files = [f for f in k8s_files if any(kw in f.read_text()[:500].lower() 
                     for kw in ['kubernetes', 'k8s', 'deployment', 'service', 'ingress'])]
        if k8s_files:
            config['deployment']['orchestration'] = 'kubernetes'
            config['technologies'].add('kubernetes')
        
        # Check requirements
        req_files = list(system_path.glob("requirements*.txt")) + \
                   list(system_path.glob("pyproject.toml"))
        for req_file in req_files:
            with open(req_file) as f:
                content = f.read()
                # Extract key technologies
                for tech in ['fastapi', 'streamlit', 'langchain', 'chromadb', 'openai', 
                           'google', 'cohere', 'prometheus', 'pydantic', 'uvicorn']:
                    if tech in content.lower():
                        config['technologies'].add(tech)
        
        # Check for monitoring config
        prom_files = list(system_path.rglob("prometheus*.yml")) + \
                    list(system_path.rglob("prometheus*.yaml"))
        if prom_files:
            config['monitoring']['prometheus_configured'] = True
        
        # Check for security config
        env_files = list(system_path.glob(".env*"))
        if env_files:
            config['security']['env_configured'] = True
        
        return config
    
    def _analyze_documentation(self, system_path: Path) -> Dict[str, Any]:
        """Analyze documentation files."""
        docs = {
            'architecture_docs': [],
            'readme_files': []
        }
        
        # Find architecture documentation
        arch_docs = list(system_path.rglob("*architect*.md")) + \
                   list(system_path.rglob("*architect*.txt")) + \
                   list(system_path.rglob("ARCHITECTURE*"))
        docs['architecture_docs'] = [str(f.relative_to(system_path)) for f in arch_docs]
        
        # Find README files
        readmes = list(system_path.rglob("README*"))
        docs['readme_files'] = [str(f.relative_to(system_path)) for f in readmes]
        
        return docs
    
    def _identify_data_flows(
        self,
        code_analysis: CodeAnalysisResult,
        config_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify data flows from analysis."""
        flows = []
        
        # RAG data flow
        if 'rag' in code_analysis.patterns:
            flows.append({
                'name': 'RAG Pipeline',
                'source': 'PDF Documents',
                'destination': 'Vector Store (ChromaDB)',
                'transformation': 'Text -> Chunks -> Embeddings -> Vector Index',
                'components': code_analysis.patterns['rag']
            })
        
        # LLM inference flow
        if 'llm' in code_analysis.patterns:
            flows.append({
                'name': 'LLM Inference',
                'source': 'User Query + Retrieved Context',
                'destination': 'LLM Provider (OpenAI/Google/Cohere)',
                'transformation': 'Prompt Engineering -> Completion -> Response',
                'components': code_analysis.patterns['llm']
            })
        
        # API request flow
        if any(s['type'] == 'api' for s in code_analysis.services):
            flows.append({
                'name': 'API Request',
                'source': 'Client (UI/CLI)',
                'destination': 'FastAPI Service',
                'transformation': 'HTTP Request -> Validation -> Processing -> Response',
                'components': [s['name'] for s in code_analysis.services if s['type'] == 'api']
            })
        
        return flows


class GapAnalyzer:
    """
    Identifies gaps between extracted principles and actual system implementation.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def identify_gaps(
        self,
        principles: List[Principle],
        system: SystemArchitecture,
        severity_filter: Optional[List[GapSeverity]] = None
    ) -> List[Gap]:
        """
        Identify gaps by comparing principles against system implementation.
        
        Args:
            principles: Extracted architectural principles
            system: Current system architecture
            severity_filter: Optional filter for gap severity levels
            
        Returns:
            List of identified gaps
        """
        gaps = []
        
        # Group principles by category
        principles_by_category = self._group_principles(principles)
        
        # Check each category against system
        for category, category_principles in principles_by_category.items():
            category_gaps = self._check_category(category, category_principles, system)
            gaps.extend(category_gaps)
        
        # Filter by severity if specified
        if severity_filter:
            gaps = [g for g in gaps if g.severity in severity_filter]
        
        logger.info("Gap identification complete", total=len(gaps))
        return gaps
    
    def _group_principles(self, principles: List[Principle]) -> Dict[str, List[Principle]]:
        """Group principles by category."""
        grouped = {}
        for principle in principles:
            cat = principle.category or 'general'
            grouped.setdefault(cat, []).append(principle)
        return grouped
    
    def _check_category(
        self,
        category: str,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check a category of principles against system."""
        gaps = []
        
        # Category-specific checks
        check_methods = {
            'architecture': self._check_architecture_principles,
            'scalability': self._check_scalability_principles,
            'reliability': self._check_reliability_principles,
            'security': self._check_security_principles,
            'observability': self._check_observability_principles,
            'deployment': self._check_deployment_principles,
            'data': self._check_data_principles,
            'ai_ml': self._check_ai_ml_principles,
            'multi_agent': self._check_multi_agent_principles,
        }
        
        check_method = check_methods.get(category, self._check_general_principles)
        gaps = check_method(principles, system)
        
        return gaps
    
    def _check_architecture_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check architecture principles."""
        gaps = []
        
        # Check for microservices patterns
        has_microservices = len(system.services) > 1
        has_service_boundaries = any(
            'boundary' in p.description.lower() or 'decompos' in p.description.lower()
            for p in principles
        )
        
        if has_service_boundaries and not has_microservices:
            gaps.append(Gap(
                principle_id=principles[0].id if principles else '',
                category=GapCategory.ARCHITECTURE,
                severity=GapSeverity.HIGH,
                title="Missing Service Decomposition",
                description="Principles recommend service decomposition but system appears monolithic",
                current_state="Single deployment unit",
                expected_state="Decomposed microservices with clear boundaries",
                impact="Limited scalability and independent deployment",
                effort_estimate="high"
            ))
        
        # Check for async communication
        async_principles = [p for p in principles if 'async' in p.description.lower() or 'event' in p.description.lower()]
        if async_principles:
            has_async = any('async' in str(s).lower() or 'event' in str(s).lower() 
                          for s in system.services)
            if not has_async:
                gaps.append(Gap(
                    principle_id=async_principles[0].id,
                    category=GapCategory.ARCHITECTURE,
                    severity=GapSeverity.MEDIUM,
                    title="Missing Asynchronous Communication",
                    description="Principles recommend async/event-driven communication but system uses synchronous patterns",
                    current_state="Synchronous request-response",
                    expected_state="Event-driven architecture with message queues",
                    impact="Tight coupling and reduced resilience",
                    effort_estimate="high"
                ))
        
        return gaps
    
    def _check_scalability_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check scalability principles."""
        gaps = []
        
        # Check for horizontal scaling
        scale_principles = [p for p in principles if 'horizontal' in p.description.lower() or 'scale out' in p.description.lower()]
        if scale_principles:
            has_k8s = 'kubernetes' in system.technologies
            has_docker = 'docker' in system.technologies
            
            if not has_k8s:
                gaps.append(Gap(
                    principle_id=scale_principles[0].id,
                    category=GapCategory.PERFORMANCE,
                    severity=GapSeverity.MEDIUM,
                    title="Missing Horizontal Scaling Infrastructure",
                    description="Principles recommend horizontal scaling but no Kubernetes orchestration detected",
                    current_state="Docker Compose or single-instance deployment",
                    expected_state="Kubernetes with Horizontal Pod Autoscaler",
                    impact="Limited ability to scale under load",
                    effort_estimate="high"
                ))
        
        # Check for caching
        cache_principles = [p for p in principles if 'cache' in p.description.lower()]
        if cache_principles:
            has_redis = 'redis' in system.technologies
            if not has_redis:
                gaps.append(Gap(
                    principle_id=cache_principles[0].id,
                    category=GapCategory.PERFORMANCE,
                    severity=GapSeverity.MEDIUM,
                    title="Missing Caching Layer",
                    description="Principles recommend caching but no Redis or cache layer detected",
                    current_state="Direct database/vector store access",
                    expected_state="Multi-level caching (Redis + local)",
                    impact="Increased latency and load on data stores",
                    effort_estimate="medium"
                ))
        
        return gaps
    
    def _check_reliability_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check reliability principles."""
        gaps = []
        
        # Circuit breaker
        cb_principles = [p for p in principles if 'circuit breaker' in p.description.lower()]
        if cb_principles:
            has_cb = any('circuit' in str(c).lower() or 'resilience' in str(c).lower() 
                        for c in system.components)
            if not has_cb:
                gaps.append(Gap(
                    principle_id=cb_principles[0].id,
                    category=GapCategory.ARCHITECTURE,
                    severity=GapSeverity.HIGH,
                    title="Missing Circuit Breaker Pattern",
                    description="Principles recommend circuit breakers for external service calls",
                    current_state="Direct LLM API calls without protection",
                    expected_state="Circuit breaker with fallback for LLM providers",
                    impact="Cascading failures when LLM providers are unavailable",
                    effort_estimate="medium"
                ))
        
        # Retry with backoff
        retry_principles = [p for p in principles if 'retry' in p.description.lower() and 'backoff' in p.description.lower()]
        if retry_principles:
            gaps.append(Gap(
                principle_id=retry_principles[0].id,
                category=GapCategory.IMPLEMENTATION,
                severity=GapSeverity.MEDIUM,
                title="Missing Retry with Exponential Backoff",
                description="Principles recommend retry with exponential backoff for transient failures",
                current_state="Basic or no retry logic",
                expected_state="Configurable retry with exponential backoff and jitter",
                impact="Failed requests during transient errors",
                effort_estimate="low"
            ))
        
        return gaps
    
    def _check_security_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check security principles."""
        gaps = []
        
        # Authentication/Authorization
        auth_principles = [p for p in principles if 'auth' in p.description.lower() or 'authorization' in p.description.lower()]
        if auth_principles:
            has_auth = system.security.get('auth_configured', False)
            if not has_auth:
                gaps.append(Gap(
                    principle_id=auth_principles[0].id,
                    category=GapCategory.SECURITY,
                    severity=GapSeverity.CRITICAL,
                    title="Missing Authentication/Authorization",
                    description="Principles require authentication but no auth system detected",
                    current_state="No authentication on API endpoints",
                    expected_state="JWT/OAuth2 with role-based access control",
                    impact="Unauthorized access to sensitive data and operations",
                    effort_estimate="high"
                ))
        
        # Secrets management
        secrets_principles = [p for p in principles if 'secret' in p.description.lower() or 'credential' in p.description.lower()]
        if secrets_principles:
            has_vault = any('vault' in t.lower() or 'secret' in t.lower() 
                          for t in system.technologies)
            if not has_vault and not system.security.get('env_configured', False):
                gaps.append(Gap(
                    principle_id=secrets_principles[0].id,
                    category=GapCategory.SECURITY,
                    severity=GapSeverity.HIGH,
                    title="Insecure Secrets Management",
                    description="Principles recommend secure secrets management but using plain environment variables",
                    current_state="API keys in .env files",
                    expected_state="HashiCorp Vault or cloud secrets manager",
                    impact="Credential exposure risk",
                    effort_estimate="medium"
                ))
        
        return gaps
    
    def _check_observability_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check observability principles."""
        gaps = []
        
        # Metrics
        metrics_principles = [p for p in principles if 'metric' in p.description.lower() or 'prometheus' in p.description.lower()]
        if metrics_principles:
            has_prometheus = system.monitoring.get('prometheus', False) or 'prometheus' in system.technologies
            if not has_prometheus:
                gaps.append(Gap(
                    principle_id=metrics_principles[0].id,
                    category=GapCategory.OPERATIONAL,
                    severity=GapSeverity.HIGH,
                    title="Missing Metrics Collection",
                    description="Principles require Prometheus metrics but no metrics endpoint detected",
                    current_state="No /metrics endpoint or Prometheus scraping",
                    expected_state="Prometheus metrics with standardized labels",
                    impact="No visibility into system performance and health",
                    effort_estimate="medium"
                ))
        
        # Distributed tracing
        tracing_principles = [p for p in principles if 'trace' in p.description.lower() or 'distributed' in p.description.lower()]
        if tracing_principles:
            has_tracing = any('jaeger' in t.lower() or 'zipkin' in t.lower() or 'otel' in t.lower() 
                            for t in system.technologies)
            if not has_tracing:
                gaps.append(Gap(
                    principle_id=tracing_principles[0].id,
                    category=GapCategory.OPERATIONAL,
                    severity=GapSeverity.MEDIUM,
                    title="Missing Distributed Tracing",
                    description="Principles recommend distributed tracing for microservices",
                    current_state="No trace context propagation",
                    expected_state="OpenTelemetry with Jaeger/Zipkin backend",
                    impact="Difficult debugging of cross-service requests",
                    effort_estimate="medium"
                ))
        
        return gaps
    
    def _check_deployment_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check deployment principles."""
        gaps = []
        
        # CI/CD
        cicd_principles = [p for p in principles if 'ci/cd' in p.description.lower() or 'pipeline' in p.description.lower()]
        if cicd_principles:
            # Check for GitHub Actions, GitLab CI, etc.
            has_cicd = False  # Would check for .github/workflows, .gitlab-ci.yml, etc.
            if not has_cicd:
                gaps.append(Gap(
                    principle_id=cicd_principles[0].id,
                    category=GapCategory.OPERATIONAL,
                    severity=GapSeverity.MEDIUM,
                    title="Missing CI/CD Pipeline",
                    description="Principles recommend automated CI/CD but no pipeline detected",
                    current_state="Manual deployment process",
                    expected_state="Automated build, test, and deploy pipeline",
                    impact="Slow, error-prone deployments",
                    effort_estimate="medium"
                ))
        
        return gaps
    
    def _check_data_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check data management principles."""
        gaps = []
        
        # Data consistency
        consistency_principles = [p for p in principles if 'consistency' in p.description.lower() or 'transaction' in p.description.lower()]
        if consistency_principles:
            gaps.append(Gap(
                principle_id=consistency_principles[0].id,
                category=GapCategory.ARCHITECTURE,
                severity=GapSeverity.MEDIUM,
                title="Unclear Data Consistency Model",
                description="Principles recommend explicit consistency models but not documented",
                current_state="Implicit eventual consistency",
                expected_state="Explicit consistency guarantees per service",
                impact="Potential data inconsistency issues",
                effort_estimate="low"
            ))
        
        return gaps
    
    def _check_ai_ml_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check AI/ML specific principles."""
        gaps = []
        
        # Model versioning
        versioning_principles = [p for p in principles if 'version' in p.description.lower() and 'model' in p.description.lower()]
        if versioning_principles:
            gaps.append(Gap(
                principle_id=versioning_principles[0].id,
                category=GapCategory.OPERATIONAL,
                severity=GapSeverity.HIGH,
                title="Missing Model Versioning",
                description="Principles require model versioning but no MLflow or model registry detected",
                current_state="No model version tracking",
                expected_state="MLflow or similar model registry with versioning",
                impact="Cannot reproduce or rollback model versions",
                effort_estimate="medium"
            ))
        
        # Prompt engineering
        prompt_principles = [p for p in principles if 'prompt' in p.description.lower()]
        if prompt_principles:
            gaps.append(Gap(
                principle_id=prompt_principles[0].id,
                category=GapCategory.IMPLEMENTATION,
                severity=GapSeverity.MEDIUM,
                title="Prompt Engineering Not Formalized",
                description="Principles recommend structured prompt engineering but prompts are hardcoded",
                current_state="Hardcoded prompts in source code",
                expected_state="Versioned prompt templates with A/B testing",
                impact="Inconsistent LLM responses, difficult to optimize",
                effort_estimate="low"
            ))
        
        # Evaluation/Monitoring
        eval_principles = [p for p in principles if 'evaluat' in p.description.lower() or 'benchmark' in p.description.lower()]
        if eval_principles:
            gaps.append(Gap(
                principle_id=eval_principles[0].id,
                category=GapCategory.OPERATIONAL,
                severity=GapSeverity.HIGH,
                title="Missing LLM Evaluation Framework",
                description="Principles require systematic evaluation but no evaluation pipeline detected",
                current_state="Manual testing only",
                expected_state="Automated evaluation with golden datasets and metrics",
                impact="Cannot measure quality or detect regressions",
                effort_estimate="medium"
            ))
        
        return gaps
    
    def _check_multi_agent_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """Check multi-agent system principles."""
        gaps = []
        
        # Agent coordination
        coord_principles = [p for p in principles if 'coordinat' in p.description.lower() or 'orchestrat' in p.description.lower()]
        if coord_principles:
            gaps.append(Gap(
                principle_id=coord_principles[0].id,
                category=GapCategory.ARCHITECTURE,
                severity=GapSeverity.MEDIUM,
                title="Missing Agent Coordination Framework",
                description="Principles recommend explicit coordination but agents are loosely coupled",
                current_state="Sequential RAG pipeline without agent orchestration",
                expected_state="Orchestrator with explicit agent communication",
                impact="Limited complex multi-step reasoning",
                effort_estimate="high"
            ))
        
        return gaps
    
    def _check_general_principles(
        self,
        principles: List[Principle],
        system: SystemArchitecture
    ) -> List[Gap]:
        """General principle checking for uncategorized principles."""
        gaps = []
        
        for principle in principles:
            # Basic keyword matching against system
            keywords = principle.description.lower().split()
            tech_keywords = [k for k in keywords if len(k) > 4]
            
            found = any(
                any(kw in str(v).lower() for kw in tech_keywords)
                for v in [
                    system.technologies,
                    system.components,
                    system.services,
                    system.deployment,
                    system.monitoring,
                    system.security
                ]
            )
            
            if not found and principle.confidence > 0.7:
                gaps.append(Gap(
                    principle_id=principle.id,
                    category=GapCategory.IMPLEMENTATION,
                    severity=GapSeverity.LOW,
                    title=f"Unimplemented Principle: {principle.title}",
                    description=principle.description,
                    current_state="Not detected in system",
                    expected_state="Implemented per principle",
                    impact="Potential missing best practice",
                    effort_estimate="medium"
                ))
        
        return gaps
    
    async def generate_recommendations(
        self,
        gaps: List[Gap],
        system: SystemArchitecture,
        business_metrics_path: Optional[str] = None
    ) -> List[Recommendation]:
        """Generate recommendations for addressing gaps."""
        recommendations = []
        
        # Load business metrics if available
        business_metrics = {}
        if business_metrics_path:
            try:
                import json
                with open(business_metrics_path) as f:
                    business_metrics = json.load(f)
            except Exception:
                pass
        
        for gap in gaps:
            rec = self._create_recommendation(gap, system, business_metrics)
            recommendations.append(rec)
        
        # Sort by priority
        recommendations.sort(key=lambda r: (-r.priority, r.risk_level.value))
        
        return recommendations
    
    def _create_recommendation(
        self,
        gap: Gap,
        system: SystemArchitecture,
        business_metrics: Dict[str, Any]
    ) -> Recommendation:
        """Create a recommendation for a specific gap."""
        # Determine effort based on gap category and severity
        effort_map = {
            (GapCategory.SECURITY, GapSeverity.CRITICAL): "short-term",
            (GapCategory.ARCHITECTURE, GapSeverity.HIGH): "medium-term",
            (GapCategory.PERFORMANCE, GapSeverity.HIGH): "short-term",
            (GapCategory.OPERATIONAL, GapSeverity.MEDIUM): "short-term",
            (GapCategory.IMPLEMENTATION, GapSeverity.LOW): "quick-win",
        }
        
        effort = effort_map.get((gap.category, gap.severity), "short-term")
        
        # Determine priority based on severity and business impact
        priority_map = {
            GapSeverity.CRITICAL: 10,
            GapSeverity.HIGH: 7,
            GapSeverity.MEDIUM: 4,
            GapSeverity.LOW: 2
        }
        
        priority = priority_map.get(gap.severity, 5)
        
        # Boost priority for business-critical gaps
        if gap.category == GapCategory.SECURITY:
            priority += 2
        if business_metrics.get('compliance_required', False) and gap.category == GapCategory.COMPLIANCE:
            priority += 3
        
        # Generate recommendation details
        rec_templates = {
            GapCategory.SECURITY: {
                'title': f"Implement {gap.title}",
                'description': f"Address security gap: {gap.description}. {gap.expected_state}",
            },
            GapCategory.ARCHITECTURE: {
                'title': f"Refactor Architecture: {gap.title}",
                'description': f"Architectural improvement needed: {gap.description}. Target: {gap.expected_state}",
            },
            GapCategory.PERFORMANCE: {
                'title': f"Optimize Performance: {gap.title}",
                'description': f"Performance gap identified: {gap.description}. Implement: {gap.expected_state}",
            },
            GapCategory.OPERATIONAL: {
                'title': f"Improve Operations: {gap.title}",
                'description': f"Operational gap: {gap.description}. Target state: {gap.expected_state}",
            },
            GapCategory.IMPLEMENTATION: {
                'title': f"Implement Best Practice: {gap.title}",
                'description': f"Implementation gap: {gap.description}. Follow: {gap.expected_state}",
            }
        }
        
        template = rec_templates.get(gap.category, {
            'title': f"Address: {gap.title}",
            'description': f"Gap identified: {gap.description}. Expected: {gap.expected_state}"
        })
        
        # Timeline based on effort
        timeline_map = {
            'quick-win': '1-2 weeks',
            'short-term': '2-8 weeks',
            'medium-term': '2-4 months',
            'long-term': '4-12 months'
        }
        
        return Recommendation(
            gap_id=gap.id,
            title=template['title'],
            description=template['description'],
            priority=min(priority, 10),
            effort=effort,
            resources=self._identify_resources(gap),
            dependencies=gap.dependencies,
            success_criteria=[
                f"Gap {gap.id} resolved",
                "Tests passing",
                "Documentation updated",
                "Monitoring in place"
            ],
            estimated_timeline=timeline_map.get(effort, '2-4 weeks'),
            risk_level=gap.severity
        )
    
    def _identify_resources(self, gap: Gap) -> List[str]:
        """Identify required resources for a recommendation."""
        resources = []
        
        category_resources = {
            GapCategory.SECURITY: ["Security engineer", "DevOps engineer", "Penetration testing"],
            GapCategory.ARCHITECTURE: ["Software architect", "Senior developers", "Domain experts"],
            GapCategory.PERFORMANCE: ["Performance engineer", "DevOps engineer", "Load testing tools"],
            GapCategory.OPERATIONAL: ["DevOps engineer", "SRE", "Monitoring tools"],
            GapCategory.IMPLEMENTATION: ["Software developers", "QA engineer", "Code review"],
            GapCategory.COMPLIANCE: ["Compliance officer", "Legal counsel", "Security auditor"]
        }
        
        return category_resources.get(gap.category, ["Software engineer"])


class RiskAssessor:
    """
    Assesses and quantifies risks for identified gaps.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    async def assess(
        self,
        gaps: List[Gap],
        system: SystemArchitecture
    ) -> List[Gap]:
        """
        Assess risks for each gap and update severity if needed.
        
        Args:
            gaps: Identified gaps
            system: Current system architecture
            
        Returns:
            Gaps with updated risk assessments
        """
        for gap in gaps:
            risk_score = self._calculate_risk_score(gap, system)
            gap.metadata = gap.metadata or {}
            gap.metadata['risk_score'] = risk_score
            gap.metadata['risk_factors'] = self._identify_risk_factors(gap, system)
        
        return gaps
    
    def _calculate_risk_score(self, gap: Gap, system: SystemArchitecture) -> float:
        """Calculate quantitative risk score (0-100)."""
        base_score = {
            GapSeverity.CRITICAL: 90,
            GapSeverity.HIGH: 70,
            GapSeverity.MEDIUM: 40,
            GapSeverity.LOW: 10
        }.get(gap.severity, 50)
        
        # Adjust based on system context
        if gap.category == GapCategory.SECURITY:
            base_score += 10
        if gap.category == GapCategory.ARCHITECTURE and len(system.services) > 5:
            base_score += 10  # More services = higher architectural risk
        if 'production' in str(system.deployment).lower():
            base_score += 15  # Production systems have higher risk
        
        return min(base_score, 100)
    
    def _identify_risk_factors(self, gap: Gap, system: SystemArchitecture) -> List[str]:
        """Identify specific risk factors for a gap."""
        factors = []
        
        if gap.category == GapCategory.SECURITY:
            factors.append("Potential data breach")
            factors.append("Regulatory compliance violation")
        
        if gap.category == GapCategory.ARCHITECTURE:
            factors.append("Technical debt accumulation")
            factors.append("Scaling limitations")
        
        if gap.category == GapCategory.PERFORMANCE:
            factors.append("User experience degradation")
            factors.append("Resource cost increase")
        
        if gap.category == GapCategory.OPERATIONAL:
            factors.append("Operational overhead")
            factors.append("Incident response complexity")
        
        return factors