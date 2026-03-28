from downloader import download_audio
from transcriber import transcribe_audio
from summarizer import summarize_text
from embedder import get_embedding
from vector_db import VectorDB

url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# 1. Download
audio_path, err = download_audio(url)
if err:
    print("Erro no download:", err)
    exit()
title = "Me at the zoo"

# 2. Transcrição (já temos o arquivo de texto, mas vamos usar a função para garantir)
transcript = transcribe_audio(audio_path)

# 3. Resumo (usa Hermes 3 – LM Studio precisa estar rodando)
summary = summarize_text(transcript, title)
print("Resumo gerado:\n", summary)

# 4. Embedding
embedding = get_embedding(summary)

# 5. Inserir no banco e índice
db = VectorDB()
db.add_video(url, title, summary, audio_path, embedding)
print("Vídeo inserido com sucesso!")

