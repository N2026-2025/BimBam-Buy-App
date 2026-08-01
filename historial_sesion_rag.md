# Bitácora de Decisiones Arquitectónicas (ADR) - BimBam Buy AI Agent

## 1. Estructura del Grafo (LangGraph)
- **Decisión:** Se implementó un flujo de dos nodos (`retrieve` -> `generate`).
- **Justificación:** Permite separar la lógica de búsqueda (RAG) de la generación de respuesta, facilitando la escalabilidad (ej. agregar un nodo de reranking o de guardrails en el futuro).

## 2. Tono del Agente
- **Decisión:** Ajuste del prompt del sistema para un tono más casual y cercano.
- **Justificación:** Mejorar la experiencia de usuario (UX) para que el agente se sienta más como un asistente de soporte humano y menos como un bot rígido.
