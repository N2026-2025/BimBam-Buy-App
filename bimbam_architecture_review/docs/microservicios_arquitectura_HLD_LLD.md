# BimBam Buy Sistema Distribuido con Soporte IA - Especificación de Diseño de Sistemas (HLD / LLD)

Este documento detalla la arquitectura de microservicios distribuida para la plataforma **BimBam Buy**, combinando un motor de e-commerce transaccional con un agente de soporte basado en IA (RAG).

---

## 🌐 1. High-Level Design (HLD)

El High-Level Design describe los límites de los componentes distribuidos, la estrategia de persistencia aislada y la topología de comunicación sincrónica/asincrónica a través de la red.

### 🏗️ Diagrama de Rabbit MQ Arquitectura Global (Macro)

```mermaid
flowchart TD
    Client([🧑‍💻 UI: Web / Mobile]) -->|HTTP / HTTPS| Gateway[⚡ API Gateway]
  
    subgraph Ecosistema de Microservicios
        Gateway -->|Route /auth| AuthService[🔒 Servicio de Autenticación]
        Gateway -->|Route /catalog| CatalogService[📦 Servicio de Catálogo]
        Gateway -->|Route /orders| OrderService[🛒 Servicio de Órdenes]
        Gateway -->|Route /ai-support| AIService[🤖 Servicio de Soporte IA]
    end

    subgraph Bases de Datos Desacopladas
        AuthService --> DB1[(PostgreSQL: Usuarios)]
        CatalogService --> DB2[(MongoDB: Productos)]
        OrderService --> DB3[(MySQL: Transacciones)]
        AIService --> DB4[(ChromaDB: Vector Store)]
    end

    subgraph Broker de Mensajería
        OrderService -->|Publica eventos| Rabbit[✉️ RabbitMQ]
        AIService -->|Publica: ReembolsoSolicitado| Rabbit
        Rabbit -->|Escucha e Invalida Caché| CatalogService
        Rabbit -->|Escucha y Procesa Dinero| OrderService
    end
```

### 🔄 Diagrama de Secuencia (DSD) - Flujo de Reembolso Automatizado por IA

Este diagrama detalla la interacción temporal asincrónica cuando un UI solicita un reembolso al bot de soporte inteligente:

```mermaid
sequenceDiagram
    autonumber
    actor UI
    participant Controller as Controller
    participant Gateway as API Gateway
    participant AIService as AI Support Service
    participant RabbitMQ as RabbitMQ Broker
    participant OrderService as Order Service

    Controller->>Gateway: POST /api/v1/support/ask {"question": "Reembolso orden #1234"}
    activate Gateway
    Gateway->>AIService: Redirecciona petición HTTP
    activate AIService
  
    Note over AIService: Consulta ChromaDB (RAG)<br/>Valida políticas en PDF
  
    AIService-->>Gateway: 200 OK {"response": "Tu reembolso fue aprobado y se está procesando."}
    deactivate AIService
    Gateway-->>Controller: Muestra respuesta en el Chat UI
    deactivate Gateway

    Note over AIService: Flujo Asincrónico en Segundo Plano
    activate AIService
    AIService->>RabbitMQ: Publica Evento: "ReembolsoSolicitado" {order_id: 1234}
    deactivate AIService
  
    activate RabbitMQ
    RabbitMQ->>OrderService: Despacha evento de la cola a Consumidor
    deactivate RabbitMQ
  
    activate OrderService
    Note over OrderService: Ejecuta lógica transaccional ACID<br/>Modifica estado en MySQL a 'REIMBURSED'
    OrderService-->>OrderService: Persiste cambio e impacta pasarela externa
    deactivate OrderService
```

---

## 🔎 2. Low-Level Design (LLD)

El Low-Level Design expone la distribución física exacta de archivos bajo una estrategia Monorepo y la estructura de clases/módulos para el procesamiento interno.

### 📂 Estructura General del Monorepo (5 Archivos Esenciales por Servicio)

```JavaScript
bimbam-buy-monorepo/
├── infra/
│   └── docker-compose.yml         # Orquestación de infraestructura local
├── services/
│   ├── ai-support-service/        # [Python / FastAPI]
│   │   ├── app.py                 # API Entrypoint & ruteo
│   │   ├── rag_engine.py          # Orquestador LangChain & ChromaDB
│   │   ├── embedder.py            # Tokenizador e inferencia ONNX (CPU)
│   │   ├── publisher.py           # Productor de eventos RabbitMQ (Pika)
│   │   └── Dockerfile             # Contenedor optimizado python-slim
│   │
│   ├── catalog-service/           # [Node.js / Express]
│   │   ├── server.js              # Servidor HTTP Express
│   │   ├── db.js                  # Driver de conexión a MongoDB
│   │   ├── productos.js           # Lógica de catálogo y stock
│   │   ├── consumer.js            # Consumidor de eventos (Restar Stock)
│   │   └── Dockerfile             # Contenedor Node runtime
│   │
│   ├── order-service/             # [Node.js / .NET / Python]
│   │   ├── server.js              # Servidor HTTP transaccional
│   │   ├── db.js                  # Conexión ACID a PostgreSQL/MySQL
│   │   ├── orders.js              # Lógica de estados de órdenes
│   │   ├── consumer.js            # Consumidor de eventos (Procesar Reembolso)
│   │   └── Dockerfile             # Contenedor transaccional aislado
│   │
│   └── auth-service/              # [Node.js / Express]
│       ├── server.js              # Rutas exclusivas login/registro
│       ├── db.js                  # Conexión a base de credenciales
│       ├── usuarios.js            # Validación de payload e identidades
│       ├── hashMaster.js          # Encriptación BCrypt y firma JWT
│       └── Dockerfile             # Contenedor liviano de seguridad
└── README.md
```



### 📐 Diagrama de Componentes / Clases (DCD) - `microservices`

classDiagram
    class AskRequest {
        +String prompt
        +String id_UI
        +String id_orden_referencia
    }

    class AskResponse {
        +String respuesta_ia
        +String correlation_id
        +String estado_solicitud
    }

    class SupportRouter {
        -JWTValidator auth_validator
        -SupportOrchestrator orchestrator
        +post_ask(request: AskRequest, token: String) AskResponse
    }

    class SupportOrchestrator {
        -RAGEngine rag_engine
        -RabbitMQPublisher publisher
        +procesar_consulta(id_UI: String, prompt: String, id_orden: String, correlation_id: String) AskResponse
    }

    class RAGEngine {
        -ChromaClient vector_db
        -LLMGateway gemini_api
        +buscar_politica_y_evaluar(prompt: String, id_orden: String) IAValidationResult
    }

    class IAValidationResult {
        +Boolean aplica_reembolso
        +String justificacion
        +Float confianza_score
    }

    class ChromaClient {
        -String collection_name
        -ONNXEmbedder embedder
        +obtener_contexto_faqs(texto: String, top_k: Int) List~String~
    }

    class ONNXEmbedder {
        -String model_path
        +generar_vector(input_text: String) List~Float~
    }

    class LLMGateway {
        -String api_key
        -Int max_retries
        +solicitar_completado(prompt_armado: String) String
    }

    class RabbitMQPublisher {
        -String rabbitmq_url
        -String queue_name
        +emitir_evento_reembolso(id_orden: String, id_UI: String, motivo: String, correlation_id: String) Boolean
    }

    %% Relaciones estructurales de composición e inyección
    SupportRouter --> AskRequest : Valida entrada
    SupportRouter --> AskResponse : Retorna salida
    SupportRouter o-- SupportOrchestrator : Inyecta
    SupportOrchestrator o-- RAGEngine : Inyecta
    SupportOrchestrator o-- RabbitMQPublisher : Inyecta
    RAGEngine --> IAValidationResult : Retorna resultado
    RAGEngine o-- ChromaClient : Inyecta
    RAGEngine o-- LLMGateway : Inyecta
    ChromaClient o-- ONNXEmbedder : Inyecta


### 📐 Diagrama de Componentes / Clases (DCD) - `RAG-support-service`

Zoom estructural de cómo interactúan las abstracciones internas en el microservicio de Inteligencia Artificial:

```mermaid
classDiagram
    class FastAPI_App {
        +UvicornServer server
        +route_ask(question: String)
    }

    class RagEngine {
        +ChromaClient vector_db
        +GeminiClient llm_client
        +search_semantic_context(query: String) String
        +generate_response(query: String) String
    }

    class Embedder {
        +InferenceSession onnx_session
        +Tokenizer tokenizer
        +encode(text: String) List~float~
        +encode_batch(texts: List~String~) List~List~float~~
    }

    class EventPublisher {
        +BlockingConnection connection
        +Channel channel
        +publicar_reembolso_solicitado(order_id: int) Boolean
    }

    FastAPI_App --> RagEngine : Invoca lógica RAG
    RagEngine --> Embedder : Depende para vectorizar consultas
    FastAPI_App --> EventPublisher : Gatilla eventos asincrónicos
```

---

## 🚀 Tecnologías y Justificación de Escalabilidad

1. **RabbitMQ (Mensajería Asincrónica):** Garantiza resiliencia. Si el microservicio de órdenes sufre latencia alta en su DB relacional, el sistema de soporte IA no se congela ni pierde la solicitud; el mensaje queda respaldado de forma segura en la cola.
2. **Estrategia Políglota de Persistencia:** Cada servicio escala de acuerdo a su patrón de acceso a datos (Lecturas masivas en MongoDB para Catálogo, Vectores en ChromaDB para IA, y consistencia estricta en MySQL para Dinero).
3. **Despliegue Independiente (Docker):** Permite escalabilidad horizontal selectiva. Ante un incremento masivo en consultas de IA, es posible clonar instancias de `ai-support-service` a través del Gateway sin necesidad de redimensionar o pagar infraestructura extra para el resto del sistema.


### 🤖 Microservicio de Soporte IA (`ai-support-service`)
1. **`app.py`**: Servidor FastAPI que expone los endpoints REST para el chat de asistencia de los compradores.
2. **`rag_engine.py`**: Motor LangChain que ejecuta las búsquedas semánticas sobre los manuales y políticas de BimBam Buy.
3. **`embedder.py`**: Procesador local encargado de transformar el texto en arrays numéricos utilizando un modelo ONNX por CPU.
4. **`publisher.py`**: Emisor asincrónico que inyecta el evento `ReembolsoSolicitado` en la cola de RabbitMQ cuando la IA aprueba una solicitud.
5. **`Dockerfile`**: Configuración de la imagen basada en `python:3.11-slim` optimizada para el cómputo de inferencia local.

### 📦 Microservicio de Catálogo (`catalog-service`)
1. **`server.js`**: Servidor Express que gestiona el ruteo público de los productos fantásticos del e-commerce.
2. **`db.js`**: Driver y pool de conexiones directo hacia la base de datos documental MongoDB.
3. **`productos.js`**: Controlador de negocio encargado de procesar listados, precios mutables e inventarios.
4. **`consumer.js`**: Listener asincrónico que procesa los mensajes del broker para decrementar o incrementar el stock físico remanente.
5. **`Dockerfile`**: Definición del contenedor Node.js para despliegues dinámicos bajo demanda de tráfico de navegación.

### 🛒 Microservicio de Órdenes (`order-service`)
1. **`server.js`**: Punto de entrada de la API transaccional para iniciar los flujos de checkout, carritos y reembolsos financieros.
2. **`db.js`**: Configuración de la persistencia ACID utilizando un ORM conectado a MySQL o PostgreSQL.
3. **`orders.js`**: Controlador que gestiona los estados de los pedidos (`CREADA`, `PAGADA`, `REEMBOLSADA`, `ERROR`).
4. **`consumer.js`**: Listener que procesa las aprobaciones dictaminadas por la IA para modificar los saldos contables de forma asíncrona.
5. **`Dockerfile`**: Contenedor dedicado a los procesos críticos de facturación y auditoría del dinero del negocio.

### 🔒 Microservicio de Autenticación (`auth-service`)
1. **`server.js`**: Servidor que aisla los endpoints de registro, renovación de sesiones e inicio de sesión de UIs.
2. **`db.js`**: Módulo de persistencia exclusivo para la tabla indexada de credenciales e identidades.
3. **`usuarios.js`**: Controlador encargado de coordinar flujos de perfiles, firmas y asignación de roles.
4. **`hashMaster.js`**: Utilidad de criptografía interna encargada de hashear claves con BCrypt y emitir firmas de tokens JWT.
5. **`Dockerfile`**: Imagen ligera Node.js para mitigar de forma aislada los vectores de ataque distribuidos (DDoS) al login.


### 📐 Diagrama de Clases de Diseño (DCD) - `ai-support-service`
A continuación se modelan las clases reales del componente de IA, detallando sus tipos de datos primitivos, variables críticas del e-commerce y estructuras de retorno exactas.

```mermaid
classDiagram
    class AskRequest {
        +String prompt
        +String id_UI
        +String id_orden_referencia
    }

    class AskResponse {
        +String respuesta_ia
        +String correlation_id
        +String estado_solicitud
    }

    class SupportRouter {
        -JWTValidator auth_validator
        -SupportOrchestrator orchestrator
        +post_ask(request: AskRequest, token: String) AskResponse
    }

    class SupportOrchestrator {
        -RAGEngine rag_engine
        -RabbitMQPublisher publisher
        +procesar_consulta(id_UI: String, prompt: String, id_orden: String, correlation_id: String) AskResponse
    }

    class RAGEngine {
        -ChromaClient vector_db
        -LLMGateway gemini_api
        +buscar_politica_y_evaluar(prompt: String, id_orden: String) IAValidationResult
    }

    class IAValidationResult {
        +Boolean aplica_reembolso
        +String justificacion
        +Float confianza_score
    }

    class ChromaClient {
        -String collection_name
        -ONNXEmbedder embedder
        +obtener_contexto_faqs(texto: String, top_k: Int) List~String~
    }

    class ONNXEmbedder {
        -String model_path
        +generar_vector(input_text: String) List~Float~
    }

    class LLMGateway {
        -String api_key
        -Int max_retries
        +solicitar_completado(prompt_armado: String) String
    }

    class RabbitMQPublisher {
        -String rabbitmq_url
        -String queue_name
        +emitir_evento_reembolso(id_orden: String, id_UI: String, motivo: String, correlation_id: String) Boolean
    }

    %% Relaciones estructurales de composición e inyección
    SupportRouter --> AskRequest : Valida entrada
    SupportRouter --> AskResponse : Retorna salida
    SupportRouter o-- SupportOrchestrator : Inyecta
    SupportOrchestrator o-- RAGEngine : Inyecta
    SupportOrchestrator o-- RabbitMQPublisher : Inyecta
    RAGEngine --> IAValidationResult : Retorna resultado
    RAGEngine o-- ChromaClient : Inyecta
    RAGEngine o-- LLMGateway : Inyecta
    ChromaClient o-- ONNXEmbedder : Inyecta
```

### ⏱️ Diagrama de Secuencia de Diseño (DSD) - Flujo de Reembolso Automatizado
Este diagrama de secuencia ilustra el ciclo de vida completo de una solicitud de reembolso transaccional iniciada por un usuario desde la interfaz de soporte de IA:

```mermaid
sequenceDiagram
    autonumber
    actor UI as 🧑‍💻 UI
    participant GW as ⚡ API Gateway
    participant AI as 🤖 ai-support-service
    participant DB as 📁 ChromaDB (Vector Store)
    participant Broker as ✉️ RabbitMQ
    participant Orders as 🛒 order-service
    participant Catalog as 📦 catalog-service

    UI->>GW: POST /api/v1/support/ask {id_UI, id_orden_referencia, prompt}
    Note over GW: Valida JWT & Inyecta Correlation-ID
    GW->>AI: Reenvía petición validada con HTTP Headers
    AI->>DB: obtener_contexto_faqs(prompt) para políticas de reembolso
    DB-->>AI: Retorna fragmentos de texto relevantes del PDF
    Note over AI: El motor RAG/LLM evalúa los datos reales de la compra
    AI->>Broker: emitir_evento_reembolso(id_orden, id_UI, motivo, correlation_id)
    Note over Broker: Encola mensaje en 'orders.reembolsos' de forma durable
    AI-->>UI: Retorna AskResponse {respuesta_ia, estado_solicitud: "PROCESANDO_REEMBOLSO"}

    par Procesamiento Asincrónico desacoplado
        Broker->>Orders: Despacha evento de reembolso pendiente
        Orders->>Orders: Cambia estado de transacción en DB a 'REEMBOLSADA'
        Orders-->>Broker: ACK (Mensaje procesado con éxito)
    and
        Broker->>Catalog: Despacha evento de devolución de ítems
        Catalog->>Catalog: Suma stock recuperado del producto ficticio en MongoDB
        Catalog-->>Broker: ACK (Stock actualizado con éxito)
    end
```

---


```mermaid
sequenceDiagram
    autonumber

    %% Declaracion limpia de participantes para evitar errores en GitHub
    actor Cliente as Cliente (Frontend UI)
    participant Gateway as API Gateway
    participant Controller as SupportController
    participant Repo as SupportRepository
    participant Chroma as ChromaDAOImpl
    participant Broker as RabbitMQPublisherDAOImpl

    %% Flujo de ejecucion temporal de bajo nivel (LLD)
    Cliente->>Gateway: POST /api/v1/support/ask (id_cliente, id_orden_ref, prompt)
    activate Gateway

    Note over Gateway: Inyecta X-Correlation-ID unico<br/>y valida JWT Token

    Gateway->>Controller: handle_ask_request(id_cliente, id_orden_ref, prompt, token)
    activate Controller

    Controller->>Repo: evaluate_client_policy(id_cliente, id_orden_ref, prompt, correlation_id)
    activate Repo

    Repo->>Chroma: find_semantic_match(query_vector, limit_k)
    activate Chroma
    Chroma-->>Repo: List~String~ (Contexto de politicas)
    deactivate Chroma

    Note over Repo: Construye prompt enriquecido<br/>y procesa inferencia con LLM

    %% Bloque Logico Condicional de Negocio
    alt aplica_reembolso == true
        Repo->>Broker: insert_refund_event(payload_json, correlation_id)
        activate Broker
        Note over Broker: Publica mensaje persistente<br/>en cola orders.reembolsos
        Broker-->>Repo: true (Confirmacion de encolamiento)
        deactivate Broker
        
        Repo-->>Controller: SupportSessionEntity (Estado: PROCESANDO_REEMBOLSO)
    else aplica_reembolso == false
        Repo-->>Controller: SupportSessionEntity (Estado: RESOLVIBLE_POR_CHAT)
    end
    deactivate Repo

    Controller-->>Gateway: AskResponseDTO (respuesta_ia, correlation_id, estado)
    deactivate Controller

    Gateway-->>Cliente: HTTP 200 OK (JSON estructurado)
    deactivate Gateway
```

---

## 📈 4. Análisis de Viabilidad y Criterios de Escalabilidad

* **Resiliencia ante Fallas en Cascada:** Al responderle al UI en el paso 9 del DSD con un estado intermedio diferido, el hilo HTTP se libera inmediatamente. Si el `order-service` o el clúster transaccional sufren un corte o lentitud, las colas de RabbitMQ retienen los mensajes de forma durable garantizando la consistencia eventual sin arrojar errores HTTP 500 al frontend.
* **Escalabilidad Horizontal Selectiva:** El consumo de hardware del pipeline de embeddings (`ONNXEmbedder`) se aísla por completo del backend tradicional. Docker puede instanciar múltiples replicas de `ai-support-service` tras el API Gateway bajo picos de uso sin alterar el consumo de memoria del catálogo o de los procesos de autenticación de la compañía.