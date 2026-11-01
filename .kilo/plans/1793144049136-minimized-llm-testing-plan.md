# Planificación Detallada del Testing de LLM para BimBam Buy AI Support Agent

## Resumen Ejecutivo

Este plan detalla una estrategia de testing minimalista y centrada para los componentes LLM del sistema BimBam Buy. Concentrándose en Google, Cohere y ONNX local como proveedores principales, el plan garantiza confiabilidad del negocio y cumplimiento regulatorio sin exceder presupuestos de API.

## Objetivos del Plan

1. **Validar confiabilidad del negocio**: Garantizar que el sistema funcione consistentemente con los tres proveedores LLM
2. **Cumplir regulaciones de LATAM**: Asegurar el procesamiento seguro de datos personales según GDPR/LGPD
3. **Optimizar costos**: Minimizar el uso de APIs pagadas mientras se garantiza calidad
4. **Mantener simplicidad**: Testing enfocado sin complejidad innecesaria

## Descripción Detallada del Alcance

### 1. Proveedores Principales de LLM

**Google GenerativeAI** (Gemini, embeddings):
- Pruebas de embeddings: embedding-001
- Pruebas de generación: Gemini 2.5 Flash
- Comportamiento determinista: Temperatura 0.0 para consistencia

**Cohere** (embed-multilingual-v2.0, generación):
- Embeddings multilingües para contenido en español
- Respuestas localizadas en LATAM
- Razonamiento de costos controlado por límite de tokens

**ONNX Local** (all-MiniLM-L6-v2):
- Sin dependencia de APIs externas para pruebas de backup
- Inferencia 100% en CPU para consistencia
- Presupuesto cero de API para prueba de falla del sistema

### 2. Alcances de Testing

**Testing de Componentes Críticos**:
- Generación de embeddings (los tres proveedores)
- Generación de respuestas LLM (los tres proveedores)
- Validación de formato de respuesta
- Manejo de temperaturas variables

**Testing de Pipeline RAG Completo**:
- Recuperación híbrida con proveedores específicos
- Reordenamiento de respuestas
- Respuestas contextualizadas multi-turno

**Testing de Cumplimiento Regulatorio**:
- Procesamiento seguro de datos personales
- Eliminación segura de datos personales
- Transparencia de uso de datos

**Testing de Optimización de Costos**:
- Monitoreo de uso de tokens por solicitud
- Detección de patrones de API no optimizados
- Pruebas de poda de contexto para minimizar uso de tokens

### 3. Casos de Uso del Negocio

**Consultas Fundamentales de BimBam Buy**:
1. "¿Cuánto tarda un reembolso?"
2. "¿Puedo devolver un producto después de 10 días?"
3. "¿Qué métodos de pago aceptan?"
4. "¿Qué cubre la garantía de los productos?"
5. "Mi pedido está demorado, ¿qué hago?"

**Flujos de Chat Multi-turno**:
- Consultas de seguimiento relacionadas con reembolsos
- Clarificaciones contextuales
- Solicitudes de seguimiento de estado

## Estratregia de Testing Detallada

### 1. Testing Unitario (12 pruebas)

**Archivos de Prueba**: `tests/test_embeddings_providers.py`, `tests/test_llm_responses.py`

**Pruebas Clave**:

```python
def test_google_embedding_dimensions():
    """Verificar que Google embeddings devuelve vectores 768-d"""

def test_cohere_embedding_multilingual():
    """Verificar soporte para consultas en español"""

def test_onnx_embedding_consistency():
    """Verificar embeddings locales sin APIs externas"""

def test_google_llm_response_format():
    """Verificar formato JSON de respuestas de Google"""

def test_cohere_response_relevance():
    """Verificar relevancia de respuestas de Cohere"""

def test_onnx_response_no_api_dependency():
    """Verificar respaldo de LLM local"""
```

### 2. Testing de Integración (15 pruebas)

**Archivos de Prueba**: `tests/test_rag_integration.py`, `tests/test_multi_turno.py`

**Pruebas Clave**:

```python
def test_hybrid_retrieval_con_cohere():
    """Validar recuperación híbrida con embeddings de Cohere"""

def test_contextualizacion_multi_turno():
    """Verificar memoria entre consultas"""

def test_respuestas_google_con_texto_latam():
    """Validar respuestas adaptadas a LATAM"""

def test_falla_de_backup_de_llm():
    """Verificar respaldo cuando Google falla"""
```

### 3. Testing de Cumplimiento Regulatorio (8 pruebas)

**Archivos de Prueba**: `tests/test_regulatory_compliance.py`

**Pruebas Clave**:

```python
def test_no_almacenamiento_datos_personales():
    """Verificar que las respuestas no contienen datos personales"""

def test_transparentidad_de_procesamiento():
    """Verificar que las fuentes de datos son conocidas"""

def test_seguridad_de_eliminacion():
    """Verificar limpieza segura de datos"""
```

### 4. Testing de Optimización de Costos (10 pruebas)

**Archivos de Prueba**: `tests/test_cost_optimization.py`

**Pruebas Clave**:

```python
def test_monitoreo_de_uso_de_tokens():
    """Validar seguimiento de tokens por solicitud"""

def test_optimizacion_de_tokens():
    """Validar poda efectiva de contexto"""

def test_patrones_de_api_baratos():
    """Validar consultas económicas en Google/ONNX"""
```

## Configuración de Testing

### Proveedores Mínimos Requeridos

```yaml
# .env.test
EMBEDDINGS_PROVIDER=local      # Para pruebas consistentes de backup
LLM_PROVIDER=local            # Como última instancia de respaldo

# Variables de Control de Costos
GOOGLE_API_KEY=${GOOGLE_API_KEY}    # Principal para pruebas
COHERE_API_KEY=${COHERE_API_KEY}    # Secundario para pruebas
MAX_TOKENS_PER_TEST=1000          # Límite de control de costos
TEMPERATURE=0.0                    # Respuestas deterministas
TOP_P=0.9                          # Control de diversidad
```

### Estructura Mínima de Testing

```bash
bimbam-buy-ai-agent/
├── tests/
│   ├── test_embeddings_providers.py
│   ├── test_llm_responses.py
│   ├── test_rag_integration.py
│   ├── test_multi_turno.py
│   ├── test_regulatory_compliance.py
│   └── test_cost_optimization.py
├── .env.test
├── requirements_test.txt
└── test_report.py
```

## Pipeline de Ejecución de Pruebas

### Comando de Testing Diaria

```bash
#!/bin/bash

# Ejecutar suite de testing con foco en proveedores críticos
pytest tests/ \
  --tb=short \
  --timeout=60 \
  --max-failures=3 \
  -v \
  --ignore=tests/test_cost_optimization.py > test_results_$(date +%Y%m%d).log

# Generar reporte con métricas
python test_report.py --generate-summary
```

### Pipeline de Testing de Proveedores

```python
def run_tests_with_provider_focus():
    """Ejecutar pruebas para los tres proveedores principales"""
    
    providers = {
        "google": "principal",
        "cohere": "secundario", 
        "onnx": "respaldo"
    }
    
    for provider in providers.keys():
        print(f"\n🔧 Ejecutando pruebas para proveedor: {provider}")
        
        # Configurar entorno
        set_provider_environment(provider)
        
        # Ejecutar pruebas críticas
        run_critical_tests(provider)
        
        # Validar cumplimiento regulatorio
        validate_regulatory_compliance()
        
        # Validar optimización de costos
        validate_cost_optimization(provider)
        
        # Reportar resultados
        generate_provider_report(provider)
```

## Líneas Base de Calidad y Alertas

### Líneas Base Mínimas

| Métrica | Línea Base | Admisible | Objetivo |
|---------|-----------|------------|---------|
| Latencia P95 | 2000ms | 5000ms | 1500ms |
| Tasa de Error | <3% | <5% | <1% |
| Precisión de Respuesta | 80% | 70% | 85% |
| Consistencia de Embedding | 0.90 | 0.85 | 0.95 |
| Cobertura de Pruebas | >70% | >60% | >80% |

### Alertas Principales

- **Latencia P95 > 3000ms**: Notificación inmediata
- **Tasa de Error > 3%**: Cancelar pruebas de proveedor
- **Precisión < 70%**: Revisar modelo del proveedor
- **Tokens > Límite Diario**: Pausar pruebas

## Protocolo de Documentación e Implementación

### Proceso de Implementación

1. **Setup Inicial**: Configurar .env.test con API keys reales
2. **Testing Unitario**: Ejecutar pruebas para embeddings locales
3. **Testing Principal**: Ejecutar pruebas con Google y Cohere API
4. **Testing de Respaldo**: Validar estrategia de respaldo con ONNX local
5. **Validación Regulatoria**: Verificar cumplimiento de latam/regulaciones
6. **Optimización de Costos**: Confirmar que no se excede el presupuesto

### Formato de Reporte

```markdown
# Informe de Calidad de LLM - [Fecha]

## Resumen por Proveedor
- **Google Gemini**: 93% precisión, 3 errores, 500ms P95
- **Cohere**: 87% precisión, 5 errores, 450ms P95
- **ONNX Local**: 92% precisión, 2 errores, 800ms P95

## Alertas de Calidad
⚠️ Latencia alta detectada en Google (P95: 2800ms)
⚠️ Tasa de error alta en Cohere (3% vs objetivo 1%)
✅ Respaldo de ONNX funcionando correctamente

## Recomendaciones
1. Optimizar consultas de Google para reducir latencia
2. Re-entrenar modelo de Cohere para mejorar precisión
3. Mantener ONNX como respaldo principal

## Validación de Cumplimiento Regulatorio
✅ Todos los datos personales eliminados
✅ Transparencia de fuentes implementada
✅ Seguridad de procesamiento validada

## Planeación de Próximas Acciones
1. Optimizar tokens de Cohere (presupuesto de $200)
2. Ejecutar pruebas de estrés para Google (memoria)
3. Documentar flujos de backup de ONNX
```

Este plan de testing minimalista y centrado garantiza que el sistema LLM de BimBam Buy mantenga altos estándares de calidad, cumpla regulaciones de LATAM y optimice el presupuesto de APIs, centrándose en los tres proveedores principales: Google, Cohere y ONNX local.