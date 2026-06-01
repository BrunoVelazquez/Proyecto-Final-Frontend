// ── Panel de inferencia YOLO + SAHI — batch con marcadores y zoom de imagen ──

(function () {
  const btnOpen      = document.getElementById('btn-open-panel');
  const btnClose     = document.getElementById('btn-close-panel');
  const panel        = document.getElementById('panel');
  const btnProc      = document.getElementById('btn-procesar');
  const btnCancel    = document.getElementById('btn-cancel');
  const statusBox    = document.getElementById('status-box');
  const chkLocal     = document.getElementById('chk-local');
  const localBlock   = document.getElementById('local-model-block');
  const sourceBadge  = document.getElementById('source-badge');
  const imageList    = document.getElementById('image-list');
  const imgListHeader= document.getElementById('img-list-header');
  const imgCountLabel= document.getElementById('img-count-label');
  const btnClearImgs = document.getElementById('btn-clear-images');
  const batchProgress= document.getElementById('batch-progress');
  const progressFill = document.getElementById('progress-fill');
  const progressLabel= document.getElementById('progress-label');

  // Lightbox
  const lightbox     = document.getElementById('img-lightbox');
  const lbImg        = document.getElementById('lb-img');
  const lbClose      = document.getElementById('lb-close');
  const lbCaption    = document.getElementById('lb-caption');

  let filesImagen = [];
  let fileGPS     = null;
  let fileModelo  = null;
  let cancelFlag  = false;

  // ── Panel ─────────────────────────────────────────────────────────────────
  btnOpen.addEventListener('click',  () => panel.classList.add('open'));
  btnClose.addEventListener('click', () => panel.classList.remove('open'));

  // ── Toggle modelo local ───────────────────────────────────────────────────
  chkLocal.addEventListener('change', () => {
    const isLocal = chkLocal.checked;
    localBlock.classList.toggle('hidden', !isLocal);
    sourceBadge.textContent = isLocal ? '📂 Local' : '🖥️ Default (servidor)';
    sourceBadge.className   = 'source-badge ' + (isLocal ? 'badge-local' : 'badge-default');
    if (!isLocal) fileModelo = null;
    checkReady();
  });

  // ── Drop zona imágenes (múltiples) ────────────────────────────────────────
  const dropImagen  = document.getElementById('drop-imagen');
  const inputImagen = document.getElementById('input-imagen');
  const labelImagen = document.getElementById('label-imagen');

  inputImagen.addEventListener('change', () => {
    addImages(Array.from(inputImagen.files));
    inputImagen.value = '';
  });
  dropImagen.addEventListener('dragover',  e => { e.preventDefault(); dropImagen.style.borderColor = '#1D9E75'; });
  dropImagen.addEventListener('dragleave', () => { dropImagen.style.borderColor = ''; });
  dropImagen.addEventListener('drop', e => {
    e.preventDefault(); dropImagen.style.borderColor = '';
    addImages(Array.from(e.dataTransfer.files).filter(f => /\.(jpe?g|png)$/i.test(f.name)));
  });

  function addImages(newFiles) {
    const existing = new Set(filesImagen.map(f => f.name));
    filesImagen.push(...newFiles.filter(f => !existing.has(f.name)));
    renderImageList();
    checkReady();
  }

  function renderImageList() {
    imageList.innerHTML = '';
    if (filesImagen.length === 0) {
      imgListHeader.style.display = 'none';
      labelImagen.textContent = 'Subir .JPG / .PNG — podés seleccionar varias';
      dropImagen.classList.remove('filled');
      return;
    }
    imgListHeader.style.display = 'flex';
    imgCountLabel.textContent = `${filesImagen.length} imagen${filesImagen.length !== 1 ? 'es' : ''} seleccionada${filesImagen.length !== 1 ? 's' : ''}`;
    labelImagen.textContent   = `${filesImagen.length} imagen${filesImagen.length !== 1 ? 'es' : ''} listas`;
    dropImagen.classList.add('filled');

    filesImagen.forEach((f, i) => {
      const chip = document.createElement('div');
      chip.className = 'img-chip';
      chip.id = `chip-${i}`;
      chip.innerHTML = `
        <span class="chip-name" title="${f.name}">${f.name}</span>
        <span class="chip-status" id="chip-status-${i}">pendiente</span>
        <button class="chip-remove" data-index="${i}" title="Quitar">✕</button>
      `;
      imageList.appendChild(chip);
    });

    imageList.querySelectorAll('.chip-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        filesImagen.splice(parseInt(btn.dataset.index), 1);
        renderImageList(); checkReady();
      });
    });
  }

  btnClearImgs.addEventListener('click', () => { filesImagen = []; renderImageList(); checkReady(); });

  // ── Drops simples ─────────────────────────────────────────────────────────
  function setupSimpleDrop(inputId, dropId, labelId, onFile) {
    const input = document.getElementById(inputId);
    const drop  = document.getElementById(dropId);
    const label = document.getElementById(labelId);
    input.addEventListener('change', () => {
      const f = input.files[0]; if (!f) return;
      onFile(f); label.textContent = f.name; drop.classList.add('filled');
    });
    drop.addEventListener('dragover',  e => { e.preventDefault(); drop.style.borderColor = '#1D9E75'; });
    drop.addEventListener('dragleave', () => { drop.style.borderColor = ''; });
    drop.addEventListener('drop', e => {
      e.preventDefault(); drop.style.borderColor = '';
      const f = e.dataTransfer.files[0]; if (!f) return;
      onFile(f); label.textContent = f.name; drop.classList.add('filled');
    });
  }
  setupSimpleDrop('input-gps',    'drop-gps',    'label-gps',    f => { fileGPS    = f; });
  setupSimpleDrop('input-modelo', 'drop-modelo', 'label-modelo', f => { fileModelo = f; checkReady(); });

  function checkReady() {
    btnProc.disabled = !(filesImagen.length > 0 && (chkLocal.checked ? !!fileModelo : true));
  }

  // ── Sliders ───────────────────────────────────────────────────────────────
  [['conf','conf-val', v => parseFloat(v).toFixed(2)],
   ['slice','slice-val', v => v],
   ['overlap','overlap-val', v => parseFloat(v).toFixed(2)]
  ].forEach(([id, outId, fmt]) => {
    document.getElementById(id).addEventListener('input', e => {
      document.getElementById(outId).textContent = fmt(e.target.value);
    });
  });

  // ── Lightbox ──────────────────────────────────────────────────────────────
  function openLightbox(src, caption) {
    lbImg.src       = src;
    lbCaption.textContent = caption;
    lightbox.classList.add('open');
    document.body.style.overflow = 'hidden';

    // Reset zoom/pan
    lbImg.style.transform  = 'scale(1) translate(0px,0px)';
    lbImg.dataset.scale    = '1';
    lbImg.dataset.tx       = '0';
    lbImg.dataset.ty       = '0';
  }

  function closeLightbox() {
    lightbox.classList.remove('open');
    document.body.style.overflow = '';
    lbImg.src = '';
  }

  lbClose.addEventListener('click', closeLightbox);
  lightbox.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

  // Zoom con rueda
  lbImg.addEventListener('wheel', e => {
    e.preventDefault();
    let scale = parseFloat(lbImg.dataset.scale || 1);
    scale = Math.min(8, Math.max(1, scale + (e.deltaY < 0 ? 0.25 : -0.25)));
    lbImg.dataset.scale = scale;
    applyTransform();
  }, { passive: false });

  // Drag para pan
  let dragging = false, startX, startY, startTx, startTy;
  lbImg.addEventListener('mousedown', e => {
    if (parseFloat(lbImg.dataset.scale || 1) <= 1) return;
    dragging = true;
    startX = e.clientX; startY = e.clientY;
    startTx = parseFloat(lbImg.dataset.tx || 0);
    startTy = parseFloat(lbImg.dataset.ty || 0);
    lbImg.style.cursor = 'grabbing';
    e.preventDefault();
  });
  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    lbImg.dataset.tx = startTx + (e.clientX - startX);
    lbImg.dataset.ty = startTy + (e.clientY - startY);
    applyTransform();
  });
  document.addEventListener('mouseup', () => {
    if (dragging) { dragging = false; lbImg.style.cursor = 'zoom-in'; }
  });

  // Touch pinch zoom
  let lastTouchDist = null;
  lbImg.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      lastTouchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
    }
  }, { passive: true });
  lbImg.addEventListener('touchmove', e => {
    if (e.touches.length === 2 && lastTouchDist) {
      const dist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      );
      let scale = parseFloat(lbImg.dataset.scale || 1) * (dist / lastTouchDist);
      scale = Math.min(8, Math.max(1, scale));
      lbImg.dataset.scale = scale;
      lastTouchDist = dist;
      applyTransform();
    }
  }, { passive: true });

  function applyTransform() {
    const s  = parseFloat(lbImg.dataset.scale || 1);
    const tx = parseFloat(lbImg.dataset.tx    || 0);
    const ty = parseFloat(lbImg.dataset.ty    || 0);
    lbImg.style.transform = `scale(${s}) translate(${tx / s}px, ${ty / s}px)`;
    lbImg.style.cursor    = s > 1 ? 'grab' : 'zoom-in';
  }

  // ── Crear marcador en el mapa con popup de imagen ─────────────────────────
  function addMapMarker(data, fileName) {
    // Si no hay datos GPS válidos, asignamos coordenadas por defecto (ej. Bahía Blanca) para no romper el flujo
    const tieneGPS = data.gps && data.gps.lat && data.gps.lon;
    const lat = tieneGPS ? data.gps.lat : -38.7183;
    const lon = tieneGPS ? data.gps.lon : -62.2663;

    const latlng = [lat, lon];
    const imgUrl  = data.result_image_url;
    const dets    = data.total_detections;
    const src     = data.model_source;

    // Icono personalizado según cantidad de detecciones (Gris: 0, Amarillo: Pocas, Verde: Muchas)
    const color = dets === 0 ? '#94a3b8' : dets < 5 ? '#f59e0b' : '#16a34a';
    
    // Si no tiene GPS real, le cambiamos sutilmente el estilo al marcador (borde punteado o línea roja) para identificarlo
    const estiloBorde = tieneGPS ? '2px solid #fff' : '2px dashed #ef4444';
    const tituloGPS = tieneGPS ? '' : ' (Sin datos GPS — Ubicación estimada)';

    const svgIcon = L.divIcon({
      className: '',
      html: `<div style="
        width:32px;height:32px;border-radius:50% 50% 50% 0;
        background:${color};border:${estiloBorde};
        box-shadow:0 2px 6px rgba(0,0,0,0.3);
        transform:rotate(-45deg);
        display:flex;align-items:center;justify-content:center;"
        title="${fileName}${tituloGPS}">
        <span style="transform:rotate(45deg);color:#fff;font-size:11px;font-weight:700;">${dets}</span>
      </div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -36],
    });

    const popupHtml = `
      <div style="width:240px;font-family:system-ui,sans-serif;">
        <div style="font-weight:600;font-size:13px;margin-bottom:6px;
                    white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
             title="${fileName}${tituloGPS}">${fileName}${tieneGPS ? '' : ' ⚠️'}</div>
        <img src="${imgUrl}"
             style="width:100%;border-radius:6px;cursor:zoom-in;display:block;
                    border:1px solid #e0e0e0;"
             title="Click para ampliar"
             onclick="window.__openLightbox('${imgUrl}','${fileName} — ${dets} detección(es)')">
        <div style="margin-top:8px;display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:12px;color:#444;">
            🔍 <b>${dets}</b> detección${dets !== 1 ? 'es' : ''}
          </span>
          <span style="font-size:11px;background:${src==='local'?'#e8f7f0':'#e8f0fe'};
                       color:${src==='local'?'#0F6E56':'#1a56c4'};
                       padding:2px 7px;border-radius:10px;">
            ${src === 'local' ? '📂 local' : '🖥️ servidor'}
          </span>
        </div>
        ${!tieneGPS ? `<div style="color:#ef4444;font-size:10.5px;margin-top:4px;text-align:center;">Ubicación por defecto (Falta .txt)</div>` : ''}
        <div style="margin-top:6px;text-align:center;">
          <a href="${imgUrl}" target="_blank"
             style="font-size:11.5px;color:#1D9E75;text-decoration:none;">
            Abrir imagen completa ↗
          </a>
        </div>
      </div>
    `;

    const marker = L.marker(latlng, { icon: svgIcon })
      .bindPopup(popupHtml, { maxWidth: 260, minWidth: 250 })
      .addTo(map);

    return marker;
  }

  // Exponer función al scope global para que el onclick del popup pueda accederla
  window.__openLightbox = openLightbox;

  // ── Batch (MODO DUMMY - PENÍNSULA VALDÉS FIJO) ─────────────────────────
  btnProc.addEventListener('click', async () => {
    cancelFlag = false;
    const total = filesImagen.length;

    btnProc.disabled = true;
    btnCancel.classList.add('visible');
    batchProgress.classList.add('visible');
    setStatus('loading', `<span class="spinner"></span> Viajando a Península Valdés (${total} imagen/es)…`);
    setProgress(0, total);

    let doneCount = 0, errorCount = 0, totalDets = 0;
    const markers = [];

    for (let i = 0; i < filesImagen.length; i++) {
      if (cancelFlag) {
        for (let j = i; j < filesImagen.length; j++) markChip(j, 'error', 'cancelada');
        break;
      }

      const f = filesImagen[i];
      markChip(i, 'active', '<span class="spinner"></span>');

      try {
        // Demora simulada de medio segundo
        await new Promise(resolve => setTimeout(resolve, 500));

        // 1. Ruta servida por tu Flask que equivale a C:\Users\Bruno\AppData\Local\Temp\yolo_results\11f08f8b\...
        const localImgUrl = "/results/11f08f8b/0a02e642__b0604f6e-_DSC2219.png";

        // 2. Coordenadas de Península Valdés + una dispersión diminuta para que no queden 100% apilados si subís varias
        const dummyLat = -42.5000 + (Math.random() - 0.5) * 0.05;
        const dummyLon = -63.9333 + (Math.random() - 0.5) * 0.05;
        
        // Simular que siempre detecta algo
        const randomDets = Math.floor(Math.random() * 5) + 1; 

        // 3. Estructura de respuesta forzada
        const data = {
          result_image_url: localImgUrl,
          total_detections: randomDets,
          model_source: 'dummy-valdes',
          gps: { lat: dummyLat, lon: dummyLon }
        };

        doneCount++;
        totalDets += data.total_detections;
        markChip(i, 'done', `✓ ${data.total_detections} det. (Valdés)`);

        // Dibujar marcador
        const marker = addMapMarker(data, f.name);
        if (marker) {
          markers.push(marker);
          // Centrar el mapa en el primero con un nivel de zoom 10 para ver la península entera
          if (markers.length === 1) map.setView([data.gps.lat, data.gps.lon], 10);
        }

      } catch (err) {
        errorCount++;
        markChip(i, 'error', `✗ Error local`);
      }

      setProgress(i + 1, total);
      setStatus('loading',
        `<span class="spinner"></span> ${i+1} / ${total} — ` +
        `${doneCount} ok${errorCount ? ', ' + errorCount + ' error(es)' : ''}`
      );
    }

    // Ajustar el bounding box si hay más de una foto
    if (markers.length > 1) {
      const group = L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.2));
    }

    btnCancel.classList.remove('visible');
    batchProgress.classList.remove('visible');

    if (cancelFlag) {
      setStatus('error', `⚠️ Simulación cancelada.`);
    } else {
      setStatus('success',
        `✅ <b>Modo Valdés:</b> ${doneCount} procesadas. ` +
        `Total detecciones: <b>${totalDets}</b>.`
      );
    }

    checkReady();
  });
  btnCancel.addEventListener('click', () => { cancelFlag = true; });

  // ── Helpers ───────────────────────────────────────────────────────────────
  function markChip(index, state, html) {
    const chip   = document.getElementById(`chip-${index}`);
    const status = document.getElementById(`chip-status-${index}`);
    if (chip)   chip.className   = `img-chip ${state}`;
    if (status) status.innerHTML = html;
  }

  function setProgress(done, total) {
    progressFill.style.width  = (total > 0 ? Math.round(done/total*100) : 0) + '%';
    progressLabel.textContent = `Procesando ${done} / ${total}`;
  }

  function setStatus(type, html) {
    statusBox.className = 'visible';
    if (type === 'error')   statusBox.classList.add('error');
    if (type === 'success') statusBox.classList.add('success');
    statusBox.innerHTML = html;
  }

})();