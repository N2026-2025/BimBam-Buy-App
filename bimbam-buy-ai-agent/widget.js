// JavaScript que corre dentro de la página web del cliente
async function enviarPreguntaAlAgente(textoUsuario) {
    const respuesta = await fetch("http://TU_IP_DE_LA_NUBE:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            question: textoUsuario,
            session_id: "sesion_cliente_123" // Mantiene la memoria multi-turno
        })
    });
    
    const datos = await respuesta.json();
    
    // datos.answer contiene la respuesta de tu Gemini 3.1 Flash-Lite
    mostrarEnPantalla(datos.answer); 
}
