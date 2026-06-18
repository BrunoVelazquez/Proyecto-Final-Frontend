<script setup>
defineProps({
  canvasWrapRef: { type: Object, default: null },
  editorCanvasRef: { type: Object, default: null },
})

defineEmits(['wheel', 'mousedown', 'mousemove', 'mouseup', 'mouseleave'])
</script>

<template>
  <div
    class="lb-canvas-wrap"
    :ref="canvasWrapRef"
    @wheel.prevent="$emit('wheel', $event)"
    @mousedown="$emit('mousedown', $event)"
    @mousemove="$emit('mousemove', $event)"
    @mouseup="$emit('mouseup', $event)"
    @mouseleave="$emit('mouseleave', $event)"
  >
    <canvas :ref="editorCanvasRef"></canvas>
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
</style>
