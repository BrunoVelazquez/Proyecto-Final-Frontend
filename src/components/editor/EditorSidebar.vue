<script setup>
import { computed } from 'vue'
import ButtonComp from '../ButtonComp.vue'

const props = defineProps({
  editorTool: { type: String, required: true },
  selectedBoxIndex: { type: Number, required: true },
  currentImageFeatures: { type: Array, required: true },
  availableCategories: { type: Array, required: true },
  getCategoryColor: { type: Function, required: true },
  showCharts: { type: Boolean, required: true },
  detectionStats: { type: Array, required: true },
  totalDetections: { type: Number, required: true },
  saveStatus: { type: String, default: '' },
  // Undo / redo
  canUndo: { type: Boolean, default: false },
  canRedo: { type: Boolean, default: false },
  // Visibilidad
  hiddenCategories: { type: Object, default: () => new Set() },
  hiddenBoxes: { type: Object, default: () => new Set() },
  allHidden: { type: Boolean, default: false },
})

defineEmits([
  'update:editorTool',
  'update:selectedBoxIndex',
  'update:showCharts',
  'removeBox',
  'changeCategory',
  'save',
  'undo',
  'redo',
  'toggleAllBoxes',
  'toggleCategory',
  'toggleBoxVisibility',
  'zoomToBox',
])

const groupedFeatures = computed(() => {
  const groups = {}
  props.availableCategories.forEach(cat => { groups[cat] = [] })
  props.currentImageFeatures.forEach((box, index) => {
    if (!groups[box.category]) groups[box.category] = []
    groups[box.category].push({ box, index })
  })
  return groups
})
</script>

<template>
  <div class="lb-sidebar">
    <h4>Editor de detecciones</h4>

    <div class="lb-sidebar-scroll">
      <!-- Herramientas principales -->
      <div class="lb-tools">
        <ButtonComp
          class="lb-tool-btn"
          :class="{ active: editorTool === 'draw' }"
          @click="$emit('update:editorTool', 'draw')"
        >
          ✏ Crear
        </ButtonComp>
        <ButtonComp
          class="lb-tool-btn lb-tool-btn-delete"
          @click="$emit('removeBox', selectedBoxIndex)"
          :disabled="selectedBoxIndex < 0"
        >
          🗑 Borrar
        </ButtonComp>
      </div>

      <!-- Undo / Redo -->
      <div class="lb-tools lb-tools-undo">
        <ButtonComp
          class="lb-tool-btn"
          :disabled="!canUndo"
          @click="$emit('undo')"
          title="Deshacer (Ctrl+Z)"
        >
          ↩ Deshacer
        </ButtonComp>
        <ButtonComp
          class="lb-tool-btn"
          :disabled="!canRedo"
          @click="$emit('redo')"
          title="Rehacer (Ctrl+Y)"
        >
          ↪ Rehacer
        </ButtonComp>
      </div>

      <!-- Cambiar a -->
      <div class="lb-change-section">
        <label class="lb-change-label">Cambiar a</label>
        <select
          class="lb-class-select"
          :value="selectedBoxIndex >= 0 ? currentImageFeatures[selectedBoxIndex]?.category : ''"
          @change="(e) => $emit('changeCategory', e.target.value)"
          :disabled="selectedBoxIndex < 0"
        >
          <option v-for="cat in availableCategories" :key="cat" :value="cat">
            {{ cat }}
          </option>
        </select>
      </div>

      <!-- Visibilidad y Objetos Unificados -->
      <div class="lb-section-title lb-vis-header-main">
        <span>Objetos por categoría</span>
        <button
          class="lb-vis-toggle-all"
          :class="{ active: allHidden }"
          @click.prevent="$emit('toggleAllBoxes')"
          :title="allHidden ? 'Mostrar todos' : 'Ocultar todos'"
        >
          {{ allHidden ? '👁 Mostrar' : '🚫 Ocultar' }}
        </button>
      </div>

      <div class="lb-category-list">
        <details
          v-for="cat in availableCategories.toSorted()"
          :key="cat"
          class="lb-cat-details"
          :open="groupedFeatures[cat]?.length > 0"
        >
          <summary class="lb-cat-summary" :class="{ hidden: allHidden || hiddenCategories.has(cat) }">
            <span class="lb-vis-dot" :style="{ background: getCategoryColor(cat) }"></span>
            <span class="lb-vis-label">{{ cat }} ({{ groupedFeatures[cat]?.length || 0 }})</span>
            <span class="lb-vis-eye" @click.prevent="$emit('toggleCategory', cat)">
              {{ allHidden || hiddenCategories.has(cat) ? '🙈' : '👁' }}
            </span>
          </summary>

          <div class="lb-cat-items" v-if="groupedFeatures[cat]?.length">
            <div
              v-for="item in groupedFeatures[cat]"
              :key="item.index"
              class="lb-box-item"
              :class="{
                 selected: selectedBoxIndex === item.index,
                 hidden: allHidden || hiddenCategories.has(cat) || hiddenBoxes.has(item.box)
              }"
              @click="$emit('update:selectedBoxIndex', item.index)"
              @dblclick="$emit('zoomToBox', item.index)"
            >
              <span class="lb-box-label">Objeto {{ item.index + 1 }}</span>
              <span class="lb-vis-eye" @click.stop="$emit('toggleBoxVisibility', item.box)">
                {{ allHidden || hiddenCategories.has(cat) || hiddenBoxes.has(item.box) ? '🙈' : '👁' }}
              </span>
            </div>
          </div>
          <div class="lb-cat-empty" v-else>Sin detecciones</div>
        </details>
      </div>
    </div>

    <!-- Footer buttons -->
    <div class="lb-sidebar-footer">
      <!-- Panel de gráficos (Drop-up) -->
      <Transition name="fade">
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
                    width: totalDetections > 0 ? (stat.count / totalDetections) * 100 + '%' : '0%',
                    backgroundColor: stat.color,
                  }"
                ></div>
              </div>
              <div class="lb-chart-count">{{ stat.count }}</div>
            </div>
          </div>
        </div>
      </Transition>
      <!-- Botón de gráficos -->
      <ButtonComp class="lb-chart-btn" @click="$emit('update:showCharts', !showCharts)">
        📊 {{ showCharts ? 'Ocultar' : 'Ver' }} conteo
      </ButtonComp>

      <!-- Guardar -->
      <ButtonComp class="lb-save-btn" @click="$emit('save')" :disabled="!canUndo">Actualizar</ButtonComp>
    </div>
  </div>
</template>

<style scoped>
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
  flex-shrink: 0;
}

.lb-sidebar-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

/* ── Herramientas ── */
.lb-tools {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  flex-wrap: wrap;
  flex-shrink: 0;
}
.lb-tools-undo {
  padding-top: 0;
}
.lb-tool-btn {
  flex: 1;
}
button.btn.lb-tool-btn {
  width: 100%;
  padding: 6px 12px;
  border: 1px solid #4a5568;
  border-radius: 6px;
  background: #2d3748;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.15s;
}
button.btn.lb-tool-btn:hover,
button.btn.lb-tool-btn.active {
  background: #1d9e75;
  border-color: #1d9e75;
  color: white;
}
button.btn.lb-tool-btn-delete {
  background: #4a1f1f;
  border-color: #e53e3e;
  color: #fc8181;
}
button.btn.lb-tool-btn-delete:hover {
  background: #e53e3e;
  color: white;
}
button.btn.lb-tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  background: #2d3748;
  border-color: #4a5568;
  color: #a0aec0;
}

/* ── Cambiar a ── */
.lb-change-section {
  padding: 8px 12px;
  border-top: 1px solid #2d3748;
  border-bottom: 1px solid #2d3748;
  flex-shrink: 0;
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

/* ── Visibilidad y Categorías Unificadas ── */
.lb-vis-header-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.lb-vis-toggle-all {
  background: none;
  border: 1px solid #4a5568;
  border-radius: 4px;
  color: #a0aec0;
  font-size: 10px;
  padding: 2px 6px;
  cursor: pointer;
  transition: all 0.15s;
}
.lb-vis-toggle-all:hover,
.lb-vis-toggle-all.active {
  background: #2d3748;
  color: #fc8181;
  border-color: #fc8181;
}

.lb-category-list {
  display: flex;
  flex-direction: column;
}

.lb-cat-summary {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  cursor: pointer;
  user-select: none;
  transition: background 0.1s;
  list-style: none;
}
.lb-cat-summary::-webkit-details-marker {
  display: none;
}
.lb-cat-summary:hover {
  background: #1a202c;
}
.lb-cat-summary.hidden {
  opacity: 0.5;
}

.lb-cat-summary::before {
  content: "▶";
  font-size: 9px;
  color: #a0aec0;
  display: inline-block;
  transition: transform 0.2s;
}
.lb-cat-details[open] .lb-cat-summary::before {
  transform: rotate(90deg);
}

.lb-vis-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.lb-vis-label {
  flex: 1;
  color: #e2e8f0;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.lb-vis-eye {
  font-size: 12px;
  cursor: pointer;
  padding: 2px;
}
.lb-vis-eye:hover {
  transform: scale(1.1);
}

.lb-cat-items {
  padding: 0 8px 8px 24px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.lb-cat-empty {
  padding: 0 8px 8px 24px;
  font-size: 11px;
  color: #718096;
  font-style: italic;
}

.lb-box-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.1s, opacity 0.15s;
}
.lb-box-item:hover {
  background: rgba(255, 255, 255, 0.05);
}
.lb-box-item.selected {
  background: rgba(144, 205, 244, 0.15);
  color: #90cdf4;
}
.lb-box-item.hidden {
  opacity: 0.45;
}

.lb-box-label {
  font-size: 11px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  color: #cbd5e0;
}

/* ── Section titles ── */
.lb-section-title {
  padding: 10px 12px;
  font-size: 12px;
  font-weight: 600;
  color: #90cdf4;
  flex-shrink: 0;
  user-select: none;
}

/* ── Charts ── */
.lb-charts-panel {
  position: absolute;
  bottom: 100%;
  left: 0;
  width: 100%;
  box-sizing: border-box;
  padding: 12px;
  background: #1a202c;
  border-top: 1px solid #2d3748;
  border-bottom: 1px solid #2d3748;
  box-shadow: 0 -4px 12px rgba(0,0,0,0.3);
  z-index: 10;
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

/* ── Sidebar Footer ── */
.lb-sidebar-footer {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  background: #1a202c;
  border-top: 1px solid #2d3748;
  position: relative;
}

button.btn.lb-chart-btn {
  width: 100%;
  margin: 0;
  padding: 14px;
  border: none;
  border-bottom: 1px solid #2d3748;
  border-radius: 0;
  background: #2d3748;
  color: #e2e8f0;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.15s;
  text-align: center;
}
button.btn.lb-chart-btn:hover {
  background: #3c4a63;
  color: #90cdf4;
}

button.btn.lb-save-btn {
  width: 100%;
  margin: 0;
  padding: 14px;
  border: none;
  border-radius: 0;
  background: #1d9e75;
  color: white;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.15s;
}
button.btn.lb-save-btn:hover {
  background: #178a64;
}
button.btn.lb-save-btn:disabled {
  background: #2d3748;
  color: #a0aec0;
  cursor: not-allowed;
}
</style>
