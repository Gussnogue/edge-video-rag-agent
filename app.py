import streamlit as st
import os
import sqlite3
import pandas as pd
import plotly.express as px
from downloader import download_audio
from transcriber import transcribe_audio
from summarizer import summarize_text
from embedder import get_embedding
from vector_db import VectorDB
from config import DATA_DIR
import subprocess

st.set_page_config(page_title="Video RAG Agent", layout="wide")
st.title("🎥 Video RAG Agent – Busca semântica em vídeos")

@st.cache_resource
def get_vector_db():
    return VectorDB()

db = get_vector_db()

# ==================== ABAS ====================
tab1, tab2, tab3 = st.tabs(["📥 Ingestão", "🔍 Consulta", "📊 Análise da coleção"])

# ------------------------------------------------------------
# ABA 1 – INGESTÃO
# ------------------------------------------------------------
with tab1:
    st.subheader("Adicionar conteúdo à base de conhecimento")

    # --- URL única ---
    with st.expander("🔗 YouTube URL", expanded=True):
        url = st.text_input("URL do vídeo")
        if st.button("Baixar, transcrever e indexar", key="single"):
            if not url:
                st.error("Insira uma URL")
            else:
                with st.spinner("Baixando áudio..."):
                    audio_path, err = download_audio(url)
                    if err:
                        st.error(err)
                    else:
                        title = os.path.basename(audio_path).replace(".mp3", "")
                with st.spinner("Transcrevendo com Whisper..."):
                    transcript = transcribe_audio(audio_path)
                with st.spinner("Resumindo com Hermes 3..."):
                    summary = summarize_text(transcript, title)
                with st.spinner("Gerando embedding..."):
                    embedding = get_embedding(summary)
                db.add_video(url, title, summary, audio_path, embedding)
                st.success(f"Vídeo '{title}' indexado com sucesso!")

    # --- Lote de URLs ---
    with st.expander("📋 Processar múltiplos vídeos (lista de URLs)"):
        urls_text = st.text_area(
            "Cole uma lista de URLs (uma por linha):",
            height=150,
            placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=..."
        )
        if st.button("🚀 Ingerir em lote", key="batch"):
            if not urls_text.strip():
                st.error("Cole pelo menos uma URL.")
            else:
                urls = [u.strip() for u in urls_text.split("\n") if u.strip()]
                progress_bar = st.progress(0)
                status_text = st.empty()
                for i, url in enumerate(urls):
                    status_text.text(f"Processando {i+1}/{len(urls)}: {url}")
                    audio_path, err = download_audio(url)
                    if err:
                        st.error(f"Erro em {url}: {err}")
                        continue
                    title = os.path.basename(audio_path).replace(".mp3", "")
                    transcript = transcribe_audio(audio_path)
                    summary = summarize_text(transcript, title)
                    embedding = get_embedding(summary)
                    db.add_video(url, title, summary, audio_path, embedding)
                    progress_bar.progress((i + 1) / len(urls))
                status_text.text("✅ Processamento em lote concluído!")
                st.success("Todos os vídeos foram indexados com sucesso.")

    # --- Upload de arquivo local ---
    with st.expander("📁 Upload de arquivo local (vídeo/áudio)"):
        uploaded_file = st.file_uploader(
            "Carregue um arquivo de vídeo ou áudio",
            type=["mp4", "avi", "mov", "mkv", "mp3", "wav", "m4a"],
            help="Formatos suportados: MP4, AVI, MOV, MKV (vídeo); MP3, WAV, M4A (áudio)"
        )
        if uploaded_file is not None:
            temp_path = os.path.join(DATA_DIR, f"upload_{uploaded_file.name}")
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("Processando arquivo..."):
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                if ext in [".mp4", ".avi", ".mov", ".mkv"]:
                    audio_path = temp_path.replace(ext, ".mp3")
                    subprocess.run([
                        "ffmpeg", "-i", temp_path, "-q:a", "0", "-map", "a", audio_path
                    ], check=True, capture_output=True)
                    os.unlink(temp_path)
                    title = os.path.basename(audio_path).replace(".mp3", "")
                else:
                    audio_path = temp_path
                    title = os.path.basename(audio_path).replace(ext, "")
                transcript = transcribe_audio(audio_path)
                summary = summarize_text(transcript, title)
                embedding = get_embedding(summary)
                db.add_video(f"local:{uploaded_file.name}", title, summary, audio_path, embedding)
            st.success(f"Arquivo '{uploaded_file.name}' indexado com sucesso!")

# ------------------------------------------------------------
# ABA 2 – CONSULTA
# ------------------------------------------------------------
with tab2:
    st.subheader("🔍 Consulta semântica")
    query = st.text_input("Pergunte sobre os vídeos indexados")
    if query and st.button("Buscar", key="search"):
        with st.spinner("Gerando embedding da consulta..."):
            q_emb = get_embedding(query)
        results = db.search(q_emb, top_k=3)
        if not results:
            st.info("Nenhum resultado encontrado.")
        else:
            for i, r in enumerate(results):
                with st.container():
                    st.markdown(f"### {i+1}. {r['title']} (score: {r['score']:.2f})")
                    st.markdown(f"**Resumo:** {r['summary'][:300]}...")
                    st.markdown(f"🔗 [Assistir no YouTube]({r['url']})")
                    st.markdown("---")

# ------------------------------------------------------------
# ABA 3 – ANALYTICS
# ------------------------------------------------------------
with tab3:
    st.subheader("📊")

    # Carrega dados do SQLite
    conn = sqlite3.connect('data/videos.db')
    df = pd.read_sql("SELECT id, title, summary, timestamp FROM videos ORDER BY timestamp", conn)
    conn.close()

    if df.empty:
        st.info("Nenhum vídeo indexado ainda. Adicione alguns vídeos para ver análises.")
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # ========== MÉTRICAS PRONTAS ==========
        st.subheader("📊 Análise da coleção")

        # 1. Total de vídeos
        total_videos = len(df)

        # 2. Período total (primeiro e último vídeo)
        first_date = df['timestamp'].min().date()
        last_date = df['timestamp'].max().date()
        period_days = (df['timestamp'].max() - df['timestamp'].min()).days

        # 3. Média de caracteres por resumo
        avg_summary_len = round(df['summary'].str.len().mean())

        # 4. Total de caracteres somados
        total_chars = df['summary'].str.len().sum()

        # 5. Palavras únicas nos resumos (após remover stopwords)
        from sklearn.feature_extraction.text import CountVectorizer
        all_text = " ".join(df['summary'].fillna(''))
        # Stopwords básicas em português
        stopwords_pt = ['de', 'da', 'do', 'que', 'em', 'para', 'com', 'uma', 'por', 'como', 'mais', 'seu', 'sua', 'ele', 'ela', 'você', 'tem', 'são', 'foi', 'ser', 'ao', 'dos', 'das', 'na', 'no', 'os', 'as', 'a', 'e', 'o', 'um', 'uma', 'me', 'te', 'se', 'nos', 'vos', 'lhe', 'lhes']
        if all_text.strip():
            vectorizer = CountVectorizer(stop_words=stopwords_pt, lowercase=True, token_pattern=r'\b[a-zA-Záéíóúâêôãõç]+\b')
            word_counts = vectorizer.fit_transform([all_text])
            unique_words = len(vectorizer.get_feature_names_out())
        else:
            unique_words = 0

        # 6. Vídeos por mês (para ver distribuição temporal)
        df['month'] = df['timestamp'].dt.to_period('M')
        videos_per_month = df['month'].value_counts().sort_index().to_dict()
        # Pega o mês com mais vídeos
        if videos_per_month:
            top_month = max(videos_per_month, key=videos_per_month.get)
            top_month_count = videos_per_month[top_month]
        else:
            top_month = None
            top_month_count = 0

        # 7. Título mais longo (caracteres)
        longest_title = df['title'].str.len().max()

        # 8. Resumo mais longo (caracteres)
        longest_summary = df['summary'].str.len().max()

        # 9. Taxa de crescimento (últimos 7 dias vs. anteriores)
        last_7_days = df[df['timestamp'] >= (df['timestamp'].max() - pd.Timedelta(days=7))].shape[0]
        before_7_days = total_videos - last_7_days
        growth_7d = (last_7_days / before_7_days) * 100 if before_7_days > 0 else 100

        # 10. Palavra mais frequente (sem stopwords)
        if all_text.strip():
            # Usando CountVectorizer novamente para obter a palavra mais comum
            word_counts = vectorizer.fit_transform([all_text])
            words = vectorizer.get_feature_names_out()
            counts = word_counts.toarray().flatten()
            top_word_index = counts.argmax()
            top_word = words[top_word_index]
            top_word_count = counts[top_word_index]
        else:
            top_word = "N/A"
            top_word_count = 0

        # Exibir métricas em colunas (grid)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de vídeos", total_videos)
        col2.metric("Período total (dias)", period_days, help=f"{first_date} → {last_date}")
        col3.metric("Média de caracteres por resumo", avg_summary_len)

        col4, col5, col6 = st.columns(3)
        col4.metric("Total de caracteres", f"{total_chars:,}".replace(',', '.'))
        col5.metric("Palavras únicas nos resumos", unique_words)
        col6.metric("Vídeos nos últimos 7 dias", last_7_days, delta=f"{growth_7d:.0f}% vs. anterior")

        col7, col8, col9 = st.columns(3)
        col7.metric("Mês com mais vídeos", f"{top_month}" if top_month else "N/A", delta=f"{top_month_count} vídeos" if top_month else "")
        col8.metric("Título mais longo (chars)", longest_title)
        col9.metric("Resumo mais longo (chars)", longest_summary)

        col10, col11, col12 = st.columns(3)
        col10.metric("Palavra mais frequente", top_word, delta=f"{top_word_count} ocorrências")
        # Pode adicionar mais uma, como média de palavras por resumo
        avg_words = round(df['summary'].str.split().str.len().mean())
        col11.metric("Média de palavras por resumo", avg_words)

        # ========== ANÁLISE DE PALAVRAS CONFIGURÁVEL ==========
        st.subheader("🔤 Análise de palavras nos resumos")

        # Stopwords configuráveis
        default_stopwords = ['de', 'da', 'do', 'que', 'em', 'para', 'com', 'uma', 'por', 'como', 'mais', 'seu', 'sua', 'ele', 'ela', 'você', 'tem', 'são', 'foi', 'ser', 'ao', 'dos', 'das', 'na', 'no', 'os', 'as', 'a', 'e', 'o', 'um', 'uma', 'me', 'te', 'se', 'nos', 'vos', 'lhe', 'lhes', 'meu', 'minha', 'teu', 'tua', 'seu', 'sua', 'nosso', 'nossa', 'vosso', 'vossa', 'este', 'esta', 'esse', 'essa', 'aquele', 'aquela', 'isto', 'isso', 'aquilo', 'está', 'são', 'foram', 'era', 'fui', 'foi', 'vai', 'vão', 'pode', 'pode', 'poder', 'quero', 'quer', 'assim', 'como', 'mas', 'por', 'com', 'sem', 'sobre', 'após', 'antes', 'depois', 'entre', 'durante', 'até']
        with st.expander("⚙️ Configurar stopwords (palavras ignoradas)"):
            stopwords_input = st.text_area(
                "Digite stopwords separadas por vírgula (ou mantenha as padrão):",
                value=",".join(default_stopwords),
                height=100,
                help="Palavras que serão removidas da análise (ex: artigos, preposições)."
            )
            custom_stopwords = set([w.strip().lower() for w in stopwords_input.split(",") if w.strip()])

        top_n = st.slider("Número de palavras mais frequentes para exibir", min_value=5, max_value=50, value=20)

        if all_text.strip():
            # Gerar frequências
            vectorizer = CountVectorizer(stop_words=list(custom_stopwords), lowercase=True, token_pattern=r'\b[a-zA-Záéíóúâêôãõç]+\b')
            word_counts = vectorizer.fit_transform([all_text])
            words = vectorizer.get_feature_names_out()
            counts = word_counts.toarray().flatten()
            word_freq = sorted(zip(words, counts), key=lambda x: x[1], reverse=True)[:top_n]

            df_words = pd.DataFrame(word_freq, columns=['Palavra', 'Frequência'])
            fig_words = px.bar(df_words, x='Palavra', y='Frequência', title=f'Top {top_n} palavras mais frequentes',
                               labels={'Palavra': 'Palavra', 'Frequência': 'Contagem'})
            fig_words.update_layout(xaxis_tickangle=-45, hovermode='x')
            st.plotly_chart(fig_words, use_container_width=True)

            # Nuvem de palavras
            st.subheader("☁️ Nuvem de palavras")
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            wordcloud = WordCloud(
                width=800, height=400, background_color='white', colormap='viridis',
                stopwords=custom_stopwords
            ).generate(all_text)
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
        else:
            st.info("Nenhum resumo disponível para análise de palavras.")