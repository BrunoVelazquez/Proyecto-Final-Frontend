<script setup>
import ButtonComp from '../ButtonComp.vue'
import EditorCanvas from './EditorCanvas.vue'
import EditorSidebar from './EditorSidebar.vue'

defineProps({
  currentEditingImage: { type: String, default: null },
  currentImageFeatures: { type: Array, required: true },
  selectedBoxIndex: { type: Number, required: true },
  editorTool: { type: String, required: true },
  saveStatus: { type: String, default: '' },
  showCharts: { type: Boolean, required: true },
  detectionStats: { type: Array, required: true },
  totalDetections: { type: Number, required: true },
  availableCategories: { type: Array, required: true },
  getCategoryColor: { type: Function, required: true },
  canvasWrapRef: { type: Object, default: null },
  editorCanvasRef: { type: Object, default: null },
})

defineEmits([
  'close',
  'update:editorTool',
  'update:selectedBoxIndex',
  'update:showCharts',
  'removeBox',
  'changeCategory',
  'save',
  'wheel',
  'mousedown',
  'mousemove',
  'mouseup',
  'mouseleave',
])
</script>

<template>
  <div v-if="currentEditingImage" class="lb-overlay" @mousedown="$emit('close')">
    <div class="lb-panel" @mousedown.stop>
      <div class="lb-header">
        <span class="lb-title">{{ currentEditingImage }}</span>
        <ButtonComp class="lb-close" @click="$emit('close')">✕</ButtonComp>
      </div>

      <div class="lb-body">
        <EditorCanvas
          :canvasWrapRef="canvasWrapRef"
          :editorCanvasRef="editorCanvasRef"
          @wheel="$emit('wheel', $event)"
          @mousedown="$emit('mousedown', $event)"
          @mousemove="$emit('mousemove', $event)"
          @mouseup="$emit('mouseup', $event)"
          @mouseleave="$emit('mouseleave', $event)"
        />

        <EditorSidebar
          :editorTool="editorTool"
          :selectedBoxIndex="selectedBoxIndex"
          :currentImageFeatures="currentImageFeatures"
          :availableCategories="availableCategories"
          :getCategoryColor="getCategoryColor"
          :showCharts="showCharts"
          :detectionStats="detectionStats"
          :totalDetections="totalDetections"
          :saveStatus="saveStatus"
          @update:editorTool="$emit('update:editorTool', $event)"
          @update:selectedBoxIndex="$emit('update:selectedBoxIndex', $event)"
          @update:showCharts="$emit('update:showCharts', $event)"
          @removeBox="$emit('removeBox', $event)"
          @changeCategory="$emit('changeCategory', $event)"
          @save="$emit('save')"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
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
.lb-close :deep(button) {
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
.lb-close :deep(button:hover) {
  background: #c53030;
}

.lb-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}
</style>
