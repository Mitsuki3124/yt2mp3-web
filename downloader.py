# =============================================================================
#  ██╗   ██╗████████╗██████╗ ███╗   ███╗██████╗ ██████╗     ██████╗ ██████╗  ██████╗
#  ╚██╗ ██╔╝╚══██╔══╝╚════██╗████╗ ████║██╔══██╗╚════██╗    ██╔══██╗██╔══██╗██╔═══██╗
#   ╚████╔╝    ██║    █████╔╝██╔████╔██║██████╔╝ █████╔╝    ██████╔╝██████╔╝██║   ██║
#    ╚██╔╝     ██║   ██╔═══╝ ██║╚██╔╝██║██╔═══╝  ╚═══██╗    ██╔═══╝ ██╔══██╗██║   ██║
#     ██║      ██║   ███████╗██║ ╚═╝ ██║██║     ██████╔╝    ██║     ██║  ██║╚██████╔╝
#     ╚═╝      ╚═╝   ╚══════╝╚═╝     ╚═╝╚═╝     ╚═════╝     ╚═╝     ╚═╝  ╚═╝ ╚═════╝
#
#  YT2MP3 PRO v3.0 — Descargador Multimedia Avanzado para Android / Termux
#  Spotify + YouTube Music + YouTube | Video • Audio • Playlists
# =============================================================================
# ⚠️  ADVERTENCIA LEGAL:
#     Solo para uso personal y educativo. El autor no se hace responsable
#     del uso indebido de esta herramienta.
# =============================================================================
# 📦 INSTALACIÓN EN TERMUX:
#   pkg update && pkg install python ffmpeg -y
#   pip install yt-dlp requests
#   (Opcional JS runtime): pkg install nodejs
# =============================================================================
# 🍪 RUTAS DE COOKIES REQUERIDAS:
#   Spotify  → /storage/emulated/0/_Carpetas VCS/cookies.txt
#   YT Music → /storage/emulated/0/music.youtube.com_cookies.txt
#   YouTube  → /storage/emulated/0/cookies.txt
# =============================================================================
# 🚀 NOVEDADES v3.0:
#   • Metadatos y carátula desde Spotify API (sp_dc token auto)
#   • Búsqueda en YT Music → fallback automático a YouTube
#   • Display de info: Nombre / Artista/s / Carátula / [N/Total]
#   • Auto 160k para álbumes y playlists de Spotify
#   • Calidades de video: 144p → 8K / Formatos: MP4 MKV WEBM
#   • Calidades de audio: 64k → 320k / Formatos: MP3 M4A FLAC
#   • Opciones extra: subtítulos, fragmentos, VLC, chapítulos,
#     continuar descarga, límite de velocidad, modo móvil y más
# =============================================================================

import yt_dlp
import subprocess
import os
import requests
import re
import sys
import shutil
import json
import time
import http.cookiejar
from datetime import datetime

# MEJORA 1 — Importación opcional de ytmusicapi
try:
    from ytmusicapi import YTMusic
    YTMUSICAPI_DISPONIBLE = True
except ImportError:
    YTMUSICAPI_DISPONIBLE = False

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────────────────────────────────────

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
os.makedirs(OUTPUT_DIR, exist_ok=True)
HISTORIAL_FILE  = os.path.join(OUTPUT_DIR, "historial_descargas.json")
MAX_REINTENTOS  = 3
COOKIES_SPOTIFY = "/storage/emulated/0/_Carpetas VCS/cookies.txt"
COOKIES_YTMUSIC = "/storage/emulated/0/music.youtube.com_cookies.txt"

import base64
import tempfile

def get_cookies_from_env():
    """Toma la variable YOUTUBE_COOKIES_B64 y la convierte en un archivo temporal de cookies."""
    cookies_b64 = os.environ.get('YOUTUBE_COOKIES_B64')
    if not cookies_b64:
        return None
    try:
        cookies_content = base64.b64decode(cookies_b64).decode('utf-8')
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
        temp_file.write(cookies_content)
        temp_file.close()
        return temp_file.name
    except Exception:
        return None

# Ahora, donde antes usabas COOKIES_YOUTUBE, usa esta función:
COOKIES_YOUTUBE = get_cookies_from_env()  # Esto intentará usar la variable de entorno
if not COOKIES_YOUTUBE:
    # Si no hay variable, fallback a la ruta de Android
    COOKIES_YOUTUBE = "/storage/emulated/0/cookies.txt" if os.path.exists("/storage/emulated/0/cookies.txt") else None
os.makedirs(OUTPUT_DIR, exist_ok=True)

descargas_sesion = 0

# MEJORA 3 — Configuración persistente
# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG PERSISTENTE
# ─────────────────────────────────────────────────────────────────────────────

_CONFIG_DIR_PREF  = os.path.expanduser("~/.config/yt2mp3_pro")
_CONFIG_FILE_PREF = os.path.join(_CONFIG_DIR_PREF, "config.json")
_CONFIG_FILE_ALT  = os.path.join(OUTPUT_DIR, "yt2mp3_pro_config.json")

_CONFIG_DEFAULTS = {
    "default_audio_quality": "192",
    "default_audio_format":  "mp3",
    "default_video_quality": "720",
    "default_video_format":  "mp4",
}

def _config_path():
    """Devuelve la ruta del archivo de config: ~/.config/... o fallback en OUTPUT_DIR."""
    try:
        os.makedirs(_CONFIG_DIR_PREF, exist_ok=True)
        return _CONFIG_FILE_PREF
    except Exception:
        return _CONFIG_FILE_ALT

def cargar_config():
    """Carga la configuración persistente; si no existe retorna los valores por defecto."""
    ruta = _config_path()
    if os.path.exists(ruta):
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Rellenar claves faltantes con defaults
            for k, v in _CONFIG_DEFAULTS.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return dict(_CONFIG_DEFAULTS)

def guardar_config(cfg):
    """Guarda la configuración en disco."""
    ruta = _config_path()
    try:
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  No se pudo guardar la configuración: {e}")

def resetear_config():
    """Restablece la configuración a valores por defecto."""
    guardar_config(dict(_CONFIG_DEFAULTS))
    print("✅ Configuración restablecida a valores por defecto.")

# Config activa durante la sesión (se carga una vez al arrancar)
_cfg = cargar_config()

# ─────────────────────────────────────────────────────────────────────────────
#  UTILIDADES GENERALES
# ─────────────────────────────────────────────────────────────────────────────

def sanitize_filename(name):
    """Elimina caracteres ilegales en nombres de archivo."""
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def run(cmd):
    """Ejecuta un comando del sistema y retorna el proceso."""
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def verificar_ffmpeg():
    """Verifica si ffmpeg está instalado en el sistema."""
    if not shutil.which("ffmpeg"):
        print("\n❌ ERROR: ffmpeg no está instalado.")
        print("   En Termux: pkg install ffmpeg")
        return False
    return True

def rescanear_archivo(ruta):
    """Fuerza el rescaneo del archivo en la biblioteca de medios de Android."""
    try:
        subprocess.run(
            ["am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
             "-d", f"file://{ruta}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except Exception:
        pass

def _tiempo_a_segundos(t):
    """Convierte HH:MM:SS o MM:SS o segundos a entero de segundos."""
    try:
        parts = [int(x) for x in t.strip().split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        elif len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return int(parts[0])
    except Exception:
        return 0

# ─────────────────────────────────────────────────────────────────────────────
#  HISTORIAL
# ─────────────────────────────────────────────────────────────────────────────

def cargar_historial():
    """Carga el historial de descargas desde el archivo JSON."""
    if not os.path.exists(HISTORIAL_FILE):
        return []
    try:
        with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def guardar_historial(h):
    """Guarda el historial en el archivo JSON."""
    try:
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
            json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️  No se pudo guardar historial: {e}")

def agregar_al_historial(titulo, nombre_disco, ruta, estado, bitrate=""):
    """Agrega una nueva entrada al historial de descargas."""
    h = cargar_historial()
    h.append({
        "titulo_original": titulo,
        "nombre_disco":    nombre_disco,
        "fecha":           datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bitrate":         bitrate,
        "ruta":            ruta,
        "estado":          estado
    })
    guardar_historial(h)

def mostrar_historial():
    """Muestra el historial de descargas en consola."""
    h = cargar_historial()
    if not h:
        print("\n📭 El historial está vacío.")
        return
    print(f"\n📋 HISTORIAL — {len(h)} entradas\n{'─' * 55}")
    for i, e in enumerate(h, 1):
        print(f" [{i:>3}] 🎵 {e.get('titulo_original', '—')}")
        print(f"        📁 {e.get('nombre_disco', '—')}")
        print(f"        📅 {e.get('fecha', '—')}  |  📊 {e.get('bitrate', '—')}")
        print(f"        ✅ {e.get('estado', '—')}")
        print("─" * 55)

# ─────────────────────────────────────────────────────────────────────────────
#  MINIATURA / CARÁTULA (YOUTUBE)
# ─────────────────────────────────────────────────────────────────────────────

def pick_best_thumbnail(info):
    """Selecciona la miniatura de mayor resolución disponible en la info."""
    thumbs = info.get("thumbnails") or []
    best, best_area = None, 0
    for t in thumbs:
        u = t.get("url")
        w = t.get("width")  or 0
        h = t.get("height") or 0
        area = w * h
        if u and area > best_area:
            best, best_area = u, area
    if best:
        return best
    thumb = info.get("thumbnail")
    if thumb:
        return thumb.replace("hqdefault", "maxresdefault") if "hqdefault" in thumb else thumb
    return None

def download_image(urls, dest):
    """Descarga la imagen desde una lista de URLs candidatas."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Android) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36",
        "Referer":    "https://www.youtube.com/"
    }
    for u in urls:
        if not u:
            continue
        try:
            r = requests.get(u, headers=headers, timeout=15, stream=True)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(dest, "wb") as f:
                    f.write(r.content)
                return True
        except Exception:
            continue
    return False

def ensure_jpeg(src, dst):
    """Convierte cualquier imagen a JPEG usando ffmpeg si es necesario."""
    if src.lower().endswith((".jpg", ".jpeg")):
        shutil.copy(src, dst)
        return True
    p = run(["ffmpeg", "-y", "-i", src, "-q:v", "2", dst])
    return p.returncode == 0 and os.path.exists(dst)

def obtener_cover_yt(info):
    """Descarga la mejor miniatura disponible desde los datos de YouTube."""
    cover_jpg = os.path.join(OUTPUT_DIR, "temp_cover.jpg")
    tmp_raw   = os.path.join(OUTPUT_DIR, "temp_cover_raw.jpg")
    best_thumb = pick_best_thumbnail(info)
    candidates = []
    if best_thumb:
        candidates.append(best_thumb)
        if "hqdefault" in best_thumb:
            candidates.insert(0, best_thumb.replace("hqdefault", "maxresdefault"))
    vid = info.get("id")
    if vid:
        candidates += [
            f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            f"https://i.ytimg.com/vi/{vid}/sddefault.jpg",
        ]
    if download_image(candidates, tmp_raw):
        if ensure_jpeg(tmp_raw, cover_jpg):
            try:
                if os.path.exists(tmp_raw) and tmp_raw != cover_jpg:
                    os.remove(tmp_raw)
            except Exception:
                pass
            return cover_jpg
    return None

def descargar_cover_spotify(url_cover, dest_path):
    """Descarga la carátula directamente desde el CDN de Spotify."""
    if not url_cover:
        return False
    try:
        r = requests.get(
            url_cover,
            headers={"User-Agent": "Mozilla/5.0",
                     "Referer": "https://open.spotify.com/"},
            timeout=15
        )
        if r.status_code == 200 and len(r.content) > 1000:
            with open(dest_path, "wb") as f:
                f.write(r.content)
            return True
    except Exception:
        pass
    return False

# ─────────────────────────────────────────────────────────────────────────────
#  NOMBRES Y METADATA
# ─────────────────────────────────────────────────────────────────────────────

def extract_prod(text):
    """Extrae la parte PROD al final de un string de título."""
    if not text:
        return text, ""
    t = text.strip()
    m = re.search(r'(?i)(?:\bprod(?:\.|ucido)?\b[\s:xX\-]*.*)$', t)
    if m:
        prod = m.group(0).strip()
        rest = t[:m.start()].strip()
        prod_norm = prod.upper()
        prod_norm = re.sub(r'\bPROD(?:\.| BY)?\b', 'PROD', prod_norm)
        prod_norm = re.sub(r'^[\-\–\—\s:]+', '', prod_norm).strip()
        return rest, prod_norm
    return t, ""

def build_names_from_info(info):
    """
    Construye nombre de archivo en disco y título de metadata
    a partir de los datos de YouTube.
    """
    raw_title = re.sub(r'\s+', ' ', info.get("title", "Desconocido").strip())
    uploader  = info.get("uploader", "").strip()
    if " - " in raw_title:
        left, right = raw_title.split(" - ", 1)
        main_title, rest = left.strip(), right.strip()
    else:
        main_title, rest = raw_title, uploader
    if uploader and rest.lower().startswith(uploader.lower()):
        rest = rest[len(uploader):].strip(" -:;")
    rest_no_prod, prod_part = extract_prod(rest)
    parts = [main_title]
    if rest_no_prod:
        parts.append(rest_no_prod)
    if prod_part:
        parts.append(prod_part)
    filename_base    = " - ".join(parts)
    filename_on_disk = sanitize_filename(filename_base) + ".mp3"
    if prod_part and rest_no_prod:
        metadata_title = f"{main_title} - {rest_no_prod} // {prod_part}"
    elif prod_part:
        metadata_title = f"{main_title} // {prod_part}"
    else:
        metadata_title = f"{main_title} - {rest_no_prod}" if rest_no_prod else main_title
    metadata_title = re.sub(r'\s+', ' ', metadata_title).strip()
    return filename_on_disk, metadata_title, main_title, rest_no_prod, prod_part

# ─────────────────────────────────────────────────────────────────────────────
#  SPOTIFY — METADATOS VÍA WEB SCRAPING (sin API keys ni cookies)
# ─────────────────────────────────────────────────────────────────────────────

def _iso8601_a_segundos(dur_str):
    """Convierte duración ISO 8601 (PT3M45S) a segundos enteros."""
    if not dur_str:
        return 0
    try:
        m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', str(dur_str))
        if not m:
            return 0
        h  = int(m.group(1) or 0)
        mi = int(m.group(2) or 0)
        s  = int(m.group(3) or 0)
        return h * 3600 + mi * 60 + s
    except Exception:
        return 0

def _limpiar_nombre(nombre):
    """Limpia caracteres ilegales de nombres."""
    if isinstance(nombre, bytes):
        nombre = nombre.decode('utf-8', errors='replace')
    nombre = re.sub(r'[\\/*?:"<>|]', '', nombre)
    return " ".join(nombre.split())

_HEADERS_SCRAPE = {
    'User-Agent': (
        'Mozilla/5.0 (compatible; Googlebot/2.1; '
        '+http://www.google.com/bot.html)'
    ),
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept': 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
}

def _scrape_nombre_spotify(url):
    """Extrae el nombre de una URL de Spotify vía scraping HTML."""
    nombre = ''
    try:
        resp = requests.get(url, headers=_HEADERS_SCRAPE, timeout=12)
        html = resp.text

        jld_m = re.search(
            r'<script[^>]+type=["\'"]application/ld\+json["\'"][^>]*>'
            r'\s*(.*?)\s*</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        if jld_m:
            try:
                jld   = json.loads(jld_m.group(1))
                items = jld if isinstance(jld, list) else [jld]
                for item in items:
                    n = item.get('name', '')
                    if n:
                        nombre = _limpiar_nombre(n)
                        break
            except Exception:
                pass

        if not nombre:
            og_m = re.search(
                r'<meta[^>]+property=["\'"]og:title["\'"][^>]+'
                r'content=["\'"]([^"\']+)["\']', html
            )
            if not og_m:
                og_m = re.search(
                    r'<meta[^>]+content=["\'"]([^"\']+)["\'"][^>]+'
                    r'property=["\'"]og:title["\']', html
                )
            if og_m:
                raw    = og_m.group(1).strip()
                raw    = re.sub(r'\s*\|\s*Spotify\s*$', '', raw).strip()
                nombre = _limpiar_nombre(raw)

        if not nombre:
            t_m = re.search(r'<title[^>]*>(.*?)</title>', html,
                            re.IGNORECASE | re.DOTALL)
            if t_m:
                raw    = t_m.group(1).strip()
                raw    = re.sub(r'\s*\|\s*Spotify\s*$', '', raw).strip()
                nombre = _limpiar_nombre(raw)

    except Exception:
        pass

    return nombre

def _meta_track_spotify(url_track):
    """
    Extrae metadatos de un track individual de Spotify vía scraping HTML/JSON-LD.
    No requiere API key ni cookies de sesión.
    Retorna: (titulo, artista, anio, num_pista, genero, dur_seg, url_portada)
    """
    titulo = artista = anio = num_pista = genero = url_portada = ''
    dur_seg = 0
    url_norm = re.sub(r'/intl-[a-z]{2}(-[a-z]+)?/', '/', url_track.strip())
    try:
        resp = requests.get(url_norm, headers=_HEADERS_SCRAPE, timeout=15)
        html = resp.text

        jld_m = re.search(
            r'<script[^>]+type=["\'"]application/ld\+json["\'"][^>]*>'
            r'\s*(.*?)\s*</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        if jld_m:
            try:
                jld   = json.loads(jld_m.group(1))
                items = jld if isinstance(jld, list) else [jld]
                for item in items:
                    if item.get('@type') not in ('MusicRecording', 'Song'):
                        continue
                    titulo = _limpiar_nombre(item.get('name', ''))
                    art_d  = (item.get('byArtist') or item.get('creator') or {})
                    if isinstance(art_d, list) and art_d:
                        art_d = art_d[0]
                    if isinstance(art_d, dict):
                        artista = _limpiar_nombre(art_d.get('name', ''))
                    img = item.get('image', '')
                    if img and isinstance(img, str) and img.startswith('http'):
                        url_portada = img
                    fecha = item.get('datePublished', '')
                    if fecha:
                        anio = fecha[:4]
                    pos = item.get('position', '')
                    if pos:
                        num_pista = str(pos)
                    gen_raw = item.get('genre', '')
                    if isinstance(gen_raw, list) and gen_raw:
                        genero = gen_raw[0]
                    elif isinstance(gen_raw, str):
                        genero = gen_raw
                    dur_raw = item.get('duration', '')
                    if dur_raw:
                        dur_seg = _iso8601_a_segundos(dur_raw)
                    if titulo:
                        break
            except Exception:
                pass

        if not url_portada:
            og = re.search(
                r'<meta[^>]+property=["\'"]og:image["\'"][^>]+content=["\'"]([^"\']+)["\']',
                html
            )
            if not og:
                og = re.search(
                    r'<meta[^>]+content=["\'"]([^"\']+)["\'"][^>]+property=["\'"]og:image["\']',
                    html
                )
            if og and og.group(1).startswith('http'):
                url_portada = og.group(1)

        if not titulo:
            tm = re.search(r'<title[^>]*>(.*?)</title>', html,
                           re.IGNORECASE | re.DOTALL)
            if tm:
                raw = tm.group(1).strip()
                raw = re.sub(r'\s*\|\s*Spotify\s*$', '', raw).strip()
                raw = (raw.replace('&amp;', '&')
                           .replace('&#x27;', "'")
                           .replace('&quot;', '"'))
                m = re.match(
                    r'^(.+?)\s*[-–]\s*(?:song(?:\s+and\s+lyrics)?\s+by)\s+(.+)$',
                    raw, re.IGNORECASE
                )
                if m:
                    titulo  = _limpiar_nombre(m.group(1).strip())
                    artista = _limpiar_nombre(m.group(2).strip())
                else:
                    partes = re.split(r'\s+·\s+', raw)
                    if len(partes) >= 2:
                        titulo  = _limpiar_nombre(partes[0].strip())
                        artista = _limpiar_nombre(partes[-1].strip())

    except Exception:
        pass

    return titulo, artista, anio, num_pista, genero, dur_seg, url_portada

def _extraer_canciones_spotify(url_album_o_playlist):
    """
    Extrae lista de canciones de un álbum o playlist de Spotify vía scraping.
    No requiere API key ni cookies de sesión.
    Retorna: (nombre_coleccion, tipo_coleccion, [canciones])
    """
    nombre_coleccion = ''
    tipo_coleccion   = 'album' if '/album/' in url_album_o_playlist else 'playlist'
    canciones        = []

    url_norm = re.sub(r'/intl-[a-z]{2}(-[a-z]+)?/', '/', url_album_o_playlist.strip())

    try:
        resp = requests.get(url_norm, headers=_HEADERS_SCRAPE, timeout=20)
        html = resp.text

        jld_m = re.search(
            r'<script[^>]+type=["\'"]application/ld\+json["\'"][^>]*>'
            r'\s*(.*?)\s*</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        if jld_m:
            try:
                jld   = json.loads(jld_m.group(1))
                items = jld if isinstance(jld, list) else [jld]
                for item in items:
                    tipo_jld = item.get('@type', '')

                    if tipo_jld in ('MusicAlbum', 'MusicPlaylist', 'MusicRecording'):
                        if not nombre_coleccion:
                            nombre_coleccion = _limpiar_nombre(item.get('name', ''))

                    tracks_raw = item.get('track', [])
                    if isinstance(tracks_raw, dict):
                        tracks_raw = tracks_raw.get('itemListElement', [])
                    if not isinstance(tracks_raw, list):
                        tracks_raw = []

                    for tr in tracks_raw:
                        if not isinstance(tr, dict):
                            continue
                        inner = tr.get('item', None)
                        if inner is None or not isinstance(inner, dict):
                            inner = tr

                        t_nom = _limpiar_nombre(inner.get('name', ''))
                        if not t_nom:
                            continue

                        art_d = (inner.get('byArtist') or inner.get('creator') or {})
                        if isinstance(art_d, list) and art_d:
                            art_d = art_d[0]
                        t_art = _limpiar_nombre(
                            art_d.get('name', '') if isinstance(art_d, dict) else ''
                        )

                        t_dur = _iso8601_a_segundos(inner.get('duration', ''))
                        t_pos = str(inner.get('position', '') or
                                    tr.get('position', '') or
                                    len(canciones) + 1)
                        t_url = inner.get('url', '') or tr.get('url', '')

                        canciones.append({
                            'titulo':       t_nom,
                            'artista':      t_art,
                            'duracion_seg': t_dur,
                            'num_pista':    t_pos,
                            'url':          t_url,
                        })

            except Exception as ex:
                print(f"⚠️  Error parseando JSON-LD de Spotify: {str(ex)[:60]}")

        if not canciones:
            track_ids = re.findall(
                r'https://open\.spotify\.com/track/([A-Za-z0-9]+)', html
            )
            seen = set()
            for tid in track_ids:
                if tid not in seen:
                    seen.add(tid)
                    canciones.append({
                        'titulo':       '',
                        'artista':      '',
                        'duracion_seg': 0,
                        'num_pista':    str(len(seen)),
                        'url':          f"https://open.spotify.com/track/{tid}",
                    })

        if not nombre_coleccion:
            nombre_coleccion = _scrape_nombre_spotify(url_norm) or 'Colección'

    except Exception as e:
        print(f"❌ Error extrayendo canciones de Spotify: {str(e)[:70]}")

    return nombre_coleccion, tipo_coleccion, canciones

def obtener_metadatos_spotify(url, cookies_path=None):
    """
    Extrae metadatos desde Spotify vía scraping HTML/JSON-LD.

    ✅ Sin API key ni cookies de sesión requeridas.
    ✅ Funciona para tracks, álbumes y playlists.

    Retorna: (tipo_str, [lista_de_tracks])
    Cada track es un dict con:
      title, artist, album, track_number, total_tracks, cover_url, duration_ms
    """
    print("🌐 Extrayendo metadatos de Spotify (scraping, sin API key)...")

    tracks = []

    # ── Track individual ────────────────────────────────────────────────────
    if '/track/' in url:
        tipo = "track"
        print("   📥 Obteniendo metadatos del track...")
        titulo, artista, anio, num_pista, genero, dur_seg, url_portada = _meta_track_spotify(url)
        if titulo:
            tracks.append({
                "title":        titulo,
                "artist":       artista,
                "album":        artista,
                "track_number": int(num_pista) if num_pista and num_pista.isdigit() else 1,
                "total_tracks": 1,
                "cover_url":    url_portada or None,
                "duration_ms":  dur_seg * 1000,
            })
            print(f"   ✅ Track obtenido: {titulo} — {artista}")
        else:
            print("   ❌ No se pudo obtener el track")

    # ── Álbum o Playlist ─────────────────────────────────────────────────────
    elif '/album/' in url or '/playlist/' in url:
        tipo = "album" if '/album/' in url else "playlist"
        tipo_label = "álbum" if tipo == "album" else "playlist"
        print(f"   📥 Obteniendo metadatos de {tipo_label}...")

        nombre_col, tipo_col, canciones = _extraer_canciones_spotify(url)

        if not canciones:
            print(f"   ❌ No se pudieron extraer canciones")
            return tipo, []

        total = len(canciones)
        print(f"   📄 {total} canciones encontradas. Obteniendo metadatos individuales...")

        for i, cancion in enumerate(canciones, 1):
            url_c  = cancion.get('url', '')
            titulo = cancion.get('titulo', '')
            artista = cancion.get('artista', '')
            dur_seg = cancion.get('duracion_seg', 0)
            url_portada = None

            # Si la canción no tiene datos completos, hacer scraping del track
            if url_c and 'open.spotify.com/track/' in url_c and (not titulo or not artista):
                print(f"   🔍 [{i}/{total}] Scrapeando track...")
                t, a, _, _, _, d, p = _meta_track_spotify(url_c)
                if t:
                    titulo  = t
                if a:
                    artista = a
                if d:
                    dur_seg = d
                if p:
                    url_portada = p
            elif url_c and 'open.spotify.com/track/' in url_c:
                # Obtener carátula individual del track
                _, _, _, _, _, _, p = _meta_track_spotify(url_c)
                url_portada = p or None

            # Fallback: usar oembed para carátula si no tenemos
            if not url_portada and url_c:
                try:
                    url_norm_c = re.sub(r'/intl-[a-z]{2}(-[a-z]+)?/', '/', url_c)
                    oe = requests.get(
                        f"https://open.spotify.com/oembed?url={url_norm_c}",
                        headers=_HEADERS_SCRAPE, timeout=8
                    )
                    if oe.status_code == 200:
                        url_portada = oe.json().get('thumbnail_url')
                except Exception:
                    pass

            tracks.append({
                "title":        titulo or f"Track {i}",
                "artist":       artista or nombre_col,
                "album":        nombre_col,
                "track_number": i,
                "total_tracks": total,
                "cover_url":    url_portada,
                "duration_ms":  dur_seg * 1000,
            })

        print(f"   ✅ {tipo_label.capitalize()} obtenido/a: {total} pistas")

    else:
        print("⚠️  URL de Spotify no reconocida (track/album/playlist).")
        return None, []

    return tipo, tracks

# ─────────────────────────────────────────────────────────────────────────────
#  BÚSQUEDA YT MUSIC → YOUTUBE FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def score_duration(entry, duracion_ms):
    """Puntúa un resultado según qué tan cercana es su duración a la de Spotify."""
    if not duracion_ms:
        return 0
    yt_duration = entry.get("duration")
    if not yt_duration:
        return 0
    yt_ms = yt_duration * 1000
    diff  = abs(yt_ms - duracion_ms)
    if diff < 3000:    # ±3s → perfecta
        return 10
    elif diff < 7000:  # ±7s → buena
        return 5
    elif diff > 20000: # +20s → probablemente versión distinta
        return -10
    return 0

def score_result(entry, query_title, query_artist, duracion_ms=0):
    """Puntúa un resultado de búsqueda priorizando canales oficiales, coincidencias exactas y duración."""
    title   = (entry.get("title")    or "").lower()
    channel = (entry.get("uploader") or "").lower()

    score = 0

    # Coincidencia fuerte título + artista
    if query_title.lower() in title:
        score += 5
    if query_artist.lower() in title:
        score += 5

    # Prioridad canales oficiales
    if "official" in channel:
        score += 10
    if "topic" in channel:
        score += 12
    if query_artist.lower() in channel:
        score += 6

    # Penalizar versiones no deseadas (filtro fuerte)
    for bad in ["karaoke", "instrumental", "cover"]:
        if bad in title:
            score -= 8
    for bad in ["live", "remix", "en vivo", "(en vivo)"]:
        if bad in title:
            score -= 5

    # Duración Spotify vs YouTube
    score += score_duration(entry, duracion_ms)

    return score

def buscar_en_ytmusic(query, cookies_file=None, duracion_ms=0):
    """
    MEJORA 1 — Busca en YouTube Music de forma fiable.

    Estrategia A (si ytmusicapi está instalado): usa YTMusic.search() directamente.
    Estrategia B (fallback): usa ytsearch10 y da prioridad a canales "- Topic"
    que son los canales oficiales auto-generados de YouTube Music.

    Retorna la URL de YouTube del mejor resultado o None.
    """
    if " - " in query:
        title_q, artist_q = query.split(" - ", 1)
    else:
        title_q, artist_q = query, ""

    # ── Estrategia A: ytmusicapi ──────────────────────────────────────────────
    if YTMUSICAPI_DISPONIBLE:
        try:
            ytm = YTMusic()
            resultados = ytm.search(query, filter="songs", limit=5)
            if not resultados:
                resultados = ytm.search(query, limit=5)
            candidatos = []
            for r in resultados:
                vid_id = r.get("videoId")
                if not vid_id:
                    continue
                # Construir entrada simulada compatible con score_result
                entry_sim = {
                    "title":    r.get("title", ""),
                    "uploader": " ".join(
                        a.get("name", "") for a in (r.get("artists") or [])
                    ),
                    "duration": (r.get("duration_seconds") or 0),
                }
                score = score_result(entry_sim, title_q, artist_q, duracion_ms)
                candidatos.append((score, f"https://www.youtube.com/watch?v={vid_id}"))
            if candidatos:
                candidatos.sort(key=lambda x: x[0], reverse=True)
                return candidatos[0][1]
        except Exception:
            pass  # Caer en Estrategia B

    # ── Estrategia B: ytsearch con filtro Topic ───────────────────────────────
    # YouTube Music genera canales "Artista - Topic" para contenido oficial.
    # Buscamos con ytsearch y priorizamos esos canales.
    opts = {
        "skip_download": True,
        "quiet":         True,
        "no_warnings":   True,
        "extract_flat":  True,
    }
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch10:{query}", download=False)
            if not res:
                return None
            entries = [e for e in (res.get("entries") or []) if e]
            if not entries:
                return None

            # Dar bonus extra a canales "- Topic" (YouTube Music oficial)
            def score_ytmusic(e):
                base = score_result(e, title_q, artist_q, duracion_ms)
                canal = (e.get("uploader") or e.get("channel") or "").lower()
                if canal.endswith("- topic") or canal.endswith("topic"):
                    base += 15  # bonus fuerte para canales Topic
                return base

            best = max(entries, key=score_ytmusic)
            # Solo devolver si tiene un score mínimo razonable (Topic o match)
            if score_ytmusic(best) > 0:
                return best.get("webpage_url") or best.get("url")
    except Exception:
        pass
    return None

def buscar_en_youtube(query, cookies_file=None, duracion_ms=0):
    """
    Busca en YouTube normal usando ytsearch5 con scoring inteligente.
    Retorna la URL del mejor resultado o None.
    """
    opts = {
        "skip_download": True,
        "quiet":         True,
        "no_warnings":   True,
        "extract_flat":  True,
    }
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            res = ydl.extract_info(f"ytsearch5:{query}", download=False)
            if not res:
                return None
            entries = [e for e in (res.get("entries") or []) if e]
            if not entries:
                return None
            if " - " in query:
                title, artist = query.split(" - ", 1)
            else:
                title, artist = query, ""
            best = max(entries, key=lambda e: score_result(e, title, artist, duracion_ms))
            return best.get("webpage_url") or best.get("url")
    except Exception:
        pass
    return None

def buscar_mejor_url(query, duracion_ms=0):
    """
    Busca primero en YT Music; si falla, busca en YouTube normal.
    Retorna (url, fuente) donde fuente es 'YT Music' o 'YouTube'.
    """
    print(f"   🎵 Buscando en YT Music...")
    url = buscar_en_ytmusic(query, COOKIES_YTMUSIC, duracion_ms)
    if url:
        print(f"   ✅ Encontrado en YT Music")
        return url, "YT Music"

    print(f"   ⚠️  No encontrado en YT Music → probando YouTube...")
    url = buscar_en_youtube(query, COOKIES_YOUTUBE, duracion_ms)
    if url:
        print(f"   ✅ Encontrado en YouTube")
        return url, "YouTube"

    print(f"   ❌ No se encontró en ninguna fuente.")
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
#  FFMPEG — CONSTRUCTOR DE COMANDO AUDIO
# ─────────────────────────────────────────────────────────────────────────────

# CAMBIO 2 — Helper: incrustar metadatos+carátula en m4a sin re-encodificar.
# Se usa exclusivamente cuando audio_format=="mp3" para evitar la conversión
# AAC→MP3 que aumenta el tamaño del archivo. El archivo resultante es un m4a
# legítimo que luego se renombra a .mp3.
def _construir_cmd_ffmpeg_m4a_copy(m4a_raw, cover_jpg, metadata_title,
                                    artista, album, out_m4a):
    """
    Construye el comando ffmpeg para copiar el stream de audio m4a/AAC
    e incrustar metadatos y carátula sin re-encodificar.

    Parámetros:
      m4a_raw        — ruta al archivo m4a descargado por yt-dlp
      cover_jpg      — ruta a la carátula JPEG (puede ser None)
      metadata_title — título limpio a incrustar como tag
      artista        — nombre del artista a incrustar como tag
      album          — nombre del álbum a incrustar como tag
      out_m4a        — ruta de salida del m4a tagueado

    Retorna una lista de argumentos lista para subprocess.run().
    """
    meta = [
        "-metadata", f"title={metadata_title}",
        "-metadata", f"artist={artista}",
        "-metadata", f"album={album}",
    ]
    tiene_cover = cover_jpg and os.path.exists(cover_jpg)
    if tiene_cover:
        # Con carátula: mapear audio + imagen, copiar ambos streams sin re-encode
        return (["ffmpeg", "-y",
                 "-i", m4a_raw, "-i", cover_jpg,
                 "-map", "0:a", "-map", "1:v",
                 "-c", "copy",
                 "-disposition:v:0", "attached_pic",
                 "-f", "mp4"]          # forzar contenedor mp4/m4a
                + meta + [out_m4a])
    # Sin carátula: solo copiar audio con metadatos
    return (["ffmpeg", "-y",
             "-i", m4a_raw, "-c", "copy", "-f", "mp4"]
            + meta + [out_m4a])


def _construir_cmd_ffmpeg_audio(m4a_raw, cover_jpg, audio_format,
                                 audio_quality, metadata_title,
                                 artista, album, final_file):
    """
    Construye la lista de argumentos ffmpeg correcta según el
    formato de audio solicitado: mp3, m4a o flac.
    """
    meta = [
        "-metadata", f"title={metadata_title}",
        "-metadata", f"artist={artista}",
        "-metadata", f"album={album}",
    ]
    tiene_cover = cover_jpg and os.path.exists(cover_jpg)

    if audio_format == "flac":
        if tiene_cover:
            return (["ffmpeg", "-y",
                     "-i", m4a_raw, "-i", cover_jpg,
                     "-map", "0:a", "-map", "1:v",
                     "-c:a", "flac", "-c:v", "copy",
                     "-disposition:v:0", "attached_pic"]
                    + meta + [final_file])
        return (["ffmpeg", "-y",
                 "-i", m4a_raw, "-c:a", "flac"]
                + meta + [final_file])

    elif audio_format == "m4a":
        if tiene_cover:
            return (["ffmpeg", "-y",
                     "-i", m4a_raw, "-i", cover_jpg,
                     "-map", "0:a", "-map", "1:v",
                     "-c", "copy",
                     "-disposition:v:0", "attached_pic",
                     "-f", "mp4"]
                    + meta + [final_file])
        return (["ffmpeg", "-y",
                 "-i", m4a_raw, "-c", "copy", "-f", "mp4"]
                + meta + [final_file])

    else:  # mp3 (default)
        if tiene_cover:
            return (["ffmpeg", "-y",
                     "-i", m4a_raw, "-i", cover_jpg,
                     "-map", "0:a", "-map", "1:v",
                     "-c:a", "libmp3lame",
                     "-b:a", f"{audio_quality}k",
                     "-c:v", "mjpeg",
                     "-id3v2_version", "3"]
                    + meta + [final_file])
        return (["ffmpeg", "-y",
                 "-i", m4a_raw,
                 "-c:a", "libmp3lame",
                 "-b:a", f"{audio_quality}k",
                 "-id3v2_version", "3"]
                + meta + [final_file])

# ─────────────────────────────────────────────────────────────────────────────
#  DESCARGA CORE — AUDIO
# ─────────────────────────────────────────────────────────────────────────────

def descargar_audio(url, audio_quality, cookies_file=None, noplaylist=True,
                    spotify_meta=None, track_num=None, total_tracks=None,
                    audio_format="mp3", show_info=True, silent=False,
                    max_retries=3):
    """
    Descarga audio de una URL de YouTube y lo convierte al formato indicado.

    Parámetros:
      url           — URL de YouTube o YT Music
      audio_quality — bitrate en kbps (str): "64","96","128","160","192","256","320"
      cookies_file  — ruta al archivo de cookies de YouTube
      noplaylist    — True para ignorar playlists (canción individual)
      spotify_meta  — dict con metadatos de Spotify (si viene de ese flujo)
      track_num     — número de pista actual
      total_tracks  — total de pistas en la colección
      audio_format  — "mp3", "m4a" o "flac"
      show_info     — True para mostrar el bloque de info de la canción
      silent        — True para suprimir la salida de yt-dlp
      max_retries   — MEJORA 2: intentos máximos de descarga+conversión (default 3)
    """
    global descargas_sesion

    if not verificar_ffmpeg():
        return None

    # ── Obtener información desde YouTube ────────────────────────────────────
    opts_info = {"skip_download": True, "quiet": True, "noplaylist": noplaylist}
    if cookies_file and os.path.exists(cookies_file):
        opts_info["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"❌ Error al obtener info de YouTube: {e}")
        return None

    # ── Playlist de YouTube (manejo recursivo) ───────────────────────────────
    if info.get("_type") == "playlist":
        entradas = [e for e in info.get("entries", []) if e]
        total    = len(entradas)
        print(f"\n📋 Playlist YouTube: {total} pistas detectadas [1/{total}→{total}/{total}]")
        for idx, entry in enumerate(entradas, 1):
            entry_url = entry.get("webpage_url") or entry.get("url")
            if entry_url:
                print(f"\n{'─'*50}")
                print(f"▶️  Procesando [{idx}/{total}]")
                descargar_audio(entry_url, audio_quality, cookies_file, True,
                               track_num=idx, total_tracks=total,
                               audio_format=audio_format, show_info=True)
        return "playlist_completada"

    # ── Construir metadatos ───────────────────────────────────────────────────
    if spotify_meta:
        titulo         = spotify_meta.get("title",        info.get("title",    "Desconocido"))
        artista        = spotify_meta.get("artist",        info.get("uploader", ""))
        album          = spotify_meta.get("album",         artista)
        t_num          = spotify_meta.get("track_number",  track_num)
        t_total        = spotify_meta.get("total_tracks",  total_tracks)
        cover_url_spot = spotify_meta.get("cover_url")
        metadata_title = titulo
        ext            = f".{audio_format}"
        filename_on_disk = sanitize_filename(f"{titulo}_-_{artista}") + ext
    else:
        filename_on_disk, metadata_title, titulo, artista_r, prod_part = build_names_from_info(info)
        artista         = info.get("uploader", "")
        album           = artista
        t_num           = track_num
        t_total         = total_tracks
        cover_url_spot  = None
        if audio_format != "mp3":
            filename_on_disk = os.path.splitext(filename_on_disk)[0] + f".{audio_format}"

    # ── Mostrar info de la canción ────────────────────────────────────────────
    sep = "─" * 50
    if show_info:
        print(f"\n{sep}")
        if t_num and t_total:
            print(f"📀 Pista:      [{t_num}/{t_total}]")
        print(f"🎵 Nombre:    {titulo}")
        print(f"👤 Artista/s: {artista}")

    # ── Descargar carátula ────────────────────────────────────────────────────
    cover_jpg = None
    cover_tmp = os.path.join(OUTPUT_DIR, f"temp_cover_{t_num or 0}.jpg")

    if cover_url_spot:
        if show_info:
            print(f"🖼️  Carátula:  ⬇️  Descargando desde Spotify CDN...")
        if descargar_cover_spotify(cover_url_spot, cover_tmp):
            cover_jpg = cover_tmp
            if show_info:
                print(f"🖼️  Carátula:  ✅ Obtenida desde Spotify")
        else:
            if show_info:
                print(f"🖼️  Carátula:  ⚠️  Spotify falló → intentando desde YouTube...")
            cover_jpg = obtener_cover_yt(info)
            if show_info:
                status = "✅ Obtenida desde YouTube" if cover_jpg else "❌ No disponible"
                print(f"🖼️  Carátula:  {status}")
    else:
        cover_jpg = obtener_cover_yt(info)
        if show_info:
            status = "✅ Obtenida desde YouTube" if cover_jpg else "❌ No disponible"
            print(f"🖼️  Carátula:  {status}")

    if show_info:
        print(sep)

    # ── CAMBIO 1: Directorio dinámico por artista principal ──────────────────
    # Extraemos solo el primer artista cuando hay varios separados por coma,
    # punto y coma o "feat."  y lo sanitizamos para que sea nombre de carpeta válido.
    _artista_limpio = re.split(r'[,;&]| feat\.| ft\.', artista, flags=re.IGNORECASE)[0].strip()
    artista_dir     = sanitize_filename(_artista_limpio) if _artista_limpio else "Desconocido"
    # Ruta final: /storage/emulated/0/{artista_principal}
    artist_output_dir = f"/storage/emulated/0/{artista_dir}"
    # Crear la carpeta si no existe; si ya existe simplemente se reutiliza
    if not os.path.exists(artist_output_dir):
        os.makedirs(artist_output_dir, exist_ok=True)
        print(f"📁 Carpeta creada:   {artist_output_dir}")
    else:
        print(f"📁 Guardando en:     {artist_output_dir}")
    # ── Rutas temporales ─────────────────────────────────────────────────────
    # Los archivos temporales (_raw, _tagged) permanecen en OUTPUT_DIR para no
    # contaminar la carpeta del artista con basura en caso de error.
    base_name  = os.path.splitext(filename_on_disk)[0]
    m4a_raw    = os.path.join(OUTPUT_DIR, sanitize_filename(base_name) + "_raw.m4a")
    # CAMBIO 1: el archivo final va a la carpeta del artista, no a Music/
    final_file = os.path.join(artist_output_dir, filename_on_disk)

    ydl_opts = {
        "format":      "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl":     m4a_raw,
        "quiet":       silent,
        "no_warnings": True,
        "noplaylist":  True,
    }
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file

    # MEJORA 2 — Bucle de reintentos con backoff exponencial ──────────────────
    espera = 2
    for intento in range(1, max_retries + 1):
        # Limpiar archivos temporales de intentos anteriores
        for tmp_limpia in [m4a_raw, final_file]:
            try:
                if tmp_limpia and os.path.exists(tmp_limpia):
                    os.remove(tmp_limpia)
            except Exception:
                pass
        # Detectar extensiones alternativas que pudo haber dejado yt-dlp
        for ext_alt in [".m4a", ".webm", ".opus", ".mp4", ".aac"]:
            alt = m4a_raw.replace("_raw.m4a", f"_raw{ext_alt}")
            try:
                if os.path.exists(alt):
                    os.remove(alt)
            except Exception:
                pass

        print(f"📥 Descargando audio [{t_num or '?'}/{t_total or '?'}]"
              + (f" (intento {intento}/{max_retries})" if intento > 1 else "") + "...")

        # ── Descarga del audio crudo desde YouTube ────────────────────────────
        error_descarga = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            error_descarga = str(e)

        # Detectar extensión real si yt-dlp cambió el nombre
        m4a_real = m4a_raw
        if not os.path.exists(m4a_real):
            for ext_alt in [".m4a", ".webm", ".opus", ".mp4", ".aac"]:
                alt = m4a_raw.replace("_raw.m4a", f"_raw{ext_alt}")
                if os.path.exists(alt):
                    m4a_real = alt
                    break

        if not os.path.exists(m4a_real):
            razon = error_descarga or "archivo de audio no encontrado"
            if intento < max_retries:
                print(f"⚠️ Intento {intento}/{max_retries} fallido: {razon}. Reintentando en {espera}s...")
                time.sleep(espera)
                espera *= 2
                continue
            else:
                print(f"❌ Error durante la descarga tras {max_retries} intentos: {razon}")
                return None

        # ── CAMBIO 2: Conversión/renombrado según formato ─────────────────────
        # Para MP3: no re-encodificar (evita aumento de tamaño AAC→MP3).
        #   1. Usar ffmpeg -c copy para incrustar metadata+carátula en un m4a temporal.
        #   2. Renombrar el m4a resultante a .mp3 (extensión solo; audio sigue en AAC).
        # Para M4A y FLAC: mantener el flujo original de conversión con ffmpeg.
        if audio_format == "mp3":
            # Archivo intermedio: m4a con tags y carátula incrustados, sin re-encode
            tagged_m4a = os.path.join(OUTPUT_DIR,
                                      sanitize_filename(base_name) + "_tagged.m4a")
            print(f"🏷️  Incrustando metadatos y carátula (sin re-encodificar)...")
            cmd = _construir_cmd_ffmpeg_m4a_copy(
                m4a_real, cover_jpg, metadata_title, artista, album, tagged_m4a
            )
            p = run(cmd)

            if p.returncode != 0 or not os.path.exists(tagged_m4a):
                # Limpiar tagged temporal si quedó a medias
                try:
                    if os.path.exists(tagged_m4a):
                        os.remove(tagged_m4a)
                except Exception:
                    pass
                razon = p.stderr.decode(errors="ignore")[-200:].strip()
                if intento < max_retries:
                    print(f"⚠️ Intento {intento}/{max_retries} fallido:"
                          f" embedding metadatos. Reintentando en {espera}s...")
                    time.sleep(espera)
                    espera *= 2
                    continue
                else:
                    print("❌ Error al incrustar metadatos con ffmpeg:")
                    print(p.stderr.decode(errors="ignore")[-600:])
                    return None

            # CAMBIO 2: renombrar el m4a tagueado → extensión .mp3
            # (el audio sigue siendo AAC; solo cambia la extensión del contenedor)
            try:
                if os.path.exists(final_file):
                    os.remove(final_file)
                os.rename(tagged_m4a, final_file)
                print(f"📝 Renombrado a .mp3 (audio AAC, sin pérdida extra)")
            except OSError:
                # rename falla si src y dst están en particiones distintas → copiar
                shutil.copy2(tagged_m4a, final_file)
                os.remove(tagged_m4a)
                print(f"📝 Copiado a .mp3 (audio AAC, sin pérdida extra)")

        else:
            # Para M4A y FLAC: mantener el flujo de conversión original con ffmpeg
            print(f"🔄 Convirtiendo a {audio_format.upper()} ({audio_quality}k)...")
            cmd = _construir_cmd_ffmpeg_audio(
                m4a_real, cover_jpg, audio_format, audio_quality,
                metadata_title, artista, album, final_file
            )
            p = run(cmd)

            if p.returncode != 0 or not os.path.exists(final_file):
                razon = p.stderr.decode(errors="ignore")[-200:].strip()
                if intento < max_retries:
                    print(f"⚠️ Intento {intento}/{max_retries} fallido:"
                          f" conversión ffmpeg. Reintentando en {espera}s...")
                    time.sleep(espera)
                    espera *= 2
                    continue
                else:
                    print("❌ Error en la conversión ffmpeg:")
                    print(p.stderr.decode(errors="ignore")[-600:])
                    return None

        # ── Éxito: salir del bucle ────────────────────────────────────────────
        m4a_raw = m4a_real  # actualizar para limpieza
        break
    # MEJORA 2 — Fin del bucle de reintentos ──────────────────────────────────

    # ── Limpieza de temporales ────────────────────────────────────────────────
    for tmp in [m4a_raw, cover_jpg]:
        try:
            if tmp and os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass

    rescanear_archivo(final_file)
    agregar_al_historial(metadata_title, filename_on_disk, final_file,
                         "OK", bitrate=f"{audio_quality}k-{audio_format}")
    descargas_sesion += 1
    print(f"\n✅ [{t_num or '?'}/{t_total or '?'}] Listo: {final_file}")
    return final_file

# ─────────────────────────────────────────────────────────────────────────────
#  DESCARGA CORE — VIDEO
# ─────────────────────────────────────────────────────────────────────────────

def descargar_video(url, calidad_video="720", formato_video="mp4",
                    cookies_file=None, opciones=None,
                    track_num=None, total_tracks=None,
                    max_retries=3):
    """
    Descarga video de YouTube con la calidad y formato indicados.

    Parámetros:
      url            — URL de YouTube
      calidad_video  — altura máxima: "144","240","360","480","720",
                       "1080","1440","2160","4320"
      formato_video  — "mp4","mkv","webm"
      cookies_file   — ruta al archivo de cookies de YouTube
      opciones       — dict con flags extra (ver _seleccionar_opciones_extra)
      track_num      — número de ítem actual en la playlist
      total_tracks   — total de ítems en la playlist
      max_retries    — MEJORA 2: intentos máximos de descarga (default 3)
    """
    global descargas_sesion

    if not verificar_ffmpeg():
        return None

    if opciones is None:
        opciones = {}

    # ── Info desde YouTube ────────────────────────────────────────────────────
    opts_info = {"skip_download": True, "quiet": True, "noplaylist": True}
    if cookies_file and os.path.exists(cookies_file):
        opts_info["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"❌ Error al obtener info: {e}")
        return None

    raw_title     = re.sub(r'\s+', ' ', info.get("title", "Video").strip())
    uploader      = info.get("uploader", "")
    filename_base = sanitize_filename(raw_title) + f".{formato_video}"
    final_file    = os.path.join(OUTPUT_DIR, filename_base)

    # ── Mostrar info ──────────────────────────────────────────────────────────
    sep = "─" * 50
    print(f"\n{sep}")
    if track_num and total_tracks:
        print(f"📹 Video:     [{track_num}/{total_tracks}]")
    print(f"🎬 Nombre:    {raw_title}")
    print(f"👤 Canal:     {uploader}")

    # Carátula opcional
    cover_jpg = None
    if opciones.get("embed_thumbnail"):
        print(f"🖼️  Miniatura: ⬇️  Descargando...")
        cover_jpg = obtener_cover_yt(info)
        status = "✅ Obtenida" if cover_jpg else "❌ No disponible"
        print(f"🖼️  Miniatura: {status}")
    print(sep)

    # ── Formato de descarga ───────────────────────────────────────────────────
    height_map = {
        "144": 144, "240": 240,  "360": 360,  "480":  480,
        "720": 720, "1080": 1080, "1440": 1440, "2160": 2160, "4320": 4320
    }
    height = height_map.get(str(calidad_video), 720)

    if opciones.get("audio_only_original"):
        fmt = "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio"
    else:
        fmt = (f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]"
               f"/bestvideo[height<={height}]+bestaudio"
               f"/best[height<={height}]")

    ydl_opts = {
        "format":              fmt,
        "outtmpl":             final_file,
        "merge_output_format": formato_video,
        "quiet":               opciones.get("silencioso", False),
        "no_warnings":         True,
        "noplaylist":          not opciones.get("descargar_playlist", False),
        "continuedl":          opciones.get("continuar", False),
        "writesubtitles":      opciones.get("subs_separado", False),
        "writeautomaticsub":   opciones.get("subs_separado", False),
        "subtitleslangs":      ["es", "en"] if opciones.get("subs_separado") else [],
        "embedsubtitles":      opciones.get("subs_incrustado", False),
        "retries":             opciones.get("reintentos", MAX_REINTENTOS),
    }
    if cookies_file and os.path.exists(cookies_file):
        ydl_opts["cookiefile"] = cookies_file
    if opciones.get("limite_velocidad"):
        ydl_opts["ratelimit"] = opciones["limite_velocidad"]
    if opciones.get("split_chapters"):
        ydl_opts["split_chapters"] = True

    # Fragmento de tiempo
    if opciones.get("inicio") or opciones.get("fin"):
        inicio_s = _tiempo_a_segundos(opciones.get("inicio", "0"))
        fin_s    = _tiempo_a_segundos(opciones.get("fin", "0")) if opciones.get("fin") else None
        ydl_opts["external_downloader"] = "ffmpeg"
        ea = ["-ss", str(inicio_s)]
        if fin_s:
            ea += ["-to", str(fin_s)]
        ydl_opts["external_downloader_args"] = {"ffmpeg_i": ea}

    # MEJORA 2 — Bucle de reintentos con backoff exponencial ──────────────────
    espera = 2
    for intento in range(1, max_retries + 1):
        # Limpiar archivo parcial de intento anterior
        try:
            if os.path.exists(final_file):
                os.remove(final_file)
        except Exception:
            pass

        print(f"📥 Descargando video {calidad_video}p en {formato_video.upper()}..."
              + (f" (intento {intento}/{max_retries})" if intento > 1 else ""))

        error_descarga = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            error_descarga = str(e)

        if not os.path.exists(final_file):
            razon = error_descarga or "archivo de video no encontrado"
            if intento < max_retries:
                print(f"⚠️ Intento {intento}/{max_retries} fallido: {razon}. Reintentando en {espera}s...")
                time.sleep(espera)
                espera *= 2
                continue
            else:
                print(f"❌ Error durante la descarga de video tras {max_retries} intentos: {razon}")
                return None
        break  # Descarga exitosa
    # MEJORA 2 — Fin del bucle de reintentos ──────────────────────────────────

    # ── Incrustar miniatura si se pidió ───────────────────────────────────────
    if cover_jpg and os.path.exists(cover_jpg) and opciones.get("embed_thumbnail"):
        tmp_out = final_file + "_thumb.mp4"
        p = run(["ffmpeg", "-y",
                 "-i", final_file, "-i", cover_jpg,
                 "-map", "0", "-map", "1",
                 "-c", "copy",
                 "-disposition:v:1", "attached_pic",
                 tmp_out])
        if p.returncode == 0 and os.path.exists(tmp_out):
            try:
                os.remove(final_file)
                os.rename(tmp_out, final_file)
            except Exception:
                pass
        try:
            os.remove(cover_jpg)
        except Exception:
            pass

    # ── Conversión móvil (3GP) ────────────────────────────────────────────────
    if opciones.get("modo_movil"):
        mov_file = final_file.replace(f".{formato_video}", "_movil.3gp")
        p = run(["ffmpeg", "-y", "-i", final_file,
                 "-vcodec", "h263", "-acodec", "aac",
                 "-s", "qcif", "-r", "15", mov_file])
        if p.returncode == 0 and os.path.exists(mov_file):
            print(f"📱 Versión móvil 3GP: {mov_file}")
            rescanear_archivo(mov_file)

    rescanear_archivo(final_file)
    agregar_al_historial(raw_title, filename_base, final_file, "OK",
                         bitrate=f"{calidad_video}p-{formato_video}")
    descargas_sesion += 1

    # ── Abrir con VLC / reproductor por defecto ───────────────────────────────
    if opciones.get("abrir_vlc"):
        try:
            subprocess.Popen([
                "am", "start", "-a", "android.intent.action.VIEW",
                "-d", f"file://{final_file}", "-t", "video/mp4"
            ])
            print("▶️  Abriendo con VLC / reproductor por defecto...")
        except Exception:
            pass

    print(f"\n✅ [{track_num or '?'}/{total_tracks or '?'}] Video listo: {final_file}")
    return final_file

# ─────────────────────────────────────────────────────────────────────────────
#  OPCIONES EXTRA (submenú reutilizable)
# ─────────────────────────────────────────────────────────────────────────────

def _seleccionar_opciones_extra():
    """
    Muestra el menú de opciones extra avanzadas.
    El usuario puede seleccionar varias separadas por espacio.
    Retorna un dict con las opciones activadas.
    """
    print("\n" + "─" * 50)
    print("  🔧  OPCIONES EXTRA")
    print("  (Escribe números separados por espacio, ej: 1 3 5)")
    print("  (O '0' para continuar sin opciones extra)")
    print("─" * 50)
    print("  [1] Subtítulos incrustados en el video")
    print("  [2] Subtítulos como archivo separado (.srt/.vtt)")
    print("  [3] Incrustar miniatura/portada del video")
    print("  [4] Continuar descarga interrumpida (--continue)")
    print("  [5] Limitar velocidad de descarga (ej: 500K, 2M)")
    print("  [6] Solo audio original sin conversión (M4A/WEBM directo)")
    print("  [7] Extraer capítulos como archivos separados")
    print("  [8] Compatibilidad móvil (generar versión 3GP adicional)")
    print("  [9] Abrir archivo con VLC al terminar")
    print("  [0] Sin opciones extra → continuar")
    print("─" * 50)

    seleccion = input("  Elige opciones: ").strip().split()
    opciones  = {}

    if not seleccion or "0" in seleccion:
        print("  ℹ️  Sin opciones extra.")
        return opciones

    if "1" in seleccion:
        opciones["subs_incrustado"] = True
        print("  ✅ Subtítulos incrustados: activado")
    if "2" in seleccion:
        opciones["subs_separado"] = True
        print("  ✅ Subtítulos separados: activado (es + en)")
    if "3" in seleccion:
        opciones["embed_thumbnail"] = True
        print("  ✅ Miniatura incrustada: activado")
    if "4" in seleccion:
        opciones["continuar"] = True
        print("  ✅ Continuar descarga: activado")
    if "5" in seleccion:
        lim = input("  Límite de velocidad (ej: 500K / 2M): ").strip()
        if lim:
            opciones["limite_velocidad"] = lim
            print(f"  ✅ Límite: {lim}/s")
    if "6" in seleccion:
        opciones["audio_only_original"] = True
        print("  ✅ Audio original sin conversión: M4A/WEBM")
    if "7" in seleccion:
        opciones["split_chapters"] = True
        print("  ✅ Extraer capítulos: activado")
    if "8" in seleccion:
        opciones["modo_movil"] = True
        print("  ✅ Modo móvil 3GP: activado")
    if "9" in seleccion:
        opciones["abrir_vlc"] = True
        print("  ✅ Abrir con VLC al terminar: activado")

    # Fragmento de tiempo (inicio/fin)
    frag = input("\n  ¿Descargar solo un fragmento? [s/n]: ").strip().lower()
    if frag == "s":
        inicio = input("  Tiempo de inicio (ej: 00:01:30): ").strip()
        fin    = input("  Tiempo de fin    (ej: 00:03:45): ").strip()
        if inicio:
            opciones["inicio"] = inicio
        if fin:
            opciones["fin"] = fin
        print(f"  ✅ Fragmento: {inicio or '0'} → {fin or 'fin'}")

    return opciones

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ 1 — YOUTUBE INDIVIDUAL
# ─────────────────────────────────────────────────────────────────────────────

def menu_youtube_individual():
    """Opción 1 — Descargar video o audio individual de YouTube."""
    global _cfg
    print("\n" + "═" * 50)
    print("  📺  YOUTUBE — Descarga Individual")
    print("═" * 50)
    url = input("🔗 Ingresa el link de YouTube: ").strip()
    if not url:
        print("❌ URL vacía.")
        return

    print("\n¿Qué deseas descargar?")
    print("  [1] 🎵 Audio (MP3 / M4A / FLAC)")
    print("  [2] 📹 Video (MP4 / MKV / WEBM)")
    tipo = input("Elige [1/2]: ").strip()

    cookies = COOKIES_YOUTUBE if os.path.exists(COOKIES_YOUTUBE) else None

    if tipo == "2":
        # ── VIDEO ─────────────────────────────────────────────────────────────
        dq = _cfg["default_video_quality"]
        df = _cfg["default_video_format"]
        print("\n📹 Calidad de video:")
        print("  [1]  144p         [2]  240p")
        print("  [3]  360p         [4]  480p  (SD)")
        print(f"  [5]  720p  (HD)   [6]  1080p (Full HD)")
        print("  [7]  1440p (2K)   [8]  2160p (4K)")
        print("  [9]  4320p (8K)")
        cal_v = {"1":"144","2":"240","3":"360","4":"480",
                 "5":"720","6":"1080","7":"1440","8":"2160","9":"4320"}
        cv    = input(f"Elige [1-9] (default = {dq}p, Enter para usar): ").strip()
        calidad_video = cal_v.get(cv, dq)  # MEJORA 3: usa default guardado

        print(f"\n📂 Formato de video:")
        print("  [1] MP4  [2] MKV  [3] WEBM")
        fmt_v = {"1":"mp4","2":"mkv","3":"webm"}
        fv    = input(f"Elige [1-3] (default = {df.upper()}, Enter para usar): ").strip()
        formato_video = fmt_v.get(fv, df)  # MEJORA 3: usa default guardado

        # MEJORA 3 — Guardar elecciones
        _cfg["default_video_quality"] = calidad_video
        _cfg["default_video_format"]  = formato_video
        guardar_config(_cfg)

        opciones = _seleccionar_opciones_extra()
        descargar_video(url, calidad_video, formato_video, cookies, opciones)
        return

    # ── AUDIO ──────────────────────────────────────────────────────────────────
    dq = _cfg["default_audio_quality"]
    df = _cfg["default_audio_format"]
    print("\n🎵 Calidad de audio (kbps):")
    print("  [1]  64k    [2]  96k    [3]  128k   [4]  160k")
    print("  [5]  192k   [6]  256k   [7]  320k")
    cal_a = {"1":"64","2":"96","3":"128","4":"160","5":"192","6":"256","7":"320"}
    ca    = input(f"Elige [1-7] (default = {dq}k, Enter para usar): ").strip()
    audio_quality = cal_a.get(ca, dq)  # MEJORA 3: usa default guardado

    print("\n📂 Formato de audio:")
    print("  [1] MP3  [2] M4A (sin recomprimir)  [3] FLAC")
    fmt_a = {"1":"mp3","2":"m4a","3":"flac"}
    fa    = input(f"Elige [1-3] (default = {df.upper()}, Enter para usar): ").strip()
    audio_format = fmt_a.get(fa, df)  # MEJORA 3: usa default guardado

    # MEJORA 3 — Guardar elecciones
    _cfg["default_audio_quality"] = audio_quality
    _cfg["default_audio_format"]  = audio_format
    guardar_config(_cfg)

    opciones = _seleccionar_opciones_extra()
    if opciones.get("audio_only_original"):
        audio_format = "m4a"

    descargar_audio(url, audio_quality,
                    cookies_file=cookies,
                    audio_format=audio_format,
                    show_info=True)

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ 2 — SPOTIFY
# ─────────────────────────────────────────────────────────────────────────────

def menu_spotify():
    """Opción 2 — Spotify: Track individual / Álbum / Playlist."""
    print("\n" + "═" * 50)
    print("  🟢  SPOTIFY — Track / Álbum / Playlist")
    print("═" * 50)
    url = input("🔗 Ingresa el link de Spotify: ").strip()
    if not url:
        print("❌ URL vacía.")
        return

    print("\n⏳ Conectando a Spotify y obteniendo metadatos...")
    tipo, tracks = obtener_metadatos_spotify(url)

    if not tracks:
        print("\n❌ No se obtuvieron metadatos de Spotify.")
        print("   Posibles causas:")
        print("   • El link no es válido (track/album/playlist)")
        print("   • El contenido es privado (solo visible en tu cuenta)")
        print("   • Error temporal de conexión con Spotify API")
        return

    total        = len(tracks)
    es_coleccion = (tipo in ("album", "playlist")) and total > 1
    tipo_label   = {"track": "Track", "album": "Álbum", "playlist": "Playlist"}.get(tipo, tipo)

    print(f"\n{'─'*50}")
    print(f"📀 Tipo detectado:  {tipo_label}")
    print(f"🔢 Total de pistas: {total}  [1/{total} → {total}/{total}]")
    print(f"{'─'*50}")

    # ── Calidad ────────────────────────────────────────────────────────────────
    if es_coleccion:
        audio_quality = "160"
        print(f"📊 Calidad automática para colección: 160k")
    else:
        print(f"\n📊 Calidad de audio (kbps):")
        print(f"  [1] 64k   [2] 96k   [3] 128k  [4] 160k")
        print(f"  [5] 192k  [6] 256k  [7] 320k")
        cal_a = {"1":"64","2":"96","3":"128","4":"160","5":"192","6":"256","7":"320"}
        ca    = input("Elige [1-7] (default 5 = 192k): ").strip()
        audio_quality = cal_a.get(ca, "192")

    print("\n📂 Formato de audio:")
    print("  [1] MP3  [2] M4A  [3] FLAC")
    fmt_a = {"1":"mp3","2":"m4a","3":"flac"}
    fa    = input("Elige [1-3] (default 1 = MP3): ").strip()
    audio_format = fmt_a.get(fa, "mp3")

    # ── Proceso canción por canción ────────────────────────────────────────────
    errores = 0
    for i, track_meta in enumerate(tracks, 1):
        print(f"\n{'═'*50}")
        print(f"🔢 Pista:     [{i}/{total}]")
        print(f"🎵 Nombre:    {track_meta['title']}")
        print(f"👤 Artista/s: {track_meta['artist']}")
        if tipo in ("album", "playlist"):
            print(f"💿 Álbum:     {track_meta['album']}")
        cover_disp = "⏳ Disponible (Spotify CDN)" if track_meta.get("cover_url") else "❌ No disponible"
        print(f"🖼️  Carátula:  {cover_disp}")

        # Búsqueda
        query = f"{track_meta['title']} - {track_meta['artist']}"
        print(f"\n🔍 Buscando: {query}")
        yt_url, fuente = buscar_mejor_url(query, track_meta.get("duration_ms", 0))

        if not yt_url:
            print(f"❌ Sin resultado para [{i}/{total}]: {track_meta['title']}")
            errores += 1
            continue

        print(f"🔗 Fuente encontrada: {fuente}")

        # Seleccionar cookies según la fuente
        cookies_dl = (COOKIES_YTMUSIC if fuente == "YT Music"
                      else COOKIES_YOUTUBE)

        # Descarga (show_info=False: la info ya se mostró arriba)
        result = descargar_audio(
            yt_url, audio_quality,
            cookies_file  = cookies_dl,
            spotify_meta  = track_meta,
            track_num     = i,
            total_tracks  = total,
            audio_format  = audio_format,
            show_info     = False
        )

        if not result:
            errores += 1
            print(f"⚠️  Falló descarga de [{i}/{total}]: {track_meta['title']}")

        if es_coleccion and i < total:
            time.sleep(1)  # Pausa breve entre pistas

    # ── Resumen final ──────────────────────────────────────────────────────────
    print(f"\n{'═'*50}")
    print(f"📊 {tipo_label} completado: ✅ {total - errores}/{total} pistas OK")
    if errores:
        print(f"   ⚠️  {errores} pista(s) no pudieron descargarse.")

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ 3 — PLAYLIST YOUTUBE
# ─────────────────────────────────────────────────────────────────────────────

def menu_playlist_youtube():
    """Opción 3 — Descargar playlist completa de YouTube (video o audio)."""
    print("\n" + "═" * 50)
    print("  📋  PLAYLIST DE YOUTUBE")
    print("═" * 50)
    url = input("🔗 Ingresa la URL de la playlist: ").strip()
    if not url:
        print("❌ URL vacía.")
        return

    print("\n¿Qué deseas descargar?")
    print("  [1] 🎵 Audio  [2] 📹 Video")
    tipo    = input("Elige [1/2]: ").strip()
    cookies = COOKIES_YOUTUBE if os.path.exists(COOKIES_YOUTUBE) else None

    if tipo == "2":
        # ── Video playlist ─────────────────────────────────────────────────────
        print("\n📹 Calidad de video:")
        print("  [1] 144p  [2] 240p  [3] 360p  [4] 480p")
        print("  [5] 720p  [6] 1080p [7] 1440p [8] 2160p  [9] 4320p")
        cal_v = {"1":"144","2":"240","3":"360","4":"480",
                 "5":"720","6":"1080","7":"1440","8":"2160","9":"4320"}
        cv    = input("Elige [1-9] (default 5 = 720p): ").strip()
        calidad_video = cal_v.get(cv, "720")

        print("\n📂 Formato: [1] MP4  [2] MKV  [3] WEBM")
        fmt_v = {"1":"mp4","2":"mkv","3":"webm"}
        fv    = input("Elige [1-3] (default 1): ").strip()
        formato_video = fmt_v.get(fv, "mp4")

        # Obtener lista de videos de la playlist
        opts_pl = {"skip_download": True, "quiet": True, "extract_flat": True}
        if cookies:
            opts_pl["cookiefile"] = cookies
        try:
            with yt_dlp.YoutubeDL(opts_pl) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"❌ Error obteniendo playlist: {e}")
            return

        entradas = [e for e in (info.get("entries") or []) if e]
        total    = len(entradas)
        print(f"\n📋 Playlist detectada: {total} videos [1/{total} → {total}/{total}]")

        opciones = _seleccionar_opciones_extra()
        for i, entry in enumerate(entradas, 1):
            entry_url = entry.get("webpage_url") or entry.get("url")
            if entry_url:
                print(f"\n{'─'*50}")
                descargar_video(entry_url, calidad_video, formato_video, cookies,
                               opciones, track_num=i, total_tracks=total)
    else:
        # ── Audio playlist ─────────────────────────────────────────────────────
        print("\n🎵 Calidad de audio:")
        print("  [1] 64k  [2] 96k  [3] 128k  [4] 160k")
        print("  [5] 192k [6] 256k [7] 320k")
        cal_a = {"1":"64","2":"96","3":"128","4":"160","5":"192","6":"256","7":"320"}
        ca    = input("Elige [1-7] (default 5 = 192k): ").strip()
        audio_quality = cal_a.get(ca, "192")

        print("\n📂 Formato: [1] MP3  [2] M4A  [3] FLAC")
        fmt_a = {"1":"mp3","2":"m4a","3":"flac"}
        fa    = input("Elige [1-3] (default 1): ").strip()
        audio_format = fmt_a.get(fa, "mp3")

        descargar_audio(url, audio_quality,
                        cookies_file  = cookies,
                        noplaylist    = False,
                        audio_format  = audio_format)

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ 4 — LOTE DESDE .TXT
# ─────────────────────────────────────────────────────────────────────────────

def menu_lote_txt():
    """Opción 4 — Descarga masiva desde un archivo .txt (una URL por línea)."""
    print("\n" + "═" * 50)
    print("  📄  LOTE DESDE ARCHIVO .TXT")
    print("═" * 50)
    ruta_txt = input("📂 Ruta del archivo .txt: ").strip()
    if not os.path.exists(ruta_txt):
        print(f"❌ Archivo no encontrado: {ruta_txt}")
        return

    print("\n¿Qué deseas descargar?")
    print("  [1] 🎵 Audio  [2] 📹 Video")
    tipo    = input("Elige [1/2]: ").strip()
    cookies = COOKIES_YOUTUBE if os.path.exists(COOKIES_YOUTUBE) else None

    calidad_video = None
    formato_video = None
    audio_quality = None
    audio_format  = None

    if tipo == "2":
        print("\n📹 Calidad: [1]144p [2]240p [3]360p [4]480p [5]720p")
        print("           [6]1080p [7]1440p [8]2160p [9]4320p")
        cal_v = {"1":"144","2":"240","3":"360","4":"480",
                 "5":"720","6":"1080","7":"1440","8":"2160","9":"4320"}
        cv    = input("Elige [1-9] (default 5): ").strip()
        calidad_video = cal_v.get(cv, "720")
        formato_video = "mp4"
    else:
        print("\n🎵 Calidad: [1] 128k  [2] 192k  [3] 320k")
        cal_a2 = {"1":"128","2":"192","3":"320"}
        ca     = input("Elige [1-3] (default 2): ").strip()
        audio_quality = cal_a2.get(ca, "192")
        audio_format  = "mp3"

    with open(ruta_txt, "r", encoding="utf-8") as f:
        urls = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]

    total = len(urls)
    print(f"\n📋 {total} URLs encontradas en el archivo.")
    ok, fallo = 0, 0

    for i, url in enumerate(urls, 1):
        print(f"\n[{i}/{total}] ──────────────────────────────────")
        print(f"🔗 {url}")
        exito = False
        for intento in range(1, MAX_REINTENTOS + 1):
            if tipo == "2":
                res = descargar_video(url, calidad_video, formato_video,
                                      cookies, track_num=i, total_tracks=total)
            else:
                res = descargar_audio(url, audio_quality,
                                      cookies_file  = cookies,
                                      audio_format  = audio_format,
                                      track_num     = i,
                                      total_tracks  = total)
            if res:
                exito = True
                break
            print(f"⚠️  Intento {intento}/{MAX_REINTENTOS} fallido → reintentando en 3s...")
            time.sleep(3)

        if exito:
            ok += 1
        else:
            fallo += 1
            print(f"❌ No se pudo descargar: {url}")

    print(f"\n{'═'*50}")
    print(f"📊 Lote completado: ✅ {ok} OK  |  ❌ {fallo} fallidas")

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ 6 — REPARAR TAGS
# ─────────────────────────────────────────────────────────────────────────────

def menu_reparar_tags():
    """Opción 6 — Reparar tags de archivos ya descargados en OUTPUT_DIR."""
    print(f"\n🔧 REPARAR TAGS — {OUTPUT_DIR}")
    archivos = [f for f in os.listdir(OUTPUT_DIR)
                if f.lower().endswith((".mp3", ".m4a", ".mp4", ".flac"))]
    if not archivos:
        print("📭 No se encontraron archivos de audio.")
        return
    print(f"📁 {len(archivos)} archivos encontrados.")
    confirm = input("¿Proceder con la reparación? [s/n]: ").strip().lower()
    if confirm != "s":
        print("Operación cancelada.")
        return
    for nombre in archivos:
        ruta    = os.path.join(OUTPUT_DIR, nombre)
        base    = os.path.splitext(nombre)[0]
        tmp_out = ruta + "_fixed.mp4"
        print(f"\n🔄 Reparando: {nombre}")
        p = run(["ffmpeg", "-y", "-i", ruta, "-c", "copy",
                 "-metadata", f"title={base}", "-f", "mp4", tmp_out])
        if p.returncode == 0 and os.path.exists(tmp_out):
            try:
                os.remove(ruta)
                os.rename(tmp_out, ruta)
                print(f"   ✅ Reparado: {nombre}")
            except Exception as e:
                print(f"   ⚠️  Error renombrando: {e}")
        else:
            print(f"   ❌ Error reparando: {nombre}")
            try:
                if os.path.exists(tmp_out):
                    os.remove(tmp_out)
            except Exception:
                pass
        rescanear_archivo(ruta)
    print("\n✅ Reparación de tags completada.")

# ─────────────────────────────────────────────────────────────────────────────
#  MENÚ PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def mostrar_menu():
    """Imprime el menú principal con el contador de descargas de la sesión."""
    print("\n" + "═" * 55)
    print("  🎶  YT2MP3 PRO v3.0 — Descargador Multimedia Android")
    print("  📺 YouTube  +  🟢 Spotify  +  🎵 YT Music")
    print("═" * 55)
    print(f"  📦 Descargas esta sesión: {descargas_sesion}")
    # MEJORA 1 — Aviso sobre ytmusicapi
    if not YTMUSICAPI_DISPONIBLE:
        print("  ⚠️  ytmusicapi no instalado → búsqueda YT Music en modo fallback")
        print("      (pip install ytmusicapi  para mejor precisión)")
    print("─" * 55)
    print("  [1] 📺 YouTube  — Video / Audio individual")
    print("  [2] 🟢 Spotify  — Track / Álbum / Playlist")
    print("  [3] 📋 YouTube  — Playlist completa (video o audio)")
    print("  [4] 📄 Lote     — Desde archivo .txt")
    print("  [5] 📋 Historial de descargas")
    print("  [6] 🔧 Reparar tags de archivos")
    print("  [7] ⚙️  Resetear configuración a valores por defecto")  # MEJORA 3
    print("  [0] 👋 Salir")
    print("─" * 55)


def main():
    """Punto de entrada principal con menú interactivo en bucle."""
    global descargas_sesion

    while True:
        mostrar_menu()
        opcion = input("  → Elige una opción: ").strip()

        if   opcion == "1": menu_youtube_individual()
        elif opcion == "2": menu_spotify()
        elif opcion == "3": menu_playlist_youtube()
        elif opcion == "4": menu_lote_txt()
        elif opcion == "5": mostrar_historial()
        elif opcion == "6": menu_reparar_tags()
        elif opcion == "7": resetear_config(); _cfg.update(cargar_config())  # MEJORA 3
        elif opcion == "0":
            print(f"\n👋 Saliendo... Total descargadas esta sesión: {descargas_sesion}")
            print("✅ ¡Hasta la próxima!")
            sys.exit(0)
        else:
            print("⚠️  Opción no válida. Elige entre 0 y 7.")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
