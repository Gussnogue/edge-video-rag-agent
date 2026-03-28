import requests
import os
from config import LM_URL, LM_MODEL, DATA_DIR

def summarize_text(text, title):
    """Envia o texto para Hermes 3 e retorna um resumo estruturado."""
    prompt = f"""
Você é um assistente que resume vídeos. Abaixo está a transcrição completa do vídeo "{title}". Gere um resumo estruturado com:
- Título
- Pontos principais (em tópicos)
- Conclusão
- Se houver, destaque trechos importantes com os timestamps aproximados.

Transcrição:
{text}

Resumo:
"""
    payload = {
        "model": LM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 800
    }
    resp = requests.post(LM_URL, json=payload)
    resp.raise_for_status()
    summary = resp.json()["choices"][0]["message"]["content"]
    # Salvar resumo
    summary_path = os.path.join(DATA_DIR, f"{title}_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(summary)
    return summary

