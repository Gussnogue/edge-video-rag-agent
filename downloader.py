import yt_dlp
import os
import glob
from config import DATA_DIR

def download_audio(url):
    os.makedirs(DATA_DIR, exist_ok=True)
    outtmpl = os.path.join(DATA_DIR, '%(title)s.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': outtmpl,
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                return None, "Não foi possível extrair informações do vídeo."
            title = info.get('title', 'video')
            # procura arquivo MP3
            pattern = os.path.join(DATA_DIR, f"{title}*.mp3")
            files = glob.glob(pattern)
            if files:
                latest = max(files, key=os.path.getctime)
                return latest, None
            all_mp3 = glob.glob(os.path.join(DATA_DIR, "*.mp3"))
            if all_mp3:
                latest = max(all_mp3, key=os.path.getctime)
                return latest, None
            return None, "Arquivo MP3 não encontrado após download."
    except yt_dlp.utils.DownloadError as e:
        return None, f"Erro ao baixar: {e}"
    except Exception as e:
        return None, f"Erro inesperado: {e}"
    
    
