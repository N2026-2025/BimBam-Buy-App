# Planificación Detallada del Testing de Arquitectura BimBam Buy

## Resumen Ejecutivo

Este plan detalla la estrategia de testing distribuido para el sistema BimBam Buy AI Support Agent, implementando pruebas a nivel de unidad, integración y E2E que cubren tanto los casos de uso normales como los escenarios críticos de tolerancia a fallos.

## Objetivo General

Validar que el caso de uso distribuido responda con resiliencia bajo estrés en tres dimensiones críticas:
1. **Bifurcaciones lógicas de negocio** (Unit Testing)
2. **Componentes físicos y conectividad de red** (Integración Testing) 
3. **Flujo end-to-end con observabilidad completa** (E2E Testing)

## Descripción Detallada de Estrategias

### A. Plan de Pruebas Unitarias de Lógica y Aislamiento (Mocking)

**Objetivo**: Validar que las bifurcaciones lógicas de la clase SupportRepository reaccionen estrictamente según los flags del negocio.

**Técnica**: Se implementarán dobles de prueba (Mocks) sobre las interfaces abstractas IChromaDAO e IRabbitMQPublisherDAO.

**Casos de prueba a ejecutar de forma automatizada**:

1. **Caso Unitario 1**: Forzar que el mock del LLM devuelva un JSON con `aplica_reembolso: true`. Verificar mediante una aserción estricta (Assert) que el método `insert_refund_event()` del publicador de RabbitMQ sea invocado exactamente una vez (`times(1)`).

2. **Caso Unitario 2**: Forzar que el LLM devuelva `aplica_reembolso: false`. Verificar que el método `insert_refund_event()` nunca llegue a ejecutarse (`never()`) y que el objeto retornado tenga el estado correspondiente de chat conversacional.

### B. Plan de Pruebas de Integración Distribuidas y Estado Efímero

**Objetivo**: Garantizar que el componente físico RabbitMQPublisherDAOImpl serialice el payload JSON con los estándares corporativos reales y que la conexión TCP de red soporte caídas intermitentes.

**Técnica**: Uso del patrón Testcontainers. El entorno de pruebas automático levantará de verdad un contenedor Docker oficial de RabbitMQ en el puerto 5672 de pruebas antes de disparar el set.

**Casos de prueba a ejecutar de forma automatizada**:

1. **Caso de Integración 1**: El componente se conecta e inyecta el mensaje. El hilo de ejecución del test lee directamente la cola mediante un cliente espejo y verifica que las propiedades internas tengan el flag de persistencia `delivery_mode == 2` y un `correlation_id` con formato UUID válido.

2. **Caso de Integración 2 (Tolerancia a fallos)**: Se apaga de forma deliberada el contenedor de RabbitMQ a mitad del test. Se ejecuta la llamada y se valida que la clase capture la excepción limpiamente sin arrojar un error de desbordamiento de memoria ni congelar el hilo de ejecución principal de la aplicación.

### C. Plan de Pruebas End-to-End (E2E) Asincrónicas y Observabilidad

**Objetivo**: Certificar la consistencia eventual total de la plataforma BimBam Buy: desde que el usuario envía el prompt hasta que impacta la base de datos transaccional de un servicio externo.

**Técnica**: Despliegue de un entorno de pruebas integrado (Staging). Se simula un request HTTP real contra el endpoint del API Gateway inyectando tokens de prueba creados por el servicio de autenticación.

**Casos de prueba a ejecutar de forma automatizados**:

1. **Caso E2E 1 (Consistencia Eventual)**: La petición ingresa al chat. Dado que el flujo del reembolso es asincrónico por colas, el script de prueba utilizará un mecanismo de espera inteligente con límite de tiempo (Polling automatizado con un Timeout de 5 segundos). El test consulta periódicamente la tabla SQL física del microservicio de órdenes independientes y da la prueba como aprobada solo cuando verifica que el registro de la orden cambió su estado a `En Proceso de Reembolso`.

2. **Caso E2E 2 (Trazabilidad Extrema)**: El script inspecciona el archivo central de logs agregados. Se valida mediante expresiones regulares que el mismo X-Correlation-ID generado en la entrada del API Gateway aparezca impreso de forma exacta en los logs de auditoría interna de ChromaDB, en el emisor de eventos del microservicio de IA y, finalmente, en las trazas del microservicio de órdenes que consumió el evento de la cola.

## Configuración Arquitectónica Requerida

Para ejecutar este plan completo, se necesita una infraestructura de testing que soporte:

- Contenedores RabbitMQ con estrategia de persistencia
- Clústeres de microservicios para pruebas distribuidas
- Base de datos transaccional para validación de cambios de estado
- Sistema de logging centralizado para trazabilidad
- API Gateway para simulación de clientes reales
- Servicios de autenticación para token de pruebas

## Métricas Clave de Validación

### Pruebas Unitarias
- Cobertura de 100% de bifurcaciones lógicas de negocio
- Verificación exacta de invocaciones de mocks (`times()`/`never()`)
- Alineación estricta con el JSON contractually acordado

### Pruebas de Integración
- Mensajes persistentes con `delivery_mode == 2`
- Formato válido de `correlation_id` (UUID v4)
- Tolerancia a fallos sin afectar el hilo principal

### Pruebas E2E
- Tiempo de respuesta inferior a 5 segundos para consistencia eventual
- Corrección del estado de órdenes (`REEMBOLSADA`/`EN_PROCESO`)
- Trazabilidad completa del `X-Correlation-ID` en todos los componentes

## Pipeline de Implementación Sugerida

```bash
# 1. Construir infraestructura de testing
./build_testing_infrastructure.sh

# 2. Ejecutar suite completa de pruebas
./run_full_testing_suite.sh

# 3. Generar reportes de resultados
./generate_test_reports.sh
```

## Checklist de Comienzo

- [ ] Configurar RabbitMQ con Testcontainers
- [ ] Implementar dobles de prueba (IChromaDAO, IRabbitMQPublisherDAO)
- [ ] Configurar entorno de staging con servicios completos
- [ ] Preparar scripts de polling y espera inteligente para pruebas E2E
- [ ] Implementar validación de correlación de logs