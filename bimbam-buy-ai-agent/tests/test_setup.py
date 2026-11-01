import pytest
import subprocess
import sys
from pathlib import Path

def test_database_schema_exists():
    """Verificar que los archivos SQL de init existen"""
    sql_dir = Path("sql")
    assert sql_dir.exists(), "Directorio sql no encontrado"
    
    init_sql = sql_dir / "init.sql"
    assert init_sql.exists(), "sql/init.sql no encontrado"
    
    with open(init_sql, "r") as f:
        content = f.read()
    
    # Verificar que el schema contiene tablas necesarias
    assert "CREATE TABLE interactions" in content
    assert "CREATE TABLE api_usage_logs" in content

def test_docker_compose_exists():
    """Verificar que docker-compose.yml existe y es válido"""
    compose_file = Path("docker-compose.yml")
    assert compose_file.exists(), "docker-compose.yml no encontrado"
    
    with open(compose_file, "r") as f:
        content = f.read()
    
    # Verificar que contiene servicios esenciales
    assert "services:" in content
    assert "api:" in content
    assert "redis:" in content
    assert "postgres:" in content
    assert "chromadb:" in content

if __name__ == "__main__":
    test_database_schema_exists()
    test_docker_compose_exists()
    print("✅ Schema y docker-compose verificados")