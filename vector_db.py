import sqlite3
import faiss
import numpy as np
import os
import json
from config import DATA_DIR

class VectorDB:
    def __init__(self):
        self.db_path = os.path.join(DATA_DIR, "videos.db")
        self.ids_path = os.path.join(DATA_DIR, "video_ids.json")
        self.index_path = os.path.join(DATA_DIR, "faiss.index")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

        self.dim = 768
        self.index, self.video_ids = self._load_or_create_index()
        print(f"[DB] Inicializado. Vetores: {self.index.ntotal}, IDs: {len(self.video_ids)}")

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                summary TEXT,
                audio_path TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _load_or_create_index(self):
        if os.path.exists(self.index_path) and os.path.exists(self.ids_path):
            idx = faiss.read_index(self.index_path)
            with open(self.ids_path, 'r') as f:
                video_ids = json.load(f)
            print(f"[DB] Carregados índice e IDs do disco. Vetores: {idx.ntotal}")
            return idx, video_ids
        else:
            print("[DB] Criando novo índice FAISS e lista de IDs")
            return faiss.IndexFlatL2(self.dim), []

    def _save_index_and_ids(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.ids_path, 'w') as f:
            json.dump(self.video_ids, f)
        print(f"[DB] Salvos índice e IDs. Vetores: {self.index.ntotal}")

    def add_video(self, url, title, summary, audio_path, embedding):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO videos (url, title, summary, audio_path) VALUES (?, ?, ?, ?)",
            (url, title, summary, audio_path)
        )
        vid = cursor.lastrowid
        self.conn.commit()
        print(f"[DB] Inserido vídeo com ID {vid}")

        embedding = np.array(embedding, dtype=np.float32).reshape(1, -1)
        self.index.add(embedding)
        self.video_ids.append(vid)
        self._save_index_and_ids()
        print(f"[DB] Embedding adicionado. Total vetores: {self.index.ntotal}")
        return vid

    def search(self, query_embedding, top_k=5):
        query_embedding = np.array(query_embedding, dtype=np.float32).reshape(1, -1)
        distances, indices = self.index.search(query_embedding, top_k)
        print(f"[DB] FAISS retornou índices: {indices[0]}, distâncias: {distances[0]}")

        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx == -1:
                continue
            # Pega o ID diretamente da lista paralela
            vid = self.video_ids[idx]  # idx é o índice no FAISS e na lista
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, title, summary, url, audio_path FROM videos WHERE id = ?", (vid,))
            row = cursor.fetchone()
            if row:
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "summary": row[2],
                    "url": row[3],
                    "audio_path": row[4],
                    "score": dist
                })
                print(f"[DB] Encontrado no SQL: ID {row[0]}, título {row[1][:50]}")
            else:
                print(f"[DB] Nenhum registro no SQL para ID {vid}")

        # Fallback: se não encontrou nada, retorna o primeiro vídeo
        if not results:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id, title, summary, url, audio_path FROM videos LIMIT 1")
            row = cursor.fetchone()
            if row:
                print("[DB] Fallback: retornando o primeiro vídeo disponível")
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "summary": row[2],
                    "url": row[3],
                    "audio_path": row[4],
                    "score": 0.0
                })
        return results

        
    



    
