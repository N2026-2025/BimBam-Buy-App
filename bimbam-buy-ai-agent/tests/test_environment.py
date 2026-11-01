import os
import sys
from pathlib import Path

# Aseguramos que el directorio del proyecto esté en el path
sys.path.append(str(Path(__file__).parent))

def test_llm_test_env_configured():
    """Verificar que .env.test está configurado correctamente"""
    assert os.path.exists(".env.test"), ".env.test no encontrado"
    
    with open(".env.test", "r") as f:
        content = f.read()
    
    # Verificar claves requeridas
    required_keys = [
        "EMBEDDINGS_PROVIDER",
        "LLM_PROVIDER", 
        "GOOGLE_API_KEY",
        "COHERE_API_KEY"
    ]
    
    for key in required_keys:
        assert f"{key}=" in content, f"{key} no encontrado en .env.test"

if __name__ == "__main__":
    test_llm_test_env_configured()
    print("✅ .env.test configurado correctamente")