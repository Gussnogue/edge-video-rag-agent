import requests
import numpy as np
from config import LM_EMBED_URL, LM_EMBED_MODEL

def get_embedding(text):
    payload = {"model": LM_EMBED_MODEL, "input": text}
    resp = requests.post(LM_EMBED_URL, json=payload)
    resp.raise_for_status()
    return np.array(resp.json()["data"][0]["embedding"], dtype=np.float32)

