from pathlib import Path
from dotenv import load_dotenv

# Load .env from the Benchmarking repo root (three levels up from this submodule)
load_dotenv(Path(__file__).parent / "../../../.env")