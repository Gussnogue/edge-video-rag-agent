import os
from dotenv import load_dotenv

load_dotenv()

LM_URL = os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1/chat/completions")
LM_EMBED_URL = os.getenv("LM_EMBEDDINGS_URL", "http://localhost:1234/v1/embeddings")
LM_MODEL = os.getenv("LM_MODEL", "hermes-3-llama-3.2-3b")
LM_EMBED_MODEL = os.getenv("LM_EMBED_MODEL", "nomic-embed-text-v1.5")

DATA_DIR = "data"

