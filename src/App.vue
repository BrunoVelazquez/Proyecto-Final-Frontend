<script setup>
import { onMounted, ref, nextTick, watch, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// --- Configuración de API ---
const API_BASE_URL = 'http://127.0.0.1:8000'

// --- Estados del Mapa ---
const map = ref()
const mapContainer = ref()
const geoJsonData = ref(null)
const campaignLoaded = ref(false)
const markersLayerGroup = ref(L.layerGroup())

// --- Estados de Filtros ---
const availableCategories = ref([])
const selectedCategories = ref([])

// --- Estados del Editor Canvas ---
const currentEditingImage = ref(null)
const currentImageFeatures = ref([])
const selectedBoxIndex = ref(-1)
const editorTool = ref('select')
const saveStatus = ref('') // Status message for save

// Referencias del DOM para el Canvas
const canvasWrap = ref(null)
const editorCanvas = ref(null)
let ctx = null
let imgObj = null
let imgNat = { w: 1, h: 1 }

// Variables de vista de la cámara del Canvas
const scale = ref(1)
const panX = ref(0)
const panY = ref(0)

// Estados de interacción del ratón
const hoveredIdx = ref(-1)
const drag = { active: false, type: null, idx: -1, sx: 0, sy: 0, ox: 0, oy: 0, obox: [] }
const drawing = { active: false, sx: 0, sy: 0, ex: 0, ey: 0 }

// Estado para mostrar/ocultar gráficos
const showCharts = ref(false)

// --- Lógica de Colores ---
const CLASS_COLORS = [
  '#FF6B6B',
  '#4ECDC4',
  '#45B7D1',
  '#96CEB4',
  '#FFEAA7',
  '#DDA0DD',
  '#98D8C8',
  '#F7DC6F',
  '#BB8FCE',
  '#85C1E9',
  '#F1948A',
  '#82E0AA',
  '#F8C471',
  '#AED6F1',
  '#A9DFBF',
]
const categoryColorMap = ref({})
let nextColorIndex = 0

function getCategoryColor(category) {
  if (!categoryColorMap.value[category]) {
    categoryColorMap.value[category] = CLASS_COLORS[nextColorIndex % CLASS_COLORS.length]
    nextColorIndex++
  }
  return categoryColorMap.value[category]
}

function getImageUrl(imageName) {
  return new URL(`../data/images/${imageName}`, import.meta.url).href
}

onMounted(() => {
  map.value = L.map(mapContainer.value, { zoomControl: true }).setView([-42.15, -64.15], 11)
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  }).addTo(map.value)

  markersLayerGroup.value.addTo(map.value)
  setTimeout(() => {
    if (map.value) map.value.invalidateSize()
  }, 200)
})

// --- CARGA Y RENDERIZADO DEL MAPA ---
async function loadCampaign() {
  try {
    const response = await fetch(`${API_BASE_URL}/dummy`)
    const data = await response.json()
    geoJsonData.value = data

    const categoriesSet = new Set()
    data.features.forEach((f) => {
      if (f.properties.detections) {
        f.properties.detections.forEach((d) => categoriesSet.add(d.category))
      }
    })
    availableCategories.value = Array.from(categoriesSet)
    selectedCategories.value = [...availableCategories.value]

    campaignLoaded.value = true
    renderMarkers()

    nextTick(() => {
      map.value.invalidateSize()
      const dummyLayer = L.geoJSON(data)
      if (data.features.length > 0) {
        map.value.fitBounds(dummyLayer.getBounds(), { padding: [50, 50] })
      }
    })
  } catch (error) {
    console.error('Error al conectar con la API:', error)
  }
}

// Genera un popup flotante
function createPopupContent(props, summary) {
  let listItemsHtml = Object.entries(summary)
    .map(
      ([cat, count]) =>
        `<li><span class="dot" style="background:${getCategoryColor(cat)}"></span> <b>${cat}:</b> ${count}</li>`,
    )
    .join('')

  const container = document.createElement('div')
  container.className = 'custom-map-popup'
  container.innerHTML = `
    <h4>${props.image_name}</h4>
    <div class="popup-image-frame">
      <img src="${getImageUrl(props.image_name)}" alt="Cargando..." class="popup-preview-img" />
    </div>
    <p class="popup-total">Total detectados: <b>${props.total_detections}</b></p>
    <ul class="popup-classes-list">${listItemsHtml}</ul>
  `
  const btn = document.createElement('button')
  btn.className = 'popup-action-btn'
  btn.innerText = '🔍 Abrir editor'
  btn.onclick = () => {
    map.value.closePopup()
    openEditor(props)
  }
  container.appendChild(btn)
  return container
}

function renderMarkers() {
  if (!geoJsonData.value) return
  markersLayerGroup.value.clearLayers()

  geoJsonData.value.features.forEach((feature) => {
    const props = feature.properties
    if (!props.detections || props.detections.length === 0) return

    const countByClass = {}
    props.detections.forEach((d) => {
      if (selectedCategories.value.includes(d.category)) {
        countByClass[d.category] = (countByClass[d.category] || 0) + 1
      }
    })

    const activeClasses = Object.keys(countByClass)
    if (activeClasses.length === 0) return

    activeClasses.sort((a, b) => countByClass[b] - countByClass[a])

    const [lon, lat] = feature.geometry.coordinates
    const popupFactory = () => createPopupContent(props, countByClass)

    activeClasses.forEach((cat) => {
      const count = countByClass[cat]
      const radius = Math.max(8, Math.min(30, Math.sqrt(count) * 4.5))
      const color = getCategoryColor(cat)

      const marker = L.circleMarker([lat, lon], {
        color: color,
        fillColor: color,
        fillOpacity: 0.25,
        opacity: 0.8,
        weight: 2,
        radius: radius,
      })

      marker.bindPopup(popupFactory, { minWidth: 220, maxWidth: 240 })
      markersLayerGroup.value.addLayer(marker)
    })
  })
}

function handleFilterChange() {
  renderMarkers()
}

// ═══════════════════════════════════════════════════════
//  LÓGICA DEL CANVAS EDITOR
// ═══════════════════════════════════════════════════════

function openEditor(properties) {
  currentEditingImage.value = properties.image_name
  currentImageFeatures.value = JSON.parse(JSON.stringify(properties.detections))
  selectedBoxIndex.value = -1
  editorTool.value = 'select'
  saveStatus.value = ''
  showCharts.value = false

  nextTick(() => {
    if (!editorCanvas.value) return
    ctx = editorCanvas.value.getContext('2d')
    imgObj = new Image()
    imgObj.onload = () => {
      imgNat.w = imgObj.naturalWidth
      imgNat.h = imgObj.naturalHeight
      fitImage()
      renderCanvas()
    }
    imgObj.src = getImageUrl(properties.image_name)
  })
}

function fitImage() {
  if (!canvasWrap.value || !editorCanvas.value) return
  const W = canvasWrap.value.clientWidth
  const H = canvasWrap.value.clientHeight
  editorCanvas.value.width = W
  editorCanvas.value.height = H

  const scaleX = W / imgNat.w
  const scaleY = H / imgNat.h
  scale.value = Math.min(scaleX, scaleY) * 0.92
  panX.value = (W - imgNat.w * scale.value) / 2
  panY.value = (H - imgNat.h * scale.value) / 2
}

const absToCanvas = (x, y) => ({ x: x * scale.value + panX.value, y: y * scale.value + panY.value })
const canvasToAbs = (cx, cy) => ({
  x: (cx - panX.value) / scale.value,
  y: (cy - panY.value) / scale.value,
})

function renderCanvas() {
  if (!ctx || !imgObj || !editorCanvas.value) {
    return
  }
  const W = editorCanvas.value.width
  const H = editorCanvas.value.height
  ctx.clearRect(0, 0, W, H)

  ctx.drawImage(imgObj, panX.value, panY.value, imgNat.w * scale.value, imgNat.h * scale.value)

  currentImageFeatures.value.forEach((b, i) => {
    const color = getCategoryColor(b.category)
    const [xmin, ymin, xmax, ymax] = b.bbox

    const tl = absToCanvas(xmin, ymin)
    const br = absToCanvas(xmax, ymax)
    const bw = br.x - tl.x
    const bh = br.y - tl.y

    const isHovered = i === hoveredIdx.value
    const isSelected = i === selectedBoxIndex.value

    if (isSelected) {
      ctx.fillStyle = color + '22'
      ctx.fillRect(tl.x, tl.y, bw, bh)
    }

    ctx.strokeStyle = color
    ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.5
    ctx.strokeRect(tl.x, tl.y, bw, bh)

    const label = b.category
    ctx.font = '11px system-ui'
    const tw = ctx.measureText(label).width
    ctx.fillStyle = color + 'cc'
    ctx.fillRect(tl.x, tl.y - 16, tw + 6, 16)
    ctx.fillStyle = '#000'
    ctx.fillText(label, tl.x + 3, tl.y - 3)

    if (isSelected) drawHandles(tl.x, tl.y, bw, bh, color)
  })

  if (drawing.active) {
    ctx.strokeStyle = '#1D9E75'
    ctx.lineWidth = 2
    ctx.setLineDash([5, 3])
    ctx.strokeRect(
      Math.min(drawing.sx, drawing.ex),
      Math.min(drawing.sy, drawing.ey),
      Math.abs(drawing.ex - drawing.sx),
      Math.abs(drawing.ey - drawing.sy),
    )
    ctx.setLineDash([])
  }
}

function drawHandles(x, y, w, h, color) {
  const pts = [
    [x, y],
    [x + w / 2, y],
    [x + w, y],
    [x, y + h / 2],
    [x + w, y + h / 2],
    [x, y + h],
    [x + w / 2, y + h],
    [x + w, y + h],
  ]
  pts.forEach(([hx, hy]) => {
    ctx.fillStyle = color
    ctx.fillRect(hx - 4, hy - 4, 8, 8)
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 1
    ctx.strokeRect(hx - 4, hy - 4, 8, 8)
  })
}

watch([selectedBoxIndex, currentImageFeatures], () => renderCanvas(), { deep: true })

function getMousePos(e) {
  const rect = editorCanvas.value.getBoundingClientRect()
  return { cx: e.clientX - rect.left, cy: e.clientY - rect.top }
}

function handleWheel(e) {
  const { cx, cy } = getMousePos(e)
  const factor = e.deltaY < 0 ? 1.12 : 0.89
  panX.value = cx - (cx - panX.value) * factor
  panY.value = cy - (cy - panY.value) * factor
  scale.value *= factor
  renderCanvas()
}

function handleMouseDown(e) {
  const { cx, cy } = getMousePos(e)

  if (editorTool.value === 'draw') {
    drawing.active = true
    drawing.sx = cx
    drawing.sy = cy
    drawing.ex = cx
    drawing.ey = cy
    return
  }

  if (selectedBoxIndex.value >= 0) {
    const h = hitHandle(cx, cy, selectedBoxIndex.value)
    if (h) {
      const bbox = currentImageFeatures.value[selectedBoxIndex.value].bbox
      drag.active = true
      drag.type = 'resize'
      drag.idx = selectedBoxIndex.value
      drag.handle = h
      drag.sx = cx
      drag.sy = cy
      drag.obox = [...bbox]
      return
    }
  }

  const hit = hitBox(cx, cy)
  if (hit >= 0) {
    selectedBoxIndex.value = hit
    const bbox = currentImageFeatures.value[hit].bbox
    drag.active = true
    drag.type = 'move'
    drag.idx = hit
    drag.sx = cx
    drag.sy = cy
    drag.obox = [...bbox]
    renderCanvas()
    return
  }

  selectedBoxIndex.value = -1
  drag.active = true
  drag.type = 'pan'
  drag.sx = cx
  drag.sy = cy
  drag.ox = panX.value
  drag.oy = panY.value
  renderCanvas()
}

function handleMouseMove(e) {
  const { cx, cy } = getMousePos(e)

  if (drawing.active) {
    drawing.ex = cx
    drawing.ey = cy
    renderCanvas()
    return
  }

  if (drag.active) {
    const dx = cx - drag.sx
    const dy = cy - drag.sy
    const dxAbs = dx / scale.value
    const dyAbs = dy / scale.value

    if (drag.type === 'pan') {
      panX.value = drag.ox + dx
      panY.value = drag.oy + dy
    } else if (drag.type === 'move') {
      const b = currentImageFeatures.value[drag.idx].bbox
      b[0] = drag.obox[0] + dxAbs
      b[1] = drag.obox[1] + dyAbs
      b[2] = drag.obox[2] + dxAbs
      b[3] = drag.obox[3] + dyAbs
    } else if (drag.type === 'resize') {
      let [xmin, ymin, xmax, ymax] = drag.obox
      if (drag.handle.includes('l')) xmin = Math.min(xmax - 1, drag.obox[0] + dxAbs)
      if (drag.handle.includes('r')) xmax = Math.max(xmin + 1, drag.obox[2] + dxAbs)
      if (drag.handle.includes('t')) ymin = Math.min(ymax - 1, drag.obox[1] + dyAbs)
      if (drag.handle.includes('b')) ymax = Math.max(ymin + 1, drag.obox[3] + dyAbs)
      currentImageFeatures.value[drag.idx].bbox = [xmin, ymin, xmax, ymax]
    }
    renderCanvas()
    return
  }

  const newHover = hitBox(cx, cy)
  if (newHover !== hoveredIdx.value) {
    hoveredIdx.value = newHover
    renderCanvas()
  }
  canvasWrap.value.style.cursor =
    editorTool.value === 'draw' ? 'crosshair' : newHover >= 0 ? 'pointer' : 'default'
}

function handleMouseUp(e) {
  if (drawing.active) {
    const { cx, cy } = getMousePos(e)
    if (Math.abs(cx - drawing.sx) > 8 && Math.abs(cy - drawing.sy) > 8) {
      const p1 = canvasToAbs(drawing.sx, drawing.sy)
      const p2 = canvasToAbs(cx, cy)
      const xmin = Math.min(p1.x, p2.x)
      const ymin = Math.min(p1.y, p2.y)
      const xmax = Math.max(p1.x, p2.x)
      const ymax = Math.max(p1.y, p2.y)

      const cat = availableCategories.value[0] || 'default'
      currentImageFeatures.value.push({ category: cat, score: 1.0, bbox: [xmin, ymin, xmax, ymax] })
      selectedBoxIndex.value = currentImageFeatures.value.length - 1
      editorTool.value = 'select'
    }
  }
  drag.active = false
  drawing.active = false
  renderCanvas()
}

function handleMouseLeave() {
  drag.active = false
  drawing.active = false
  hoveredIdx.value = -1
  renderCanvas()
}

function hitBox(cx, cy) {
  for (let i = currentImageFeatures.value.length - 1; i >= 0; i--) {
    const [xmin, ymin, xmax, ymax] = currentImageFeatures.value[i].bbox
    const tl = absToCanvas(xmin, ymin)
    const br = absToCanvas(xmax, ymax)
    if (cx >= tl.x && cx <= br.x && cy >= tl.y && cy <= br.y) return i
  }
  return -1
}

const HANDLE_NAMES = ['tl', 'tc', 'tr', 'ml', 'mr', 'bl', 'bc', 'br']
function hitHandle(cx, cy, idx) {
  const [xmin, ymin, xmax, ymax] = currentImageFeatures.value[idx].bbox
  const tl = absToCanvas(xmin, ymin)
  const br = absToCanvas(xmax, ymax)
  const pts = [
    [tl.x, tl.y],
    [(tl.x + br.x) / 2, tl.y],
    [br.x, tl.y],
    [tl.x, (tl.y + br.y) / 2],
    [br.x, (tl.y + br.y) / 2],
    [tl.x, br.y],
    [(tl.x + br.x) / 2, br.y],
    [br.x, br.y],
  ]
  for (let i = 0; i < pts.length; i++) {
    if (Math.abs(cx - pts[i][0]) < 7 && Math.abs(cy - pts[i][1]) < 7) return HANDLE_NAMES[i]
  }
  return null
}

function removeBox(index) {
  currentImageFeatures.value.splice(index, 1)
  if (selectedBoxIndex.value === index) selectedBoxIndex.value = -1
  else if (selectedBoxIndex.value > index) selectedBoxIndex.value--
}

function closeEditor() {
  currentEditingImage.value = null

  ctx = null
  imgObj = null

  selectedBoxIndex.value = -1
  hoveredIdx.value = -1

  showCharts.value = false
}

// ── Computed para estadísticas de detección ──
const detectionStats = computed(() => {
  const stats = {}
  currentImageFeatures.value.forEach((b) => {
    stats[b.category] = (stats[b.category] || 0) + 1
  })
  return Object.entries(stats)
    .map(([cat, count]) => ({
      category: cat,
      count: count,
      color: getCategoryColor(cat),
    }))
    .sort((a, b) => b.count - a.count)
})

const totalDetections = computed(() => currentImageFeatures.value.length)

// ── Guardar cambios (no cierra el modal) ──
async function saveChanges() {
  saveStatus.value = 'Guardando...'
  try {
    // Simulación de guardado - reemplazar con tu endpoint real
    // const response = await fetch(`${API_BASE_URL}/save`, {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({
    //     image: currentEditingImage.value,
    //     detections: currentImageFeatures.value
    //   })
    // })
    // const data = await response.json()

    // Simulación:
    await new Promise((r) => setTimeout(r, 500))
    saveStatus.value = `✅ ${currentImageFeatures.value.length} detecciones guardadas`
    setTimeout(() => {
      saveStatus.value = ''
    }, 3000)
  } catch (error) {
    saveStatus.value = '❌ Error al guardar'
    console.error(error)
  }
}

// ── Cambiar categoría del objeto seleccionado ──
function changeSelectedCategory(newCat) {
  if (selectedBoxIndex.value >= 0 && currentImageFeatures.value[selectedBoxIndex.value]) {
    currentImageFeatures.value[selectedBoxIndex.value].category = newCat
  }
}
</script>

<template>
  <div class="app-container">
    <div class="map-view-wrapper">
      <div ref="mapContainer" class="map-canvas"></div>

      <div class="fab-position-left">
        <button class="pill-trigger-btn" @click="loadCampaign">Cargar campaña</button>
      </div>

      <div v-if="campaignLoaded" class="floating-filter-card">
        <h4>Filtros de Campaña</h4>
        <div class="filter-scroll-area">
          <div v-for="cat in availableCategories" :key="cat" class="checkbox-row">
            <input
              type="checkbox"
              :id="'filter-' + cat"
              :value="cat"
              v-model="selectedCategories"
              @change="handleFilterChange"
            />
            <span
              class="legend-color-dot"
              :style="{ backgroundColor: getCategoryColor(cat) }"
            ></span>
            <label :for="'filter-' + cat">{{ cat }}</label>
          </div>
        </div>
        <div class="card-footer-stats">Categorías activas: {{ selectedCategories.length }}</div>
      </div>
    </div>

    <!-- ═══════════════════════════════════════════════════════ -->
    <!--  LIGHTBOX EDITOR - Estilo como la imagen                  -->
    <!-- ═══════════════════════════════════════════════════════ -->
    <div v-if="currentEditingImage" class="lb-overlay" @mousedown="closeEditor">
      <div class="lb-panel">
        <div class="lb-header">
          <span class="lb-title">{{ currentEditingImage }}</span>
          <button class="lb-close" @click="currentEditingImage = null">✕</button>
        </div>

        <div class="lb-body">
          <div
            class="lb-canvas-wrap"
            ref="canvasWrap"
            @wheel.prevent="handleWheel"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseLeave"
          >
            <canvas ref="editorCanvas"></canvas>
          </div>

          <div class="lb-sidebar">
            <h4>Editor de detecciones</h4>

            <!-- Herramientas -->
            <div class="lb-tools">
              <!-- <button
                class="lb-tool-btn"
                :class="{ active: editorTool === 'select' }"
                @click="editorTool = 'select'"
              >✦ Sel</button> -->
              <button
                class="lb-tool-btn"
                :class="{ active: editorTool === 'draw' }"
                @click="editorTool = 'draw'"
              >
                ✏ Crear
              </button>
              <button
                class="lb-tool-btn lb-tool-btn-delete"
                @click="removeBox(selectedBoxIndex)"
                :disabled="selectedBoxIndex < 0"
              >
                🗑 Borrar
              </button>
            </div>

            <!-- Cambiar a - UN SOLO DESPLEGABLE -->
            <div class="lb-change-section">
              <label class="lb-change-label">Cambiar a</label>
              <select
                class="lb-class-select"
                :value="
                  selectedBoxIndex >= 0 ? currentImageFeatures[selectedBoxIndex]?.category : ''
                "
                @change="(e) => changeSelectedCategory(e.target.value)"
                :disabled="selectedBoxIndex < 0"
              >
                <option v-for="cat in availableCategories" :key="cat" :value="cat">
                  {{ cat }}
                </option>
              </select>
            </div>

            <!-- Lista de objetos encontrados -->
            <div class="lb-section-title">Objetos encontrados</div>
            <div class="lb-box-list">
              <div
                v-for="(box, index) in currentImageFeatures"
                :key="index"
                class="lb-box-item"
                :class="{ selected: selectedBoxIndex === index }"
                @click="selectedBoxIndex = index"
              >
                <div
                  class="lb-box-dot"
                  :style="{ background: getCategoryColor(box.category) }"
                ></div>
                <span class="lb-box-label">{{ box.category }}</span>
              </div>
            </div>

            <!-- Botón de gráficos -->
            <button class="lb-chart-btn" @click="showCharts = !showCharts">
              📊 {{ showCharts ? 'Ocultar' : 'Ver' }} conteo
            </button>

            <!-- Panel de gráficos -->
            <div v-if="showCharts" class="lb-charts-panel">
              <div class="lb-chart-header">
                Total: <b>{{ totalDetections }}</b> detecciones
              </div>
              <div class="lb-chart-bars">
                <div v-for="stat in detectionStats" :key="stat.category" class="lb-chart-row">
                  <div class="lb-chart-label">{{ stat.category }}</div>
                  <div class="lb-chart-bar-wrap">
                    <div
                      class="lb-chart-bar"
                      :style="{
                        width:
                          totalDetections > 0 ? (stat.count / totalDetections) * 100 + '%' : '0%',
                        backgroundColor: stat.color,
                      }"
                    ></div>
                  </div>
                  <div class="lb-chart-count">{{ stat.count }}</div>
                </div>
              </div>
            </div>

            <!-- Guardar -->
            <button class="lb-save-btn" @click="saveChanges">💾 Guardar</button>

            <!-- Status de guardado -->
            <div v-if="saveStatus" class="lb-status" :class="{ error: saveStatus.includes('❌') }">
              {{ saveStatus }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* ═══════════════════════════════════════════════════════ */
/*  ESTILOS POPUPS                                        */
/* ═══════════════════════════════════════════════════════ */
.custom-map-popup h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-family: monospace;
  color: #333;
  word-break: break-all;
}
.popup-image-frame {
  width: 100%;
  height: 110px;
  background: #eaeaea;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 8px;
  border: 1px solid #ddd;
}
.popup-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.popup-total {
  font-size: 12px;
  margin: 4px 0;
  color: #555;
}
.popup-classes-list {
  list-style: none;
  padding: 0;
  margin: 6px 0;
  max-height: 80px;
  overflow-y: auto;
  font-size: 11px;
}
.popup-classes-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}
.popup-classes-list .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.popup-action-btn {
  background-color: #1d9e75;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 0;
  width: 100%;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 5px;
}
.popup-action-btn:hover {
  background-color: #178a64;
}
</style>

<style scoped>
/* ═══════════════════════════════════════════════════════ */
/*  APP CONTAINER - MAPA LLENO                            */
/* ═══════════════════════════════════════════════════════ */
.app-container {
  position: fixed;
  inset: 0;
  overflow: hidden;
}

.map-view-wrapper {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
}
.map-canvas {
  width: 100%;
  height: 100%;
}

.fab-position-left {
  position: absolute;
  bottom: 30px;
  left: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.pill-trigger-btn {
  background-color: white;
  color: #5b5394;
  border: none;
  border-radius: 50px;
  padding: 14px 26px;
  font-weight: bold;
  font-size: 14px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2);
  cursor: pointer;
  transition: all 0.2s;
}
.pill-trigger-btn:hover {
  background-color: #f8f8f8;
  transform: translateY(-2px);
}

.floating-filter-card {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 260px;
  max-height: 400px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  z-index: 1000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
}
.floating-filter-card h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  color: #303133;
  border-bottom: 2px solid #5b5394;
  padding-bottom: 6px;
}
.filter-scroll-area {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #606266;
}
.checkbox-row input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
.legend-color-dot {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  flex-shrink: 0;
}
.card-footer-stats {
  margin-top: 12px;
  font-size: 11px;
  color: #909399;
  text-align: right;
  border-top: 1px solid #f2f6fc;
  padding-top: 6px;
}

/* ═══════════════════════════════════════════════════════ */
/*  OVERLAY LIGHTBOX - Estilo imagen                       */
/* ═══════════════════════════════════════════════════════ */
.lb-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(0, 0, 0, 0.82);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.lb-panel {
  background: #1a1a2e;
  border-radius: 14px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.6);
  display: flex;
  flex-direction: column;
  width: 92vw;
  max-width: 1100px;
  height: 88vh;
  overflow: hidden;
}

.lb-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #16213e;
  border-bottom: 1px solid #0f3460;
  flex-shrink: 0;
}
.lb-title {
  flex: 1;
  font-size: 14px;
  color: #a0aec0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
}
.lb-close {
  background: #e53e3e;
  border: none;
  color: white;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.lb-close:hover {
  background: #c53030;
}

.lb-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
.lb-canvas-wrap {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #111;
  cursor: default;
}
canvas {
  display: block;
  width: 100%;
  height: 100%;
}

/* ═══════════════════════════════════════════════════════ */
/*  SIDEBAR - Estilo como la imagen                        */
/* ═══════════════════════════════════════════════════════ */
.lb-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #16213e;
  border-left: 1px solid #0f3460;
  display: flex;
  flex-direction: column;
  color: #cbd5e0;
  overflow: hidden;
}
.lb-sidebar h4 {
  padding: 12px;
  margin: 0;
  font-size: 14px;
  background: #0f3460;
  color: #90cdf4;
  border-bottom: 1px solid #2d3748;
}

/* Herramientas */
.lb-tools {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  flex-wrap: wrap;
}
.lb-tool-btn {
  padding: 6px 12px;
  border: 1px solid #4a5568;
  border-radius: 6px;
  background: #2d3748;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
  flex: 1;
  min-width: 0;
}
.lb-tool-btn:hover,
.lb-tool-btn.active {
  background: #1d9e75;
  border-color: #1d9e75;
  color: white;
}
.lb-tool-btn-delete {
  background: #4a1f1f;
  border-color: #e53e3e;
  color: #fc8181;
}
.lb-tool-btn-delete:hover {
  background: #e53e3e;
  color: white;
}
.lb-tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Cambiar a - UN SOLO DESPLEGABLE */
.lb-change-section {
  padding: 8px 12px;
  border-bottom: 1px solid #2d3748;
}
.lb-change-label {
  display: block;
  font-size: 11px;
  color: #a0aec0;
  margin-bottom: 4px;
}
.lb-class-select {
  width: 100%;
  background: #1a202c;
  border: 1px solid #4a5568;
  color: #e2e8f0;
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 12px;
  cursor: pointer;
}
.lb-class-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Título de sección */
.lb-section-title {
  padding: 8px 12px 4px;
  font-size: 12px;
  font-weight: 600;
  color: #90cdf4;
  border-bottom: 1px solid #2d3748;
}

/* Lista de objetos encontrados */
.lb-box-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lb-box-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  background: #2d3748;
  cursor: pointer;
  transition: background 0.1s;
}
.lb-box-item:hover {
  background: #3c4a63;
}
.lb-box-item.selected {
  background: #2b4a6f;
  box-shadow: inset 0 0 0 1px #90cdf4;
}
.lb-box-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex-shrink: 0;
}
.lb-box-label {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}

/* Botón de gráficos */
.lb-chart-btn {
  margin: 8px 12px 0;
  padding: 8px;
  border: 1px solid #4a5568;
  border-radius: 6px;
  background: #2d3748;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
  text-align: center;
}
.lb-chart-btn:hover {
  background: #3c4a63;
  border-color: #90cdf4;
}

/* Panel de gráficos */
.lb-charts-panel {
  margin: 8px 12px;
  padding: 10px;
  background: #1a202c;
  border-radius: 8px;
  border: 1px solid #2d3748;
}
.lb-chart-header {
  font-size: 12px;
  color: #a0aec0;
  margin-bottom: 8px;
  text-align: center;
  padding-bottom: 6px;
  border-bottom: 1px solid #2d3748;
}
.lb-chart-bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.lb-chart-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.lb-chart-label {
  font-size: 10px;
  color: #cbd5e0;
  width: 60px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
}
.lb-chart-bar-wrap {
  flex: 1;
  height: 14px;
  background: #2d3748;
  border-radius: 3px;
  overflow: hidden;
}
.lb-chart-bar {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}
.lb-chart-count {
  font-size: 11px;
  color: #90cdf4;
  font-weight: bold;
  width: 20px;
  text-align: right;
  flex-shrink: 0;
}

/* Botón Guardar */
.lb-save-btn {
  margin: 8px 12px 4px;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: #1d9e75;
  color: white;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.15s;
}
.lb-save-btn:hover {
  background: #178a64;
}

/* Status */
.lb-status {
  margin: 0 12px 8px;
  padding: 6px;
  font-size: 11px;
  color: #68d391;
  text-align: center;
  min-height: 22px;
}
.lb-status.error {
  color: #fc8181;
}
</style>
