import os
import threading
import uuid
import json
import time
from downloader import COOKIES_YOUTUBE
from flask import Flask, request, jsonify, send_file, render_template, send_from_directory
from downloader import (
    descargar_audio, descargar_video,
    obtener_metadatos_spotify,
    buscar_mejor_url,
    OUTPUT_DIR,
    cargar_historial,
    agregar_al_historial,
    _cfg
)
import yt_dlp

app = Flask(__name__)

# Diccionario para tareas en segundo plano
tasks = {}

# ------------------------------------------------------------
# 1. OBTENER INFORMACIÓN DE UNA URL (YouTube / Spotify / YT Music)
# ------------------------------------------------------------
def get_video_info(url):
    """Obtiene información de YouTube: título, canal, miniatura, duración, etc."""
    opts = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,  # Necesario para obtener thumbnails
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Si es playlist, devolvemos la lista de entradas
            if info.get('_type') == 'playlist':
                entries = []
                for e in info.get('entries', []):
                    if e:
                        entries.append({
                            'title': e.get('title', 'Sin título'),
                            'url': e.get('webpage_url') or e.get('url'),
                            'duration': e.get('duration'),
                            'thumbnail': e.get('thumbnail'),
                            'uploader': e.get('uploader', ''),
                        })
                return {
                    'type': 'playlist',
                    'title': info.get('title', 'Playlist'),
                    'entries': entries,
                    'count': len(entries)
                }
            else:
                # Video individual
                thumbnails = info.get('thumbnails', [])
                best_thumb = None
                if thumbnails:
                    # Buscar la de mayor resolución
                    best_thumb = max(thumbnails, key=lambda t: t.get('width', 0) * t.get('height', 0)).get('url')
                if not best_thumb:
                    best_thumb = info.get('thumbnail')
                return {
                    'type': 'video',
                    'title': info.get('title', 'Sin título'),
                    'uploader': info.get('uploader', ''),
                    'duration': info.get('duration'),
                    'thumbnail': best_thumb,
                    'url': url,
                    'id': info.get('id')
                }
    except Exception as e:
        raise Exception(f"Error obteniendo info: {str(e)}")

def get_spotify_info(url):
    """Obtiene info de Spotify (track o playlist) usando tu función."""
    tipo, tracks = obtener_metadatos_spotify(url)
    if not tracks:
        raise Exception("No se pudo obtener información de Spotify")
    if tipo == 'track':
        track = tracks[0]
        return {
            'type': 'spotify_track',
            'title': track['title'],
            'artist': track['artist'],
            'album': track['album'],
            'cover_url': track.get('cover_url'),
            'duration_ms': track.get('duration_ms'),
            'url': url
        }
    else:
        # playlist o album
        return {
            'type': 'spotify_playlist',
            'title': tracks[0]['album'] if tracks else 'Playlist',
            'entries': tracks,
            'count': len(tracks)
        }

@app.route('/api/info')
def api_info():
    """Endpoint para obtener información de una URL."""
    url = request.args.get('url')
    if not url:
        return jsonify({'error': 'URL requerida'}), 400

    try:
        if 'spotify.com' in url:
            data = get_spotify_info(url)
        else:
            data = get_video_info(url)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ------------------------------------------------------------
# 2. INICIAR DESCARGA (AUDIO / VIDEO)
# ------------------------------------------------------------
def run_audio_task(task_id, url, quality, audio_format, options):
    """Ejecuta descarga de audio en segundo plano."""
    try:
        # Primero, obtener metadatos de Spotify si es necesario
        spotify_meta = None
        if 'spotify.com' in url:
            tipo, tracks = obtener_metadatos_spotify(url)
            if tracks:
                spotify_meta = tracks[0]  # Si es track individual
                # Si es playlist, lo manejaremos de otra forma
                if tipo in ('album', 'playlist'):
                    # Descargar toda la playlist
                    total = len(tracks)
                    for i, track in enumerate(tracks, 1):
                        query = f"{track['title']} - {track['artist']}"
                        yt_url, fuente = buscar_mejor_url(query, track.get('duration_ms', 0))
                        if yt_url:
                            result = descargar_audio(
                                yt_url,
                                quality,
                                cookies_file=COOKIES_YOUTUBE,
                                spotify_meta=track,
                                track_num=i,
                                total_tracks=total,
                                audio_format=audio_format,
                                show_info=False,
                                silent=True
                            )
                    tasks[task_id] = {
                        'status': 'completed',
                        'message': f'Playlist descargada ({total} canciones)'
                    }
                    return

        # Si no es Spotify o es track individual
        # Si es YouTube, obtener la URL directamente
        if 'spotify.com' not in url:
            yt_url = url
            fuente = 'YouTube'
        else:
            # Buscar en YT Music / YouTube
            query = f"{spotify_meta['title']} - {spotify_meta['artist']}"
            yt_url, fuente = buscar_mejor_url(query, spotify_meta.get('duration_ms', 0))
            if not yt_url:
                tasks[task_id] = {'status': 'failed', 'error': 'No se encontró la canción en YouTube'}
                return

        result = descargar_audio(
            yt_url,
            quality,
            cookies_file=COOKIES_YOUTUBE,
            spotify_meta=spotify_meta,
            track_num=1,
            total_tracks=1,
            audio_format=audio_format,
            show_info=False,
            silent=True
        )
        if result and os.path.exists(result):
            tasks[task_id] = {
                'status': 'completed',
                'file': result,
                'filename': os.path.basename(result)
            }
        else:
            tasks[task_id] = {'status': 'failed', 'error': 'No se generó el archivo'}
    except Exception as e:
        tasks[task_id] = {'status': 'failed', 'error': str(e)}

def run_video_task(task_id, url, quality, video_format, options):
    """Ejecuta descarga de video en segundo plano."""
    try:
        result = descargar_video(
            url,
            calidad_video=quality,
            formato_video=video_format,
            cookies_file=COOKIES_YOUTUBE,
            opciones=options,
            track_num=1,
            total_tracks=1
        )
        if result and os.path.exists(result):
            tasks[task_id] = {
                'status': 'completed',
                'file': result,
                'filename': os.path.basename(result)
            }
        else:
            tasks[task_id] = {'status': 'failed', 'error': 'No se generó el archivo'}
    except Exception as e:
        tasks[task_id] = {'status': 'failed', 'error': str(e)}

@app.route('/api/download', methods=['POST'])
def api_download():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON'}), 400

    url = data.get('url')
    media_type = data.get('type', 'audio')  # 'audio' o 'video'
    quality = data.get('quality', '192')
    format_ = data.get('format', 'mp3' if media_type == 'audio' else 'mp4')
    options = data.get('options', {})

    if not url:
        return jsonify({'error': 'URL es requerida'}), 400

    # Validar formatos
    if media_type == 'audio':
        if format_ not in ['mp3', 'm4a', 'flac']:
            return jsonify({'error': 'Formato de audio no soportado'}), 400
        if quality not in ['64', '96', '128', '160', '192', '256', '320']:
            return jsonify({'error': 'Calidad no soportada'}), 400
    else:
        if format_ not in ['mp4', 'mkv', 'webm']:
            return jsonify({'error': 'Formato de video no soportado'}), 400
        if quality not in ['144', '240', '360', '480', '720', '1080', '1440', '2160', '4320']:
            return jsonify({'error': 'Calidad no soportada'}), 400

    task_id = str(uuid.uuid4())
    tasks[task_id] = {'status': 'processing'}

    if media_type == 'audio':
        thread = threading.Thread(
            target=run_audio_task,
            args=(task_id, url, quality, format_, options)
        )
    else:
        thread = threading.Thread(
            target=run_video_task,
            args=(task_id, url, quality, format_, options)
        )
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>')
def api_status(task_id):
    task = tasks.get(task_id)
    if not task:
        return jsonify({'error': 'Tarea no encontrada'}), 404
    return jsonify(task)

@app.route('/download/<filename>')
def download_file(filename):
    safe_path = os.path.join(OUTPUT_DIR, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return jsonify({'error': 'Archivo no encontrado'}), 404
    return send_file(safe_path, as_attachment=True)

# ------------------------------------------------------------
# 3. HISTORIAL
# ------------------------------------------------------------
@app.route('/api/history')
def api_history():
    historial = cargar_historial()
    return jsonify(historial)

# ------------------------------------------------------------
# 4. PÁGINA PRINCIPAL
# ------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
