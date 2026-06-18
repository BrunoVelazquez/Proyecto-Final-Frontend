<script setup>
import { computed } from 'vue'

const props = defineProps({
  feature: { type: Object, default: null }, // { props: feature.properties, summary: { cat: count } }
  getCategoryColor: { type: Function, required: true },
  getImageUrl: { type: Function, required: true },
})

defineEmits(['openEditor', 'close'])

const imageUrl = computed(() =>
  props.feature ? props.getImageUrl(props.feature.props.image_name) : null,
)

const summaryEntries = computed(() =>
  props.feature
    ? Object.entries(props.feature.summary).sort((a, b) => b[1] - a[1])
    : [],
)
</script>

<template>
  <Transition name="slide-down">
    <div v-if="feature" class="marker-info-card">

      <!-- Image with floating close button -->
      <div class="mic-image-frame">
        <img :src="imageUrl" alt="Vista previa" class="mic-preview-img" />
        <button class="mic-close-btn" @click="$emit('close')" title="Cerrar">✕</button>
      </div>

      <div class="mic-body">
        <p class="mic-total">
          Total detectados: <b>{{ feature.props.total_detections }}</b>
        </p>
        <ul class="mic-classes-list">
          <li v-for="[cat, count] in summaryEntries" :key="cat" class="mic-class-row">
            <span class="mic-dot" :style="{ background: getCategoryColor(cat) }"></span>
            <span class="mic-cat-name">{{ cat }}</span>
            <span class="mic-cat-count">{{ count }}</span>
          </li>
        </ul>
      </div>

      <button class="mic-action-btn" @click="$emit('openEditor', feature.props)">
        🔍 Abrir editor
      </button>
    </div>
  </Transition>
</template>

<style scoped>
.marker-info-card {
  width: 100%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Image + floating close */
.mic-image-frame {
  position: relative;
  width: 100%;
  height: 110px;
  background: #eaeaea;
  overflow: hidden;
  flex-shrink: 0;
}
.mic-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.mic-close-btn {
  position: absolute;
  top: 7px;
  right: 7px;
  background: rgba(229, 62, 62, 0.9);
  border: none;
  color: white;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  transition: background 0.15s;
  backdrop-filter: blur(2px);
}
.mic-close-btn:hover {
  background: rgba(197, 48, 48, 1);
}

.mic-body {
  padding: 8px 14px 4px;
}
.mic-total {
  font-size: 12px;
  margin: 0 0 6px 0;
  color: #555;
}
.mic-classes-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 90px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mic-class-row {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: #606266;
}
.mic-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.mic-cat-name {
  flex: 1;
}
.mic-cat-count {
  font-weight: bold;
  color: #5b5394;
}

.mic-action-btn {
  background-color: #1d9e75;
  color: white;
  border: none;
  padding: 10px 0;
  width: 100%;
  font-weight: bold;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
  flex-shrink: 0;
  margin-top: 6px;
}
.mic-action-btn:hover {
  background-color: #178a64;
}

/* Slide-in animation */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.22s ease;
}
.slide-down-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
