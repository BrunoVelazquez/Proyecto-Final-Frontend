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
  registerCanvasWrap: { type: Function, default: null },
  registerEditorCanvas: { type: Function, default: null },
  canUndo: { type: Boolean, default: false },
  canRedo: { type: Boolean, default: false },
  hiddenCategories: { type: Object, default: () => new Set() },
  hiddenBoxes: { type: Object, default: () => new Set() },
  allHidden: { type: Boolean, default: false },
})

defineEmits([
  'close',
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
  'zoomIn',
  'zoomOut',
  'zoomReset',
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
        <span class="lb-title">ID: {{ currentEditingImage }}</span>
        <ButtonComp class="lb-close" @click="$emit('close')">✕</ButtonComp>
      </div>

      <div class="lb-body">
        <EditorCanvas
          :registerCanvasWrap="registerCanvasWrap"
          :registerEditorCanvas="registerEditorCanvas"
          @wheel="$emit('wheel', $event)"
          @mousedown="$emit('mousedown', $event)"
          @mousemove="$emit('mousemove', $event)"
          @mouseup="$emit('mouseup', $event)"
          @mouseleave="$emit('mouseleave', $event)"
          @zoomIn="$emit('zoomIn')"
          @zoomOut="$emit('zoomOut')"
          @zoomReset="$emit('zoomReset')"
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
          :canUndo="canUndo"
          :canRedo="canRedo"
          :hiddenCategories="hiddenCategories"
          :hiddenBoxes="hiddenBoxes"
          :allHidden="allHidden"
          @update:editorTool="$emit('update:editorTool', $event)"
          @update:selectedBoxIndex="$emit('update:selectedBoxIndex', $event)"
          @update:showCharts="$emit('update:showCharts', $event)"
          @removeBox="$emit('removeBox', $event)"
          @changeCategory="$emit('changeCategory', $event)"
          @save="$emit('save')"
          @undo="$emit('undo')"
          @redo="$emit('redo')"
          @toggleAllBoxes="$emit('toggleAllBoxes')"
          @toggleCategory="$emit('toggleCategory', $event)"
          @toggleBoxVisibility="$emit('toggleBoxVisibility', $event)"
          @zoomToBox="$emit('zoomToBox', $event)"
        />
      </div>

      <!-- Floating save status -->
      <Transition name="fade">
        <div v-if="saveStatus" class="lb-floating-status" :class="{ error: saveStatus.includes('❌') }">
          {{ saveStatus }}
        </div>
      </Transition>

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
  position: relative;
}

/* Floating Status */
.lb-floating-status {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 24px;
  background: rgba(45, 55, 72, 0.95);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  font-size: 14px;
  color: #68d391;
  font-weight: bold;
  text-align: center;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
  z-index: 1000;
  pointer-events: none;
}
.lb-floating-status.error {
  color: #fc8181;
}

/* Fade Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s, transform 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translate(-50%, 10px);
}
</style>
