<script setup>
import ButtonComp from '../ButtonComp.vue'

defineProps({
  editorTool: { type: String, required: true },
  selectedBoxIndex: { type: Number, required: true },
  currentImageFeatures: { type: Array, required: true },
  availableCategories: { type: Array, required: true },
  getCategoryColor: { type: Function, required: true },
  showCharts: { type: Boolean, required: true },
  detectionStats: { type: Array, required: true },
  totalDetections: { type: Number, required: true },
  saveStatus: { type: String, default: '' },
})

defineEmits([
  'update:editorTool',
  'update:selectedBoxIndex',
  'update:showCharts',
  'removeBox',
  'changeCategory',
  'save',
])
</script>

<template>
  <div class="lb-sidebar">
    <h4>Editor de detecciones</h4>

    <!-- Herramientas -->
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

    <!-- Lista de objetos encontrados -->
    <div class="lb-section-title">Objetos encontrados</div>
    <div class="lb-box-list">
      <div
        v-for="(box, index) in currentImageFeatures"
        :key="index"
        class="lb-box-item"
        :class="{ selected: selectedBoxIndex === index }"
        @click="$emit('update:selectedBoxIndex', index)"
      >
        <div class="lb-box-dot" :style="{ background: getCategoryColor(box.category) }"></div>
        <span class="lb-box-label">{{ box.category }}</span>
      </div>
    </div>

    <!-- Botón de gráficos -->
    <ButtonComp class="lb-chart-btn" @click="$emit('update:showCharts', !showCharts)">
      📊 {{ showCharts ? 'Ocultar' : 'Ver' }} conteo
    </ButtonComp>

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
                width: totalDetections > 0 ? (stat.count / totalDetections) * 100 + '%' : '0%',
                backgroundColor: stat.color,
              }"
            ></div>
          </div>
          <div class="lb-chart-count">{{ stat.count }}</div>
        </div>
      </div>
    </div>

    <!-- Guardar -->
    <ButtonComp class="lb-save-btn" @click="$emit('save')">💾 Guardar</ButtonComp>

    <!-- Status de guardado -->
    <div v-if="saveStatus" class="lb-status" :class="{ error: saveStatus.includes('❌') }">
      {{ saveStatus }}
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
}

.lb-tools {
  display: flex;
  gap: 6px;
  padding: 10px 12px;
  flex-wrap: wrap;
}
.lb-tool-btn {
  flex: 1;
}
.lb-tool-btn :deep(button) {
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
.lb-tool-btn :deep(button:hover),
.lb-tool-btn.active :deep(button) {
  background: #1d9e75;
  border-color: #1d9e75;
  color: white;
}
.lb-tool-btn-delete :deep(button) {
  background: #4a1f1f;
  border-color: #e53e3e;
  color: #fc8181;
}
.lb-tool-btn-delete :deep(button:hover) {
  background: #e53e3e;
  color: white;
}
.lb-tool-btn :deep(button:disabled) {
  opacity: 0.4;
  cursor: not-allowed;
}

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

.lb-section-title {
  padding: 8px 12px 4px;
  font-size: 12px;
  font-weight: 600;
  color: #90cdf4;
  border-bottom: 1px solid #2d3748;
}

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

.lb-chart-btn :deep(button) {
  width: 100%;
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
.lb-chart-btn :deep(button:hover) {
  background: #3c4a63;
  border-color: #90cdf4;
}

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

.lb-save-btn :deep(button) {
  width: 100%;
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
.lb-save-btn :deep(button:hover) {
  background: #178a64;
}

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
