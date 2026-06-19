// Elementos del DOM
const urlInput = document.getElementById('url-input');
const fetchInfoBtn = document.getElementById('fetch-info-btn');
const loadingInfo = document.getElementById('loading-info');
const infoSection = document.getElementById('info-section');
const infoContent = document.getElementById('info-content');
const optionsSection = document.getElementById('options-section');
const optionsContent = document.getElementById('options-content');
const downloadBtn = document.getElementById('download-btn');
const downloadStatus = document.getElementById('download-status');
const historyContent = document.getElementById('history-content');

// Estado global
let currentInfo = null;
let currentTaskId = null;

// ------------------------------------------------------------------
// 1. OBTENER INFORMACIÓN
// ------------------------------------------------------------------
fetchInfoBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) {
        alert('Por favor ingresa una URL válida');
        return;
    }

    loadingInfo.classList.remove('hidden');
    infoSection.classList.add('hidden');
    optionsSection.classList.add('hidden');

    try {
        const response = await fetch(`/api/info?url=${encodeURIComponent(url)}`);
        const data = await response.json();

        if (data.error) {
            alert('Error: ' + data.error);
            loadingInfo.classList.add('hidden');
            return;
        }

        currentInfo = data;
        renderInfo(data);
        renderOptions(data);
        infoSection.classList.remove('hidden');
        optionsSection.classList.remove('hidden');
    } catch (err) {
        alert('Error de conexión: ' + err.message);
    } finally {
        loadingInfo.classList.add('hidden');
    }
});

// ------------------------------------------------------------------
// 2. RENDERIZAR INFORMACIÓN
// ------------------------------------------------------------------
function renderInfo(data) {
    let html = '';

    if (data.type === 'video' || data.type === 'spotify_track') {
        const thumbnail = data.thumbnail || data.cover_url || '';
        const duration = data.duration ? formatDuration(data.duration) : '';
        const artist = data.artist || data.uploader || '';

        html = `
            <img class="thumbnail" src="${thumbnail}" alt="Carátula" onerror="this.src='https://via.placeholder.com/160x90?text=No+image'">
            <div class="details">
                <div class="title">${escapeHtml(data.title)}</div>
                <div class="artist">${escapeHtml(artist)}</div>
                ${duration ? `<div class="duration">⏱️ ${duration}</div>` : ''}
            </div>
        `;
    } else if (data.type === 'playlist' || data.type === 'spotify_playlist') {
        html = `
            <div class="details" style="width:100%">
                <div class="title">📋 ${escapeHtml(data.title)}</div>
                <div class="artist">${data.count} canciones</div>
                <ul style="max-height:200px; overflow-y:auto; margin-top:10px; list-style:none; padding:0;">
                    ${data.entries.map((item, i) => `
                        <li style="padding:5px 0; border-bottom:1px solid #eee;">
                            ${i+1}. ${escapeHtml(item.title || item.titulo)} 
                            ${item.artist || item.artista ? `— ${escapeHtml(item.artist || item.artista)}` : ''}
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    }

    infoContent.innerHTML = html;
}

// ------------------------------------------------------------------
// 3. RENDERIZAR OPCIONES
// ------------------------------------------------------------------
function renderOptions(data) {
    const isAudio = (data.type === 'video' || data.type === 'spotify_track' || data.type === 'playlist' || data.type === 'spotify_playlist');
    // Por defecto, si es video de YouTube, permitir audio o video
    let html = '';

    // Selector de tipo (audio/video) solo para YouTube individual
    if (data.type === 'video') {
        html += `
            <div>
                <label>Tipo de descarga:</label>
                <select id="media-type">
                    <option value="audio">🎵 Audio</option>
                    <option value="video">🎬 Video</option>
                </select>
            </div>
        `;
    }

    // Calidad
    html += `
        <div>
            <label>Calidad:</label>
            <select id="quality-select">
    `;
    if (data.type === 'video') {
        // Opciones de video
        const qualities = ['144', '240', '360', '480', '720', '1080', '1440', '2160', '4320'];
        qualities.forEach(q => {
            html += `<option value="${q}">${q}p</option>`;
        });
    } else {
        // Opciones de audio
        const qualities = ['64', '96', '128', '160', '192', '256', '320'];
        qualities.forEach(q => {
            html += `<option value="${q}">${q} kbps</option>`;
        });
        html += `<option value="320" selected>192 kbps</option>`; // default
    }
    html += `</select></div>`;

    // Formato
    html += `
        <div>
            <label>Formato:</label>
            <select id="format-select">
    `;
    if (data.type === 'video') {
        html += `
            <option value="mp4">MP4</option>
            <option value="mkv">MKV</option>
            <option value="webm">WEBM</option>
        `;
    } else {
        html += `
            <option value="mp3" selected>MP3</option>
            <option value="m4a">M4A (AAC)</option>
            <option value="flac">FLAC</option>
        `;
    }
    html += `</select></div>`;

    // Opciones extra (checkboxes)
    html += `
        <div class="extra-options">
            <label><input type="checkbox" id="opt-subs-embed"> Subtítulos incrustados</label>
            <label><input type="checkbox" id="opt-subs-sep"> Subtítulos separados (.srt)</label>
            <label><input type="checkbox" id="opt-thumbnail"> Incrustar carátula</label>
            <label><input type="checkbox" id="opt-continue"> Continuar descarga</label>
            <label><input type="checkbox" id="opt-movil"> Modo móvil (3GP)</label>
            <label><input type="checkbox" id="opt-vlc"> Abrir con VLC</label>
        </div>
    `;

    optionsContent.innerHTML = html;

    // Evento para cambiar opciones según tipo (audio/video)
    const mediaTypeSelect = document.getElementById('media-type');
    if (mediaTypeSelect) {
        mediaTypeSelect.addEventListener('change', function() {
            updateOptionsForType(this.value);
        });
    }
}

function updateOptionsForType(type) {
    const qualitySelect = document.getElementById('quality-select');
    const formatSelect = document.getElementById('format-select');
    if (!qualitySelect || !formatSelect) return;

    if (type === 'video') {
        // Cambiar a opciones de video
        qualitySelect.innerHTML = `
            <option value="144">144p</option>
            <option value="240">240p</option>
            <option value="360">360p</option>
            <option value="480">480p</option>
            <option value="720" selected>720p</option>
            <option value="1080">1080p</option>
            <option value="1440">1440p</option>
            <option value="2160">2160p</option>
            <option value="4320">4320p</option>
        `;
        formatSelect.innerHTML = `
            <option value="mp4" selected>MP4</option>
            <option value="mkv">MKV</option>
            <option value="webm">WEBM</option>
        `;
    } else {
        qualitySelect.innerHTML = `
            <option value="64">64 kbps</option>
            <option value="96">96 kbps</option>
            <option value="128">128 kbps</option>
            <option value="160">160 kbps</option>
            <option value="192" selected>192 kbps</option>
            <option value="256">256 kbps</option>
            <option value="320">320 kbps</option>
        `;
        formatSelect.innerHTML = `
            <option value="mp3" selected>MP3</option>
            <option value="m4a">M4A (AAC)</option>
            <option value="flac">FLAC</option>
        `;
    }
}

// ------------------------------------------------------------------
// 4. DESCARGA
// ------------------------------------------------------------------
downloadBtn.addEventListener('click', async () => {
    const url = urlInput.value.trim();
    if (!url) return;

    // Recoger opciones
    const mediaTypeSelect = document.getElementById('media-type');
    const mediaType = mediaTypeSelect ? mediaTypeSelect.value : 'audio';
    const quality = document.getElementById('quality-select').value;
    const format = document.getElementById('format-select').value;

    const options = {
        subs_incrustado: document.getElementById('opt-subs-embed')?.checked || false,
        subs_separado: document.getElementById('opt-subs-sep')?.checked || false,
        embed_thumbnail: document.getElementById('opt-thumbnail')?.checked || false,
        continuar: document.getElementById('opt-continue')?.checked || false,
        modo_movil: document.getElementById('opt-movil')?.checked || false,
        abrir_vlc: document.getElementById('opt-vlc')?.checked || false,
    };

    downloadStatus.innerHTML = '⏳ Iniciando descarga... (puede tardar)';
    downloadBtn.disabled = true;

    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                type: mediaType,
                quality,
                format,
                options
            })
        });
        const data = await response.json();
        if (data.error) {
            downloadStatus.innerHTML = `❌ Error: ${data.error}`;
            downloadBtn.disabled = false;
            return;
        }

        const taskId = data.task_id;
        currentTaskId = taskId;
        downloadStatus.innerHTML = `⏳ Procesando (ID: ${taskId.slice(0,8)})...`;

        // Polling de estado
        const interval = setInterval(async () => {
            try {
                const statusRes = await fetch(`/api/status/${taskId}`);
                const statusData = await statusRes.json();

                if (statusData.status === 'completed') {
                    clearInterval(interval);
                    downloadStatus.innerHTML = `
                        ✅ ¡Descarga completada! 
                        <br><a href="/download/${encodeURIComponent(statusData.filename)}" class="btn-secondary" style="display:inline-block;margin-top:10px;">📥 Descargar archivo</a>
                    `;
                    downloadBtn.disabled = false;
                    // Actualizar historial
                    loadHistory();
                } else if (statusData.status === 'failed') {
                    clearInterval(interval);
                    downloadStatus.innerHTML = `❌ Error: ${statusData.error || 'Falló la descarga'}`;
                    downloadBtn.disabled = false;
                }
            } catch (err) {
                // Ignorar errores de polling
            }
        }, 3000);

    } catch (err) {
        downloadStatus.innerHTML = `❌ Error de conexión: ${err.message}`;
        downloadBtn.disabled = false;
    }
});

// ------------------------------------------------------------------
// 5. HISTORIAL
// ------------------------------------------------------------------
async function loadHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        if (!data.length) {
            historyContent.innerHTML = '<p>No hay descargas registradas.</p>';
            return;
        }
        let html = '';
        data.slice().reverse().forEach(item => {
            html += `
                <div class="history-item">
                    <div>
                        <div class="title">${escapeHtml(item.titulo_original || 'Sin título')}</div>
                        <div style="font-size:0.85rem;color:#5f6368;">${escapeHtml(item.nombre_disco || '')}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:0.85rem;">${escapeHtml(item.bitrate || '')}</div>
                        <div class="date">${escapeHtml(item.fecha || '')}</div>
                    </div>
                </div>
            `;
        });
        historyContent.innerHTML = html;
    } catch (err) {
        historyContent.innerHTML = '<p>Error al cargar historial</p>';
    }
}

// ------------------------------------------------------------------
// UTILIDADES
// ------------------------------------------------------------------
function formatDuration(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return h ? `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}` : `${m}:${String(s).padStart(2,'0')}`;
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
}

// Cargar historial al iniciar
loadHistory();

// Permitir presionar Enter en el input
urlInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        fetchInfoBtn.click();
    }
});
