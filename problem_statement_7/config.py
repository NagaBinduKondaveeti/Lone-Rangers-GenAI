import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR        = Path(__file__).parent
PDF_FOLDER      = str(BASE_DIR / "pdf_datasets ")   # trailing space is part of dir name
DB_PATH         = os.getenv("DB_PATH",       str(BASE_DIR / "data/fleet.db"))
CHROMA_PATH     = os.getenv("CHROMA_PATH",   str(BASE_DIR / "data/chroma"))
NVIDIA_API_KEY  = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL           = "meta/llama-3.1-70b-instruct"

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)
