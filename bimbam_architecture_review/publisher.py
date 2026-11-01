# ai-support-service/publisher.py
import os
import json
import uuid
import pika

def publicar_reembolso_solicitado(order_id: int, motivo: str, correlation_id: str = None) -> bool:
    """
    Publica un evento asincrónico en RabbitMQ indicando que la IA 
    ha validado y aprobado la solicitud de un reembolso.
    """
    # 1. Obtener la URL de conexión desde las variables de entorno (Estrategia 12 Factor App)
    rabbitmq_url = os.environ.get("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    
    # 2. Si no se provee un Correlation ID de la petición HTTP, generamos uno nuevo para la traza
    if not correlation_id:
        correlation_id = str(uuid.uuid4())
        
    try:
        # 3. Establecer la conexión con el Message Broker
        params = pika.URLParameters(rabbitmq_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        
        # 4. Declarar la cola de forma segura (Durable garantiza que no se borre si cae el broker)
        queue_name = "orders.reembolsos"
        channel.queue_declare(queue=queue_name, durable=True)
        
        # 5. Estructurar el cuerpo del evento (Mensaje JSON estándar de la industria)
        evento_payload = {
            "event_name": "ReembolsoSolicitadoPorIA",
            "order_id": order_id,
            "motivo_aprobacion": motivo,
            "origen": "ai-support-service"
        }
        
        mensaje_body = json.dumps(evento_payload)
        
        # 6. Publicar el mensaje con propiedades de persistencia e ID de correlación
        channel.basic_publish(
            exchange="",  # Usamos el Default Exchange
            routing_key=queue_name,
            body=mensaje_body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # 2 significa persistente (el mensaje se guarda en disco)
                correlation_id=correlation_id  # Clave fundamental para observabilidad distribuida
            )
        )
        
        print(f" [🤖 IA Publisher] Evento enviado exitosamente a la cola '{queue_name}'")
        print(f"      -> Payload: {mensaje_body}")
        print(f"      -> Correlation ID: {correlation_id}")
        
        # 7. Cerrar la conexión limpiamente
        connection.close()
        return True

    except Exception as e:
        print(f" [❌ IA Publisher Error] Falló el envío del evento a RabbitMQ: {str(e)}")
        return False

# --- Ejemplo rápido de ejecución local ---
if __name__ == "__main__":
    # Seteamos variable de entorno simulada para testear en local
    os.environ["RABBITMQ_URL"] = "amqp://guest:guest@localhost:5672/"
    
    print("Probando el emisor de eventos del servicio de IA...")
    # Simulamos que el bot leyó los PDFs y aprobó devolver la plata de la orden 4567
    publicar_reembolso_solicitado(
        order_id=4567, 
        motivo="El usuario demostró con fotos que el hechizo de telepatía falló."
    )
