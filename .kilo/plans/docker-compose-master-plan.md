# Planificación de Implementación del docker-compose.yml Maestro BimBam Buy

## Resumen Ejecutivo

Implementar un master docker-compose.yml que soporte las necesidades de testing distribuido del sistema LLM BimBam Buy, cubriendo Google Gemini, Cohere y ONNX local con cumplimiento regulatorio y límites de presupuesto.

## Objetivos

1. **Crear docker-compose.yml completo** que soporte testing unitario, integración y E2E
2. **Integrar infraestructura crítica**: Redis, PostgreSQL, ChromaDB para testing
3. **Asegurar cumplimiento regulatorio**: Red aislada, cifrado, retención de datos
4. **Implementar control de costos**: Monitoreo de uso de API y límites

## Tareas de Implementación Detalladas

### 1. Estructura Principal del docker-compose.yml

**Ubicación del archivo**: `bimbam-buy-ai-agent/docker-compose.yml`

**Contenido**:
```yaml
version: "3.9"

# Infraestructura maestra para testing de LLM BimBam Buy
# Soporta Google Gemini, Cohere y ONNX local

services:
  # API principal (exactamente como en producción)
  api:
    build: .
    container_name: bimbam-buy-llm-test-api
    ports:
      - "8000:8000"
    env_file:
      - .env.test
    volumes:
      - ./data:/app/data
      - chroma_data:/app/chroma_db
    depends_on:
      - redis
    networks:
      - test_net

  # Redis para testing multi-turno y sesiones
  redis:
    image: redis:7-alpine
    container_name: bimbam-buy-llm-test-redis
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - test_net

  # PostgreSQL para logs de testing (para cumplimiento regulatorio)
  postgres:
    image: postgres:16-alpine
    container_name: bimbam-buy-llm-test-postgres
    environment:
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
      POSTGRES_DB: bimbam_test
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./sql/:/docker-entrypoint-initdb.d/
    networks:
      - test_net

  # ChromaDB para testing de vector store
  chromadb:
    image: chromadb/chroma:latest
    container_name: bimbam-buy-llm-test-chroma
    ports:
      - "8000:8000"
    volumes:
      - chroma_test_data:/chroma
    networks:
      - test_net

volumes:
  chroma_data:
  chroma_test_data:
  redis_data:
  postgres_data:

networks:
  test_net:
    driver: bridge
```

### 2. Archivo .env.test Requerido

**Ubicación**: `bimbam-buy-ai-agent/.env.test`

**Contenido**:
```bash
# Configuración de testing
EMBEDDINGS_PROVIDER=local
LLM_PROVIDER=local

# API keys reales (controlados por presupuesto)
GOOGLE_API_KEY=${GOOGLE_API_KEY}
COHERE_API_KEY=${COHERE_API_KEY}

# Límites de control de costos
MAX_TOKENS_PER_TEST=1000
TEMPERATURE=0.0
TOP_P=0.9

# Configuración regulatoria
DATA_REGION=latam
LOG_RETENTION_DAYS=30
ENCRYPT_CONNECTIONS=true
```

### 3. Archivo sql/init.sql Requerido

**Ubicación**: `bimbam-buy-ai-agent/sql/init.sql`

**Contenido**:
```sql
-- Schema de testing regulatorio
-- Todos los campos personales标记 como confidenciales

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    sources TEXT[],
    embedding VECTOR(1536),
    created_at TIMESTAMP DEFAULT NOW(),
    region VARCHAR(10) DEFAULT 'latam',
    is_personal_data BOOLEAN DEFAULT false
);

CREATE TABLE api_usage_logs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,
    tokens_used INTEGER NOT NULL,
    cost DECIMAL(10,4) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    session_id VARCHAR(255)
);
```

### 4. Directorio de Comandos para Testing

**Crear**:
```
bimbam-buy-ai-agent/
├── tests/
│   ├── test_embeddings_providers.py
│   ├── test_llm_responses.py
│   ├── test_rag_integration.py
│   ├── test_regulatory_compliance.py
│   └── test_cost_optimization.py
├── docker-compose.test.yml
├── .env.test
├── requirements_test.txt
└── test_report.py
```

### 5. Configuración de Testing Crítico

**commands.yml**:
```yaml
commands:
  up:
    command: docker compose -f docker-compose.test.yml up --build -d
    description: Construir e iniciar el entorno completo de testing

  down:
    command: docker compose -f docker-compose.test.yml down -v
    description: Detener y limpiar todo el entorno de testing

  test-ready:
    command: |
      echo "Esperando servicios..."
      sleep 10
      pytest tests/ -v --tb=short
    description: Esperar hasta que los servicios estén listos y ejecutar pruebas

  generate-report:
    command: python3 test_report.py --generate > test_report_$(date +%Y%m%d).json
    description: Generar reporte de testing con timestamp
```

## Validación del Plan

### Pasos de Verificación

1. **Estructura de Archivos**: Todos los archivos necesarios creados
2. **Variables de Entorno**: .env.test válido con todos los required keys
3. **Servicios Docker**: Todos los contenedores pueden iniciarse
4. **Pruebas Unitarias**: Las pruebas básicas pasan
5. **Cobertura Regulatoria**: Schema cumple con requisitos LATAM/GDPR

### Alerta de Calidad

- **Pruebas Pasadas**: Todas las pruebas unitarias pasan
- **Inicio Correcto de Contenedores**: Todas las dependencias se inician
- **Variables de Entorno Configuradas**: .env.test válido con API keys reales
- **Schema de Database Creado**: SQL init ejecutado correctamente

## Continuidad del Pipeline

### Después de Planificación

1. **Ejecutar `docker compose -f docker-compose.test.yml up --build`**
2. **Configurar .env.test con API keys reales**
3. **Crear directorio sql/ con init.sql**
4. **Ejecutar `make test-ready` o `pytest tests/`**
5. **Generar reportes con `make generate-report`**

### Documentación para Equipo de Implementación

- **README Testing**: Instrucciones de inicio rápido para nuevos miembros del equipo
- **Guía de Configuración de API Keys**: Lista de required keys y ubicación
- **Pipeline de Pruebas Diaria**: Script automatizado para testing continuo
- **Dashboard de Reportes**: Métricas e informes para stakeholders

## Documentación de Tareas Específicas

### Tarea 1: Crear docker-compose.yml
**Estado**: En progreso - [x] Esbozo completo creado

### Tarea 2: Configurar .env.test
**Estado**: Pendiente - [ ] Variables necesarias requeridas

### Tarea 3: Crear sql/init.sql
**Estado**: Pendiente - [ ] Schema regulatorio necesario

### Tarea 4: Configurar testing
**Estado**: Pendiente - [ ] Directorio y archivos necesarios

### Tarea 5: Implementar pipeline de ejecución
**Estado**: Pendiente - [ ] Comandos validados

Este plan proporciona una implementación lista para el master docker-compose.yml que soporta los requisitos de testing LLM de BimBam Buy, incluyendo cumplimiento regulatorio y control de costos.