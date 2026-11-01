# Planificación Detallada del Testing de LLM para BimBam Buy AI Support Agent

## Resumen Ejecutivo

Este plan detalla una estrategia de testing exhaustiva para los componentes del modelo de lenguaje (LLM) del sistema de soporte de IA BimBam Buy. Cubriendo desde pruebas unitarias de componentes LLM individuales hasta pruebas end-to-end completas con clientes reales, el plan garantiza confiabilidad, consistencia y rendimiento bajo diversas cargas y condiciones de error.

## Objetivos de Testing para LLMs

1. **Validar componentes individuales del LLM**: probar embeddings, invocaciones de LLM y generación de respuestas
2. **Probar el pipeline RAG completo**: recuperar documentos relevantes, reordenar, contextualizar y generar respuestas
3. **Verificar confiabilidad del negocio**: garantizar que el sistema maneje todos los documentos de BimBam Buy de manera consistente
4. **Medir y optimizar el rendimiento**: catalogar latencia, memoria y uso de CPU para cada etapa del LLM
5. **Probar con múltiples proveedores**: OpenAI, Google (Gemini), Cohere y embeddings locales ONNX

## Descripción Detallada del Alcance

### 1. Área de Alcance: Testing de Componentes Individuales del LLM

**Componentes a probar**:

- **Generación de Embeddings** (`get_embeddings()`):
  - OpenAI embeddings (text-embedding-ada-002)
  - Google GenerativeAI embeddings (embedding-001)
  - Cohere embeddings (embed-multilingual-v2.0)
  - Local ONNX embeddings (all-MiniLM-L6-v2)

- **Invocación del LLM** (`pipeline.llm`):
  - Configuración de temperatura, max_tokens y top_p para cada proveedor
  - Manejo de errores para errores de API, límites de cuota y tiempos de espera

- **Generación de Respuestas** (`RagPipeline.ask`):
  - Formato de respuesta, longitud y contexto citado
  - Manejo de documentos sin contexto relevante

**Tipos de Pruebas**:

- **Pruebas Unitarias**: Probar interfaces de embedding individuales con datos mock
- **Pruebas de Integración**: Probar invocaciones de LLM con llamadas reales a APIs (con mocks de respuesta)
- **Pruebas de Contrato**: Validar formato de respuesta JSON, tipos de datos requeridos

### 2. Área de Alcance: Testing del Pipeline RAG Completo

**Etapas del Pipeline**:

1. **Carga de Documentos**: Probar todos los formatos de PDF y datos OCR
2. **División y Chunking**: Verificar chunks consistentes, límites de tamaño y superposición
3. **Recuperación Híbrida**: Probar combinación BM25 + vectorial, RRF y selección de top_k
4. **Reordenamiento**: Validar cross-encoder y rendimiento del reordenamiento local
5. **Contextualización Multi-turno**: Probar historial de chat y persistencia de sesión
6. **Generación de Respuestas**: Probar todos los proveedores de LLM con diferentes longitudes de contexto

**Casos de Prueba Críticos**:

- **Documentos de Éxito**: Ingesta completa y recuperación del corpus completo de BimBam Buy (5 documentos)
- **Documentos Incompletos**: PDFs rotos, formatos corruptos, contenido OCR problemático
- **Búsquedas con Confianza Baja**: Consultas sin relevancia semántica en documentos
- **Búsquedas con Confianza Alta**: Consultas con coincidencia exacta de palabra clave
- **Ejemplos de Múltiples Respuestas**: Diferentes prompts generando el mismo documento relevante
- **Contención de Sesión**: Recuperación de historial multi-turno entre diferentes session_ids

### 3. Área de Alcance: Testing de Usuario en el Mundo Real

**Casos de Uso del Negocio**:

1. **Búsquedas Típicas de los Clientes**:
   - "¿Cuánto tarda un reembolso?"
   - "¿Puedo devolver un producto después de 10 días?"
   - "¿Qué métodos de pago aceptan?"
   - "¿Qué cubre la garantía de los productos?"
   - "Mi pedido está demorado, ¿qué hago?"

2. **Flujos de Chat Multi-turno**:
   - Pregunta de seguimiento: "¿Y si pagué con transferencia?"
   - Clarificación contextual: "¿Existe garantía para accesorios?"
   - Secuencia de pedido: "¿Cuál es el tiempo de envío para mi pedido?"

3. **Escenarios con Múltiples Documentos**:
   - Consultas que abarcan políticas de diferentes documentos
   - Solicitudes que requieren ensamblaje de contexto de múltiples fuentes

### 4. Área de Alcance: Testing de Confianza y Confiabilidad

**Métricas de Confiabilidad**:

- **Tiempos de Respuesta**: P90, P95, P99 de latencia para diferentes tamaños de consulta
- **Tasas de Error**: Errores 4xx, 5xx, timeouts y fallos parciales de componentes
- **Tolerancia a Fallos**: Comportamiento bajo fallos en embedding, retrieval y generación
- **Condiciones de Saturación**: Rendimiento con carga alta (100 RPS, 10 sesiones concurrentes)

**Pruebas de Confiabilidad**:

1. **Fallos Transitorios**: Simulando timeouts de API, errores de red
2. **Errores de Carga**: Exceder límites de cuota de API
3. **Intermitencia de Conexión**: Fallos temporales en ChromaDB y servicios externos
4. **Pruebas de Memoria**: Verificar escapes de memoria y fugas de memoria con lotes grandes

### 5. Área de Alcance: Testing de Múltiples Proveedores de LLM

**Configuración de Proveedores**:

Cada proveedor debe probarse con:
- Configuración por defecto del pipeline (EMBEDDINGS_PROVIDER=local)
- Proveedor seleccionado por variable de entorno
- Configuración personalizada con temperatura, max_tokens y top_p

**Casos de Prueba Específicos por Proveedor**:

- **ONNX Local**: Consistencia de rendimiento en CPU sin APIs externas
- **Google Gemini**: Verificación de contenido multilenguaje y multilingüe
- **OpenAI**: Verificación de calidad de formato de respuesta de ChatGPT
- **Cohere**: Pruebas de embedding multilingüe y rendimiento de profundidad semántica

## Estrategia de Testing Detallada

### Pruebas Unitarias (15-20 pruebas)

**Archivos de Prueba**: `tests/test_embeddings.py`, `tests/test_llm_invocations.py`, `tests/test_response_format.py`

**Pruebas Clave**:

```python
def test_openai_embedding_dimensions():
    """Verificar que OpenAI embeddings devuelve vectores de dimensión 1536"""

def test_google_embedding_consistency():
    """Misma consulta -> mismo embedding (determinismo)"""

def test_cohere_embedding_multilingual():
    """Verificar soporte para contenido en español"""

def test_onnx_embedding_no_api_dependency():
    """Verificar que ONNX funciona sin APIs externas"""

def test_llm_temperature_impact():
    """Validar que la temperatura afecta la varianza de respuestas"""

def test_response_sources_required():
    """Verificar que todas las respuestas citan al menos una fuente"""
```

### Pruebas de Integración (25-30 pruebas)

**Archivos de Prueba**: `tests/test_rag_pipeline.py`, `tests/test_hybrid_retriever.py`, `tests/test_reranker.py`

**Pruebas Clave**:

```python
def test_hybrid_retriever_rrf_fusion():
    """Validar que RRF fusiona correctamente resultados BM25 y vectoriales"""

def test_reranker_improves_rank():
    """Verificar que el reordenamiento mejora la precisión"""

def test_multi_turno_memory_persist():
    """Verificar que el historial de sesión persiste entre solicitudes"""

def test_all_documents_indexed():
    """Validar que los 5 documentos de BimBam Buy están completamente indexados"""

def test_context_cited_in_response():
    """Verificar que las citas de fuentes son exactas y completas"""
```

### Pruebas E2E (15-20 pruebas)

**Archivos de Prueba**: `tests/test_e2e_full_workflow.py`, `tests/test_e2e_voice_workflow.py`

**Pruebas Clave**:

```python
def test_full_question_answering_workflow():
    """Flujo completo: pregunta -> recuperación -> reordenamiento -> respuesta"""

def test_voice_to_answer_workflow():
    """Flujo completo: STT -> RAG -> TTS"""

def test_multi_session_isolation():
    """Verificar que diferentes session_ids mantienen historial separado"""

def test_error_handling_malformed_audio():
    """Verificar manejo graceful de entrada de voz corrupta"""
```

### Pruebas de Confiabilidad (10-15 pruebas)

**Archivos de Prueba**: `tests/test_reliability.py`

**Pruebas Clave**:

```python
def test_timeout_handling_llm_api():
    """Verificar manejo de timeouts de API de LLM"""

def test_quota_exceeded_graceful_degradation():
    """Verificar degradación elegante cuando se exceden límites de cuota"""

def test_memory_stability_large_context():
    """Verificar estabilidad de memoria con documentos grandes"""

def test_circuit_breaker_pattern_llm():
    """Verificar patrón de breaker de circuito para fallos de LLM"""
```

## Herramientas y Frameworks de Testing

### Testing Unitario
- **pytest**: Framework principal de testing
- **pytest-mock**: Para mocking dependencies
- **pytest-asyncio**: Para testing de funciones asíncronas

### Testing de Integración
- **Testcontainers**: Para servicios externos (RabbitMQ, ChromaDB, databases)
- **httpx**: Cliente HTTP asíncrono para testing de API
- **pytest-redis**: Para testing de caching/redis

### Pruebas E2E y de Consola
- **playwright**: Testing end-to-end para UI y APIs
- **docker-compose**: Para entornos de testing con servicios completos
- **locust**: Para pruebas de carga y escalabilidad

### Métricas y Observabilidad
- **pytest-performance**: Medición de rendimiento
- **pytest-timeout**: Detección de pruebas colgadas
- **pytest-mock**: Verificación de invocaciones y espías

## Configuración de Testing

### Entornos de Testing

```yaml
# docker-compose.test.yml
version: "3.9"

services:
  # ChromaDB para testing vectorial
  chromadb:
    image: chromadb/chroma:latest
    ports: ["8000:8000"]
    
  # Redis para caching y sesiones
  redis:
    image: redis:alpine
    ports: ["6379:6379"]
    
  # RabbitMQ para testing (si es necesario)
  rabbitmq:
    image: rabbitmq:3-management
    ports: ["5672:5672", "15672:15672"]
    
  # PostgreSQL para logging de testing
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: test_bimbam
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    ports: ["5432:5432"]
```

### Variables de Entorno

```bash
# Variables de Testing
EMBEDDINGS_PROVIDER=local  # Para pruebas consistentes y reproducibles
LLM_PROVIDER=local         # Usar embeddings locales sin APIs externas
TEST_ENVIRONMENT=integration  # Forzar modo de testing

# Configuración de Testing LLM
TEMPERATURE=0.0  # Para respuestas deterministas
TOP_P=0.9
MAX_TOKENS=500

# Rutas y Configuración
TEST_DATA_DIR=./test_data
GROUND_TRUTH_PATH=./evaluation/ground_truth.csv
```

## Pipeline de Ejecución de Pruebas

### Comando de Testing Diaria

```bash
#!/bin/bash

# Ejecutar suite completa de pruebas
pytest tests/ \
  --tb=short \
  --timeout=60 \
  --max-failures=5 \
  --performance-threshold=2000ms \
  -v \
  -m "not slow" > test_results_$(date +%Y%m%d_%H%M%S).log

# Generar reportes
pytest tests/ --co -q > test_summary.txt
pytest tests/ --json-report --json-report-file=report.json
```

### Pipeline de Reportes

1. **JUnit XML**: Para integración con CI/CD
2. **HTML Report**: Dashboard con Pasos de Pruebas
3. **JSON Report**: Para análisis automático
4. **Dashboard de Métricas**: Gráficos de rendimiento y cobertura

### Comando de Testing Múltiple Proveedor

```python
def run_tests_for_all_providers():
    """Ejecutar suite de pruebas completa para todos los proveedores de LLM"""
    
    providers = ["openai", "google", "cohere", "local"]
    
    for provider in providers:
        print(f"\n🚀 Ejecutando pruebas para proveedor: {provider}")
        
        # Configurar entorno para este proveedor
        os.environ["EMBEDDINGS_PROVIDER"] = provider
        os.environ["LLM_PROVIDER"] = provider
        
        # Ejecutar pruebas unitarias
        run_unit_tests()
        
        # Ejecutar pruebas de integración
        run_integration_tests()
        
        # Ejecutar casos de uso específicos del negocio
        run_business_workflow_tests()
        
        # Reportar resultados
        report_provider_results(provider)
        
        print(f"✅ Pruebas completadas para proveedor: {provider}")
```

## Métricas y Alertas de Calidad

### Líneas Base de Calidad

| Métrica | Línea Base | Admisible | Objetivo |
|---------|-----------|------------|---------|
| P95 Latencia (ms) | 2000ms | 5000ms | 1500ms |
| Tasa de Error | <2% | <5% | <1% |
| Precisión de Respuesta (LLM-as-judge) | 85% | 75% | 90% |
| Consistencia de Embedding | 0.95 | 0.90 | 0.98 |
| Cobertura de Pruebas | >80% | >70% | >90% |

### Alertas de Pruebas

- **Pruebas Colgadas**: < 30 segundos sin progreso
- **Tasa de Error de Suposición**: > 10% fallos en mocks
- **Precisión de Similaridad de Embedding**: < 0.85
- **Incidencias Críticas del Negocio**: > 1 reporte por día

## Mantenimiento del Pipeline de Pruebas

### Rotación de Datos de Pruebas

- **Rotación Semanal**: Generar nuevas muestras de ground truth
- **Rotación Mensual**: Agregar nuevos documentos de BimBam Buy (nuevos PDFs)
- **Rotación Trimestral**: Probar con documentos reales de la compañía

### Validación de Ground Truth

```python
def validate_ground_truth():
    """Validar que ground_truth.csv es consistente con PDFs reales"""
    
    # Verificar que todas las preguntas tienen documentos relevantes
    # Verificar que los chunks y fuentes son precisos
    # Verificar que los ground truth no tienen duplicados
    # Verificar que el scoring de relevancia es consistente
```

### Protocolo de Actualización de Pruebas

1. **Desarrollo**: Crear nuevas pruebas unitarias para nuevos componentes
2. **Revisión**: Revisión de código para casos de prueba edge
3. **Integración**: Agregar pruebas de integración con mocks
4. **E2E**: Implementar casos de prueba end-to-end
5. **Validación**: Ejecutar suite completa con todos los proveedores
6. **Documentación**: Documentar nuevos casos de prueba, requerimientos y causa raíz

## Protocolo de Documentación e Implementación

### Entregar Casos de Prueba

Cada nuevo caso de prueba debe incluir:

1. **Name**: Descripción clara del caso de prueba
2. **Objetivo**: Validación específica del negocio
3. **Cobertura**: Qué código o flujo es probado
4. **Input**: Datos de entrada exactos
5. **Expectativa**: Resultado y validaciones exactas
6. **Descripción del Error**: Cómo se manifestaría un fallo
7. ** Relación con el Negocio**: Impacto en confiabilidad del producto

### Autoría de Casos de Prueba

- **Ingenieros de QA**: Escribir casos de prueba de nivel bajo
- **Desarrolladores**: Revisar casos de prueba para viabilidad técnica
- **Expertos en Negocio**: Validar casos de prueba para relevancia del negocio
- **Líder Técnico**: Priorizar casos de prueba basados en riesgo de negocio

Este plan de testing integral garantiza que el sistema LLM de BimBam Buy AI Support Agent mantenga altos estándares de calidad, confiabilidad y rendimiento en todas las condiciones operativas.