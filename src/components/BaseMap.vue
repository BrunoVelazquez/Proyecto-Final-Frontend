<script setup>
import { ref } from 'vue'

import ButtonComp from './ButtonComp.vue'
import FilterCard from './FilterCard.vue'
import MarkerInfoCard from './MarkerInfoCard.vue'
import EditorLightbox from './editor/EditorLightbox.vue'

import { useMap } from './composables/useMap'
import { useCategories } from './composables/useCategories'
import { useCampaign } from './composables/useCampaign'
import { useEditor } from './composables/useEditor'

// --- Referencias del DOM ---
const mapContainer = ref()

// --- Mapa ---
const { map, markersLayerGroup } = useMap(mapContainer)

// --- Categorías / colores ---
const { availableCategories, selectedCategories, getCategoryColor, extractCategories } =
  useCategories()

function getImageUrl(imageName) {
  return new URL(`../data/images/${imageName}`, import.meta.url).href
}

// --- Campaña (fetch + marcadores) ---
const {
  campaignLoaded,
  selectedFeature,
  loadCampaign,
  handleFilterChange,
  updateFeatureDetections,
  setOpenEditorCallback,
} = useCampaign(
  map,
  markersLayerGroup,
  { getCategoryColor, extractCategories, selectedCategories, availableCategories },
)

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

// Conectamos el popup del mapa con el editor
setOpenEditorCallback(openEditor)

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
    <div class="map-view-wrapper">
      <div ref="mapContainer" class="map-canvas"></div>

      <div class="fab-position-left">
        <ButtonComp
          label="Cargar campaña"
          variant="primary"
          class="pill-trigger-btn"
          @click="loadCampaign"
        />
      </div>

      <!-- Panel derecho: filtros + info del marcador seleccionado -->
      <div v-if="campaignLoaded" class="right-panel">
        <FilterCard
          :availableCategories="availableCategories"
          :selectedCategories="selectedCategories"
          :getCategoryColor="getCategoryColor"
          @change="onFilterChange"
        />
        <MarkerInfoCard
          :feature="selectedFeature"
          :getCategoryColor="getCategoryColor"
          :getImageUrl="getImageUrl"
          @openEditor="openEditor"
          @close="selectedFeature = null"
        />
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

.fab-position-left {
  position: absolute;
  bottom: 30px;
  left: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-panel {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 1000;
  width: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: calc(100vh - 40px);
  overflow-y: auto;
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
</style>
