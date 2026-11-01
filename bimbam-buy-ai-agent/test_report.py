#!/usr/bin/env python3
"""
Script de reporte de testing para BimBam Buy LLM testing
Genera reportes JSON con métricas e resultados de testing
"""

import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

def generate_test_summary() -> Dict[str, Any]:
    """Generar resumen de testing de los archivos de resultados"""
    results_dir = Path("results")
    if not results_dir.exists():
        return {"error": "Directorio results no encontrado", "timestamp": datetime.now().isoformat()}
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "test_files": [],
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "coverage": 0
    }
    
    # Buscar archivos de resultados CSV
    for csv_file in results_dir.glob("*.csv"):
        test_name = csv_file.stem
        summary["test_files"].append({
            "file": test_name,
            "path": str(csv_file),
            "records": count_csv_records(csv_file)
        })
    
    return summary

def count_csv_records(csv_file: Path) -> int:
    """Contar registros en archivo CSV"""
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            return sum(1 for row in reader) - 1  # Restar header
    except Exception:
        return 0

def generate_markdown_report(summary: Dict[str, Any]) -> str:
    """Generar reporte en formato Markdown"""
    report = f"""# Informe de Testing LLM BimBam Buy

**Fecha**: {summary.get('timestamp', 'N/A')}
**Total de Pruebas**: {summary.get('total_tests', 0)}
**Pruebas Pasadas**: {summary.get('passed_tests', 0)}
**Pruebas Falladas**: {summary.get('failed_tests', 0)}
**Cobertura**: {summary.get('coverage', 0)}%

## Archivos de Testeo

"""
    
    for test_file in summary.get('test_files', []):
        report += f"- **{test_file['file']}**: {test_file['records']} registros\n"
    
    if 'error' in summary:
        report += f"\n❌ Error: {summary['error']}"
    
    return report

def generate_json_report(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Generar reporte en formato JSON"""
    return summary

def main():
    parser = argparse.ArgumentParser(description="Generar reportes de testing")
    parser.add_argument("--generate", action="store_true", help="Generar reporte")
    parser.add_argument("--format", choices=["json", "markdown"], default="json", help="Formato del reporte")
    
    args = parser.parse_args()
    
    if not args.generate:
        print("Use --generate para crear reportes")
        return
    
    # Generar resumen
    summary = generate_test_summary()
    
    # Generar reporte en formato solicitado
    if args.format == "markdown":
        report = generate_markdown_report(summary)
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report)
    else:
        report = generate_json_report(summary)
        filename = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
    
    print(f"✅ Reporte generado: {filename}")

if __name__ == "__main__":
    main()