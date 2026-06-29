<script setup>
import { ref } from 'vue'

import ButtonComp from './ButtonComp.vue'
import FilterCard from './FilterCard.vue'
import MarkerInfoCard from './MarkerInfoCard.vue'
import EditorLightbox from './editor/EditorLightbox.vue'
import OffsetCalibrator from './OffsetCalibrator.vue'

import { useMap } from './composables/useMap'
import { useCategories } from './composables/useCategories'
import { useCampaign } from './composables/useCampaign'
import { useEditor } from './composables/useEditor'
import { useTrajectory } from './composables/useTrajectory'
import { useCoastSnap } from './composables/useCoastSnap'

// --- Referencias del DOM ---
const mapContainer = ref()

// --- Mapa ---
const { map, markersLayerGroup } = useMap(mapContainer)

// --- Categorías / colores ---
const { availableCategories, selectedCategories, getCategoryColor, extractCategories } =
  useCategories()

function getImageUrl(imageName) {
  if (!imageName) return ''
  const apiUrl = import.meta.env.DEV ? '' : (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
  return `${apiUrl}/api/db/imagenes/${imageName}/`
}

// --- Campaña (fetch + marcadores) ---
const {
  geoJsonData,
  campaignLoaded,
  selectedFeature,
  unmappedFeatures,
  placementModeFeature,
  moveMarkerMode,
  moveMarkerTarget,
  loadCampaign,
  renderMarkers,
  handleFilterChange,
  updateFeatureDetections,
  showTrajectory,
  clearTrajectoryLayer,
  applyOffset,
  startMoveMarker,
  cancelMoveMarker,
} = useCampaign(
  map,
  markersLayerGroup,
  { getCategoryColor, extractCategories, selectedCategories, availableCategories, getImageUrl },
)

// --- Coast Snapping ---
const { snapStatus, snapMessage, snapAllToCoast, dismissSnap } = useCoastSnap()

function onSnapToCoast() {
  snapAllToCoast(geoJsonData, renderMarkers)
}

// --- Calibración de desfasaje GPS ---
const { trajectoryData, loadTrajectory, getPositionAtOffset } = useTrajectory()
const calibrationMode = ref(false)
const gpsFileInput = ref(null)

async function startCalibration() {
  gpsFileInput.value.click()
}

async function onGpsFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  event.target.value = '' // reset so same file can be re-selected
  await loadTrajectory(file)
  showTrajectory(trajectoryData.value)
  calibrationMode.value = true
  selectedFeature.value = null // ask user to pick a reference photo
}

function onApplyOffset(offsetSeconds) {
  applyOffset(offsetSeconds, trajectoryData.value)
  clearTrajectoryLayer()
  calibrationMode.value = false
}

function onCancelCalibration() {
  clearTrajectoryLayer()
  calibrationMode.value = false
}

// --- Editor canvas ---
const {
  currentEditingImage,
  currentImageFeatures,
  selectedBoxIndex,
  editorTool,
  saveStatus,
  showCharts,
  canUndo,
  canRedo,
  undo,
  redo,
  hiddenCategories,
  hiddenBoxes,
  allHidden,
  toggleAllBoxes,
  toggleCategory,
  toggleBoxVisibility,
  registerCanvasWrap,
  registerEditorCanvas,
  detectionStats,
  totalDetections,
  openEditor,
  closeEditor,
  zoomIn,
  zoomOut,
  zoomReset,
  zoomToBox,
  handleWheel,
  handleMouseDown,
  handleMouseMove,
  handleMouseUp,
  handleMouseLeave,
  removeBox,
  changeSelectedCategory,
  setOnSaveCallback,
  saveChanges,
} = useEditor({ getCategoryColor, availableCategories, getImageUrl })

// Cuando se guarda en el editor, escribe de vuelta al geoJSON y re-renderiza marcadores
setOnSaveCallback((imageName, detections) => {
  updateFeatureDetections(imageName, detections)
})

// --- Manejo de filtros (v-model manual sobre selectedCategories) ---
function onFilterChange(cat) {
  const idx = selectedCategories.value.indexOf(cat)
  if (idx >= 0) selectedCategories.value.splice(idx, 1)
  else selectedCategories.value.push(cat)
  handleFilterChange()
}
</script>

<template>
  <div class="app-container">
    <div class="map-view-wrapper" :class="{ 'placement-mode': !!placementModeFeature || moveMarkerMode }">
      <div ref="mapContainer" class="map-canvas"></div>

      <div class="fab-position-left">
        <ButtonComp
          v-if="campaignLoaded"
          label="Calibrar GPS"
          variant="primary"
          class="pill-trigger-btn pill-calibrate-btn"
          @click="startCalibration"
        />
        <ButtonComp
          v-if="campaignLoaded"
          label="Ajustar a Costa"
          variant="primary"
          class="pill-trigger-btn"
          :disabled="snapStatus === 'loading' || snapStatus === 'snapping'"
          @click="onSnapToCoast"
        />
        <ButtonComp
          label="Cargar campaña"
          variant="primary"
          class="pill-trigger-btn"
          @click="loadCampaign"
        />
        <!-- Hidden GPS file picker -->
        <input
          ref="gpsFileInput"
          type="file"
          accept=".txt,.csv"
          style="display: none"
          @change="onGpsFileSelected"
        />
      </div>

      <!-- Panel superior izquierdo: info del marcador seleccionado y calibrador -->
      <div v-if="campaignLoaded" class="top-left-panel">
        <MarkerInfoCard
          v-if="!calibrationMode"
          :feature="selectedFeature"
          :getCategoryColor="getCategoryColor"
          :getImageUrl="getImageUrl"
          @openEditor="openEditor"
          @moveMarker="startMoveMarker"
          @close="selectedFeature = null"
        />

        <!-- Calibrador de desfasaje GPS -->
        <OffsetCalibrator
          v-if="calibrationMode"
          :referenceFeature="selectedFeature"
          :getImageUrl="getImageUrl"
          :getPositionAtOffset="getPositionAtOffset"
          :map="map"
          @apply="onApplyOffset"
          @cancel="onCancelCalibration"
        />
      </div>

      <!-- Coast snap status banner -->
      <Transition name="snap-fade">
        <div v-if="snapStatus" class="snap-status-banner" :class="`snap-${snapStatus}`">
          <span v-if="snapStatus === 'loading' || snapStatus === 'snapping'" class="snap-spinner">⧗</span>
          <span>{{ snapMessage }}</span>
          <button v-if="snapStatus === 'error' || snapStatus === 'done'" class="move-cancel-btn" @click="dismissSnap">✕</button>
        </div>
      </Transition>

      <!-- Move marker mode banner -->
      <div v-if="moveMarkerMode" class="move-marker-banner">
        <span>📍 Haz click en el mapa para reubicar <b>{{ moveMarkerTarget?.properties?.image_name }}</b></span>
        <button class="move-cancel-btn" @click="cancelMoveMarker">✕ Cancelar</button>
      </div>

      <!-- Panel derecho: filtros y lista de no ubicados -->
      <div v-if="campaignLoaded" class="right-panel">
        <FilterCard
          :availableCategories="availableCategories"
          :selectedCategories="selectedCategories"
          :getCategoryColor="getCategoryColor"
          @change="onFilterChange"
        />

        <div v-if="unmappedFeatures.length > 0" class="unmapped-list-container">
          <div class="unmapped-header">
            <h4>Imágenes sin GPS ({{ unmappedFeatures.length }})</h4>
            <p v-if="placementModeFeature" class="placement-instruction">Haz click en el mapa para ubicar la imagen seleccionada.</p>
          </div>
          <div class="unmapped-list">
            <div v-for="feat in unmappedFeatures" :key="feat.properties.image_name"
                 class="unmapped-item"
                 :class="{ 'is-placing': placementModeFeature?.properties.image_name === feat.properties.image_name }">
              <img :src="getImageUrl(feat.properties.image_name)" alt="thumbnail" class="unmapped-thumb" />
              <div class="unmapped-info">
                <span class="unmapped-name">{{ feat.properties.image_name }}</span>
                <div class="unmapped-actions">
                  <button
                    v-if="placementModeFeature?.properties.image_name !== feat.properties.image_name"
                    class="btn-place"
                    @click.stop="placementModeFeature = feat"
                    :disabled="calibrationMode"
                  >
                    Ubicar en mapa
                  </button>
                  <button
                    v-else
                    class="btn-cancel-place"
                    @click.stop="placementModeFeature = null"
                  >
                    Cancelar
                  </button>
                  <button
                    class="btn-edit"
                    @click.stop="openEditor(feat.properties)"
                  >
                    Editar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <EditorLightbox
      :currentEditingImage="currentEditingImage"
      :currentImageFeatures="currentImageFeatures"
      :selectedBoxIndex="selectedBoxIndex"
      :editorTool="editorTool"
      :saveStatus="saveStatus"
      :showCharts="showCharts"
      :detectionStats="detectionStats"
      :totalDetections="totalDetections"
      :availableCategories="availableCategories"
      :getCategoryColor="getCategoryColor"
      :registerCanvasWrap="registerCanvasWrap"
      :registerEditorCanvas="registerEditorCanvas"
      :canUndo="canUndo"
      :canRedo="canRedo"
      :hiddenCategories="hiddenCategories"
      :hiddenBoxes="hiddenBoxes"
      :allHidden="allHidden"
      @close="closeEditor"
      @update:editorTool="editorTool = $event"
      @update:selectedBoxIndex="selectedBoxIndex = $event"
      @update:showCharts="showCharts = $event"
      @removeBox="removeBox"
      @changeCategory="changeSelectedCategory"
      @save="saveChanges"
      @undo="undo"
      @redo="redo"
      @toggleAllBoxes="toggleAllBoxes"
      @toggleCategory="toggleCategory"
      @toggleBoxVisibility="toggleBoxVisibility"
      @zoomIn="zoomIn"
      @zoomOut="zoomOut"
      @zoomReset="zoomReset"
      @zoomToBox="zoomToBox"
      @wheel="handleWheel"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseLeave"
    />
  </div>
</template>

<style scoped>
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
.placement-mode .map-canvas {
  cursor: crosshair !important;
}

/* Move marker mode banner */
.move-marker-banner {
  position: absolute;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1001;
  background: rgba(30, 20, 60, 0.92);
  color: white;
  padding: 12px 20px;
  border-radius: 50px;
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 13px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(4px);
  pointer-events: auto;
  white-space: nowrap;
}

.move-cancel-btn {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  color: white;
  padding: 5px 12px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.15s;
}
.move-cancel-btn:hover {
  background: rgba(231, 76, 60, 0.7);
}

/* Coast Snap Status Banner */
.snap-status-banner {
  position: absolute;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1002;
  padding: 10px 20px;
  border-radius: 50px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
  pointer-events: auto;
  white-space: nowrap;
  color: white;
}

.snap-loading, .snap-snapping {
  background: rgba(30, 20, 60, 0.9);
}
.snap-done {
  background: rgba(29, 158, 117, 0.92);
}
.snap-error {
  background: rgba(220, 53, 69, 0.92);
}

.snap-spinner {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.snap-fade-enter-active,
.snap-fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.snap-fade-enter-from,
.snap-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px);
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

.top-left-panel {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 1000;
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
}

.right-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  width: 300px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 40px);
  pointer-events: none;
}

.right-panel > * {
  pointer-events: auto;
}

/* UI no ubicados */
.unmapped-list-container {
  background: white;
  border-radius: 8px;
  padding: 12px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 400px;
}

.unmapped-header h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  color: #2c3e50;
}

.placement-instruction {
  margin: 0;
  font-size: 12px;
  color: #e67e22;
  font-weight: bold;
}

.unmapped-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
}

.unmapped-item {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 6px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid transparent;
}

.unmapped-item.is-placing {
  border-color: #e67e22;
  background: #fff3e0;
}

.unmapped-thumb {
  width: 40px;
  height: 40px;
  object-fit: cover;
  border-radius: 4px;
}

.unmapped-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 4px;
}

.unmapped-name {
  font-size: 11px;
  word-break: break-all;
  color: #555;
}

.btn-place {
  background: #3498db;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  align-self: flex-start;
  transition: background 0.2s;
}

.btn-place:hover:not(:disabled) {
  background: #2980b9;
}

.btn-place:disabled {
  background: #bdc3c7;
  cursor: not-allowed;
}

.btn-cancel-place {
  background: #e74c3c;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  align-self: flex-start;
  transition: background 0.2s;
}

.btn-cancel-place:hover {
  background: #c0392b;
}

.unmapped-item.is-placing {
  border-color: #e67e22;
  background: #fff3e0;
}

.unmapped-actions {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.btn-edit {
  background: #9b59b6;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  align-self: flex-start;
  transition: background 0.2s;
}

.btn-edit:hover {
  background: #8e44ad;
}

.pill-trigger-btn :deep(button) {
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
.pill-trigger-btn :deep(button:hover) {
  background-color: #f8f8f8;
  transform: translateY(-2px);
}

.pill-calibrate-btn :deep(button) {
  background-color: #0f3460;
  color: #90cdf4;
}
.pill-calibrate-btn :deep(button:hover) {
  background-color: #1a4a7a;
  color: #bee3f8;
}

/* Alineación de controles en la esquina inferior derecha */
:deep(.leaflet-bottom.leaflet-right) {
  display: grid !important;
  grid-template-columns: 1fr auto auto;
  grid-template-rows: auto auto;
  column-gap: 5px;
  row-gap: 8px;
  align-items: end;
  justify-items: end;
  padding-right: 10px;
  padding-bottom: 10px;
  pointer-events: none;
}
:deep(.leaflet-bottom.leaflet-right .leaflet-control) {
  margin: 0 !important;
  clear: none !important;
  pointer-events: auto;
}
:deep(.leaflet-control-layers) {
  grid-column: 2;
  grid-row: 1;
}
:deep(.leaflet-control-zoom) {
  grid-column: 3;
  grid-row: 1;
}
:deep(.leaflet-control-attribution) {
  grid-column: 1 / span 3;
  grid-row: 2;
}
</style>
