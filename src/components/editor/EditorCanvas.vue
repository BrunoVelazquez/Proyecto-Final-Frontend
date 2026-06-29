<script setup>
defineProps({
  registerCanvasWrap: { type: Function, default: null },
  registerEditorCanvas: { type: Function, default: null },
})

defineEmits([
  'wheel',
  'mousedown',
  'mousemove',
  'mouseup',
  'mouseleave',
  'zoomIn',
  'zoomOut',
  'zoomReset'
])
</script>

<template>
  <div
    class="lb-canvas-wrap"
    :ref="registerCanvasWrap"
    @wheel.prevent="$emit('wheel', $event)"
    @mousedown="$emit('mousedown', $event)"
    @mousemove="$emit('mousemove', $event)"
    @mouseup="$emit('mouseup', $event)"
    @mouseleave="$emit('mouseleave', $event)"
  >
    <canvas :ref="registerEditorCanvas"></canvas>
    <div class="lb-zoom-overlay">
      <button class="lb-zoom-btn" @click="$emit('zoomOut')" title="Alejar">−</button>
      <button class="lb-zoom-btn lb-zoom-reset" @click="$emit('zoomReset')" title="Ajustar imagen">⊡</button>
      <button class="lb-zoom-btn" @click="$emit('zoomIn')" title="Acercar">+</button>
    </div>
  </div>
</template>

<style scoped>
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

.lb-zoom-overlay {
  position: absolute;
  bottom: 20px;
  right: 20px;
  display: flex;
  background: rgba(45, 55, 72, 0.85);
  backdrop-filter: blur(4px);
  border-radius: 8px;
  padding: 4px;
  gap: 4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
}

.lb-zoom-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #4a5568;
  border-radius: 6px;
  background: #1a202c;
  color: #e2e8f0;
  font-size: 18px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.lb-zoom-btn:hover {
  background: #4a5568;
  border-color: #90cdf4;
}

.lb-zoom-reset {
  font-size: 16px;
}
</style>
