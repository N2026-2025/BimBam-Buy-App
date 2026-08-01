import os
import shutil
import logging
from pathlib import Path
from huggingface_hub import hf_hub_download, list_repo_files

os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

ONNX_CANDIDATES = [
    "onnx/model.onnx",
    "onnx/encoder_model.onnx",
    "model.onnx",
]

# Raíz del proyecto (dos niveles arriba de rag/local_embeddings/download.py),
# para que el destino sea el mismo sin importar desde dónde se invoque el
# script (CLI directo, `python -m rag.local_embeddings.download`, Docker, etc.)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DEST = PROJECT_ROOT / "models"


def download(repo, dest=DEFAULT_DEST):
    dest = Path(dest) / repo
    dest.mkdir(parents=True, exist_ok=True)

    files = list_repo_files(repo_id=repo)
    onnx_file = next((c for c in ONNX_CANDIDATES if c in files), None)
    if not onnx_file:
        raise FileNotFoundError(f"No ONNX model found in {repo}")

    for remote, local in [
        ("tokenizer.json", "tokenizer.json"),
        (onnx_file, "model.onnx"),
    ]:
        src = hf_hub_download(repo_id=repo, filename=remote)
        dst = dest / local
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  saved {dst}")
        else:
            print(f"  exists {dst}")

    onnx_ext = onnx_file + "_data"
    if onnx_ext in files:
        src = hf_hub_download(repo_id=repo, filename=onnx_ext)
        dst = dest / "model.onnx_data"
        if not dst.exists():
            shutil.copy2(src, dst)
            print(f"  saved {dst}")
        else:
            print(f"  exists {dst}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Descarga un modelo ONNX de embeddings desde Hugging Face Hub.")
    parser.add_argument(
        "--repo",
        default=os.getenv("LOCAL_EMBEDDINGS_MODEL_REPO", "Xenova/all-MiniLM-L6-v2"),
        help="Repo de Hugging Face con el modelo en formato ONNX (default: %(default)s)",
    )
    args = parser.parse_args()
    print(f"Descargando modelo de embeddings: {args.repo}")
    download(args.repo)
    print("Listo.")