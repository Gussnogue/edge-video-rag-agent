import whisper
import os
from config import DATA_DIR

def transcribe_audio(audio_path):
    """Transcreve o áudio com Whisper e salva em .txt e .json (com timestamps)."""
    model = whisper.load_model("base")  # pode ser "small", "medium", "large"
    result = model.transcribe(audio_path, word_timestamps=True)
    text = result["text"]
    # Salva texto simples
    txt_path = audio_path.replace(".mp3", ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)
    # Salva JSON com timestamps (opcional)
    import json
    json_path = audio_path.replace(".mp3", ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return text

