"""
PDF Document Extractor and Principle Extraction
================================================

Handles extraction of text and architectural principles from PDF documents.
"""

import re
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

import pypdf
from pdfminer.high_level import extract_text as pdfminer_extract_text
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument

from .models import Document, Principle, DocumentType
from .config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Container for extracted document content."""
    text: str
    pages: List[str]
    metadata: Dict[str, Any]
    page_count: int


class PDFExtractor:
    """
    Extracts text content from PDF documents using multiple engines
    for maximum coverage and accuracy.
    """
    
    def __init__(self):
        self.settings = get_settings()
    
    def extract(self, pdf_path: Path) -> Document:
        """
        Extract content from a PDF file using multiple extraction methods.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Document with extracted content and metadata
        """
        logger.info("Extracting PDF", path=str(pdf_path))
        
        # Try primary extraction with pypdf
        content = self._extract_with_pypdf(pdf_path)
        
        # Fallback to pdfminer if pypdf fails or returns empty content
        if not content.text or len(content.text.strip()) < 100:
            logger.info("Falling back to pdfminer", path=str(pdf_path))
            content = self._extract_with_pdfminer(pdf_path)
        
        # Create document object
        document = Document(
            path=str(pdf_path),
            name=pdf_path.name,
            type=DocumentType.PDF,
            content=content.text,
            metadata=content.metadata,
            extracted_at=datetime.now(),
            size_bytes=pdf_path.stat().st_size,
            page_count=content.page_count
        )
        
        logger.info(
            "PDF extraction complete",
            name=document.name,
            pages=document.page_count,
            chars=len(document.content) if document.content else 0
        )
        
        return document
    
    def _extract_with_pypdf(self, pdf_path: Path) -> ExtractedContent:
        """Extract using pypdf library."""
        try:
            with open(pdf_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                pages = []
                full_text = []
                
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text:
                            pages.append(page_text)
                            full_text.append(f"--- Page {i+1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning("Failed to extract page", page=i+1, error=str(e))
                        pages.append("")
                
                metadata = reader.metadata or {}
                
                return ExtractedContent(
                    text="\n\n".join(full_text),
                    pages=pages,
                    metadata=dict(metadata),
                    page_count=len(reader.pages)
                )
        except Exception as e:
            logger.error("pypdf extraction failed", error=str(e))
            raise
    
    def _extract_with_pdfminer(self, pdf_path: Path) -> ExtractedContent:
        """Extract using pdfminer library."""
        try:
            text = pdfminer_extract_text(str(pdf_path))
            
            # Try to get page count
            page_count = 0
            try:
                with open(pdf_path, 'rb') as f:
                    parser = PDFParser(f)
                    doc = PDFDocument(parser)
                    page_count = sum(1 for _ in doc.get_pages())
            except Exception:
                page_count = text.count('\f') + 1  # Form feed as page separator
            
            # Split into pages (rough approximation)
            pages = text.split('\f') if '\f' in text else [text]
            
            return ExtractedContent(
                text=text,
                pages=pages,
                metadata={},
                page_count=page_count
            )
        except Exception as e:
            logger.error("pdfminer extraction failed", error=str(e))
            raise
    
    def extract_batch(self, pdf_paths: List[Path]) -> List[Document]:
        """Extract multiple PDFs in parallel."""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        documents = []
        with ThreadPoolExecutor(max_workers=self.settings.pdf_parallel_jobs) as executor:
            futures = {executor.submit(self.extract, path): path for path in pdf_paths}
            
            for future in as_completed(futures):
                try:
                    document = future.result()
                    documents.append(document)
                except Exception as e:
                    path = futures[future]
                    logger.error("Batch extraction failed", file=str(path), error=str(e))
        
        return documents


class PrincipleExtractor:
    """
    Extracts architectural principles and best practices from document text
    using pattern matching and NLP techniques.
    """
    
    # Patterns for identifying architectural principles
    PRINCIPLE_PATTERNS = [
        # Explicit principle statements
        r'(?:principle|pattern|best practice|guideline|rule|law)\s*(?:#?\d+)?\s*[:\-]\s*(.+)',
        # Architecture decision records
        r'(?:ADR|architecture decision|design decision)\s*(?:#?\d+)?\s*[:\-]\s*(.+)',
        # Anti-patterns
        r'(?:anti-pattern|avoid|don\'t|never|should not)\s+(.+)',
        # Requirements
        r'(?:must|should|required to|need to|have to)\s+(.+)',
        # Recommendations
        r'(?:recommend|suggest|advise|propose)\s+(.+)',
        # Headers that indicate principles
        r'^(?:##?\s*)?(?:principle|pattern|practice|guideline)\s+\d*[:\-]?\s*(.+)$',
    ]
    
    # Categories for classification
    CATEGORIES = {
        'architecture': [
            'microservice', 'service', 'boundary', 'coupling', 'cohesion',
            'domain', 'bounded context', 'decomposition', 'granularity'
        ],
        'scalability': [
            'scale', 'horizontal', 'vertical', 'load', 'throughput',
            'partition', 'shard', 'cache', 'queue', 'async'
        ],
        'reliability': [
            'fault', 'failure', 'resilient', 'retry', 'circuit breaker',
            'timeout', 'bulkhead', 'redundancy', 'failover', 'recovery'
        ],
        'security': [
            'authentication', 'authorization', 'encryption', 'tls', 'ssl',
            'secret', 'credential', 'vulnerability', 'compliance', 'audit'
        ],
        'observability': [
            'monitor', 'log', 'metric', 'trace', 'alert', 'dashboard',
            'observability', 'visibility', 'debug', 'audit'
        ],
        'deployment': [
            'deploy', 'ci/cd', 'pipeline', 'container', 'kubernetes',
            'infrastructure', 'cloud', 'environment', 'release'
        ],
        'data': [
            'database', 'consistency', 'transaction', 'event', 'stream',
            'cache', 'index', 'query', 'migration', 'schema'
        ],
        'ai_ml': [
            'model', 'training', 'inference', 'embedding', 'vector',
            'llm', 'foundation', 'fine-tun', 'prompt', 'rag', 'retrieval'
        ],
        'multi_agent': [
            'agent', 'coordination', 'communication', 'consensus',
            'orchestration', 'workflow', 'human-in-the-loop'
        ]
    }
    
    def __init__(self):
        self.settings = get_settings()
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.MULTILINE)
            for pattern in self.PRINCIPLE_PATTERNS
        ]
    
    def extract(
        self,
        text: str,
        document_id: str,
        document_name: str
    ) -> List[Principle]:
        """
        Extract architectural principles from document text.
        
        Args:
            text: Document text content
            document_id: Source document ID
            document_name: Source document name
            
        Returns:
            List of extracted principles
        """
        principles = []
        
        # Split text into sections for better context
        sections = self._split_into_sections(text)
        
        for section_idx, section in enumerate(sections):
            section_principles = self._extract_from_section(
                section, document_id, document_name, section_idx
            )
            principles.extend(section_principles)
        
        # Deduplicate similar principles
        principles = self._deduplicate_principles(principles)
        
        logger.info(
            "Principles extracted",
            document=document_name,
            total=len(principles)
        )
        
        return principles
    
    def _split_into_sections(self, text: str) -> List[str]:
        """Split text into logical sections."""
        # Split by page markers, headers, or large gaps
        sections = re.split(
            r'(?:--- Page \d+ ---|\n\s*\n\s*\n|^#{1,3}\s+.+$)',
            text,
            flags=re.MULTILINE
        )
        return [s.strip() for s in sections if s.strip() and len(s.strip()) > 50]
    
    def _extract_from_section(
        self,
        section: str,
        document_id: str,
        document_name: str,
        section_idx: int
    ) -> List[Principle]:
        """Extract principles from a single text section."""
        principles = []
        category = self._classify_section(section)
        
        for pattern in self.compiled_patterns:
            matches = pattern.finditer(section)
            for match in matches:
                principle_text = match.group(1) if match.groups() else match.group(0)
                principle_text = principle_text.strip()
                
                if self._is_valid_principle(principle_text):
                    principle = Principle(
                        document_id=document_id,
                        category=category,
                        title=self._generate_title(principle_text),
                        description=principle_text,
                        source_text=section[:500],  # First 500 chars as context
                        confidence=self._calculate_confidence(principle_text, category),
                        tags=self._extract_tags(principle_text)
                    )
                    principles.append(principle)
        
        return principles
    
    def _classify_section(self, text: str) -> str:
        """Classify text section into a category."""
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in self.CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores, key=scores.get)
        return 'general'
    
    def _is_valid_principle(self, text: str) -> bool:
        """Validate if extracted text is a meaningful principle."""
        if len(text) < 20 or len(text) > 1000:
            return False
        
        # Must contain actionable language
        actionable_keywords = [
            'use', 'implement', 'apply', 'follow', 'ensure', 'avoid',
            'design', 'build', 'create', 'maintain', 'monitor', 'test',
            'should', 'must', 'recommend', 'prefer', 'consider'
        ]
        
        text_lower = text.lower()
        return any(kw in text_lower for kw in actionable_keywords)
    
    def _generate_title(self, text: str) -> str:
        """Generate a concise title from principle text."""
        # Take first sentence or first 80 chars
        sentences = re.split(r'[.!?]+', text)
        if sentences:
            title = sentences[0].strip()
            if len(title) > 80:
                title = title[:77] + "..."
            return title
        return text[:80]
    
    def _calculate_confidence(self, text: str, category: str) -> float:
        """Calculate confidence score for extracted principle."""
        confidence = 0.5  # Base confidence
        
        # Boost for specific architectural terms
        arch_terms = ['pattern', 'principle', 'must', 'should', 'always', 'never']
        text_lower = text.lower()
        confidence += sum(0.05 for term in arch_terms if term in text_lower)
        
        # Boost for category match
        if category != 'general':
            confidence += 0.1
        
        # Boost for length (more detail = higher confidence)
        if len(text) > 100:
            confidence += 0.1
        if len(text) > 300:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract relevant tags from principle text."""
        tags = []
        text_lower = text.lower()
        
        tag_keywords = {
            'microservices': ['microservice', 'service mesh', 'service boundary'],
            'scalability': ['scale', 'horizontal scaling', 'load balancing'],
            'resilience': ['circuit breaker', 'retry', 'timeout', 'bulkhead'],
            'security': ['authentication', 'authorization', 'encryption', 'zero trust'],
            'observability': ['logging', 'metrics', 'tracing', 'monitoring'],
            'deployment': ['ci/cd', 'kubernetes', 'docker', 'container'],
            'data': ['database', 'event sourcing', 'cqrs', 'consistency'],
            'ai': ['llm', 'embedding', 'vector', 'rag', 'fine-tuning'],
            'multi-agent': ['agent', 'orchestration', 'coordination']
        }
        
        for tag, keywords in tag_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags
    
    def _deduplicate_principles(self, principles: List[Principle]) -> List[Principle]:
        """Remove duplicate or very similar principles."""
        unique = []
        seen_texts = set()
        
        for principle in principles:
            # Create normalized key for comparison
            key = re.sub(r'\s+', ' ', principle.description.lower())[:100]
            
            if key not in seen_texts:
                seen_texts.add(key)
                unique.append(principle)
        
        return unique


from datetime import datetime