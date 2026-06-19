# YT2MP3 Pro Web

Descarga audio y video desde YouTube, Spotify y YouTube Music con una interfaz web moderna.

## Características

- 🔍 Obtener información de videos y playlists (título, carátula, duración, artista).
- 🎵 Descarga de audio en MP3, M4A, FLAC con calidad configurable (64-320 kbps).
- 🎬 Descarga de video en MP4, MKV, WEBM con calidad hasta 8K.
- 📋 Soporte para playlists de YouTube y Spotify.
- 🎶 Búsqueda en YouTube Music con fallback a YouTube.
- 🖼️ Incrustación de carátula y metadatos.
- 📜 Historial de descargas.
- ⚙️ Opciones extra: subtítulos, fragmentos, modo móvil, etc.

## Despliegue en Render (Gratis)

1. Sube este repositorio a GitHub.
2. Crea una cuenta en [Render.com](https://render.com).
3. Crea un nuevo Web Service y conecta tu repo.
4. Configura:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - Plan: Free
5. Haz clic en "Create" y en minutos tendrás tu app en línea.

## Uso local

```bash
pip install -r requirements.txt
python app.py
