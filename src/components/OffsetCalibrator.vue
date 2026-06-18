<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { formatOffsetLabel } from '../utils/trajectoryUtils.js'
import L from 'leaflet'

const props = defineProps({
  referenceFeature: { type: Object, default: null }, // { props, summary } from selectedFeature
  getImageUrl: { type: Function, required: true },
  getPositionAtOffset: { type: Function, required: true }, // from useTrajectory
  map: { type: Object, default: null }, // Leaflet map instance (ref.value)
})

const emit = defineEmits(['apply', 'cancel'])

const offsetSeconds = ref(0)

const offsetLabel = computed(() => formatOffsetLabel(offsetSeconds.value))
const refImageUrl = computed(() =>
  props.referenceFeature ? props.getImageUrl(props.referenceFeature.props.image_name) : null
)
const refTimestamp = computed(() =>
  props.referenceFeature?.props?.gps?.timestamp ?? '—'
)

// ── Live preview marker ──
let previewMarker = null

function updatePreviewMarker() {
  if (!props.referenceFeature || !props.map) return
  const ts = props.referenceFeature.props.gps?.timestamp
  if (!ts) return

  const pos = props.getPositionAtOffset(ts, offsetSeconds.value)
  if (!pos) return

  if (!previewMarker) {
    previewMarker = L.circleMarker([pos.lat, pos.lng], {
      color: '#ffffff',
      fillColor: '#f97316',
      fillOpacity: 0.9,
      weight: 2,
      radius: 10,
    }).addTo(props.map)
    previewMarker.bindTooltip('📍 Referencia', { permanent: false })
  } else {
    previewMarker.setLatLng([pos.lat, pos.lng])
  }
}

function clearPreviewMarker() {
  if (previewMarker) {
    previewMarker.remove()
    previewMarker = null
  }
}

watch(() => props.referenceFeature, (val) => {
  if (!val) clearPreviewMarker()
  else updatePreviewMarker()
}, { immediate: true })

watch(offsetSeconds, () => updatePreviewMarker())

onUnmounted(() => clearPreviewMarker())

function handleApply() {
  clearPreviewMarker()
  emit('apply', offsetSeconds.value)
}

function handleCancel() {
  clearPreviewMarker()
  offsetSeconds.value = 0
  emit('cancel')
}
</script>

<template>
  <div v-if="referenceFeature" class="offset-calibrator">
    <div class="oc-header">
      <span class="oc-icon">🛰️</span>
      <span class="oc-title">Calibrar desfasaje GPS</span>
    </div>

    <div v-if="referenceFeature?.props?.manual_placement || referenceFeature?.props?.gps_matched === false" class="oc-warning">
      Esta imagen fue ubicada manualmente o no tiene datos de GPS. No se puede utilizar como referencia para calibrar la trayectoria.
    </div>

    <div v-else>
      <div class="oc-instruction">
        Mueve el slider para ajustar la posición de esta foto sobre la trayectoria.
        Cuando la ubicación sea correcta, presiona <strong>Aplicar</strong>.
      </div>

      <!-- Reference image thumbnail -->
      <div class="oc-photo-row">
        <img
          v-if="refImageUrl"
          :src="refImageUrl"
          class="oc-thumb"
          :alt="referenceFeature.props.image_name"
        />
        <div class="oc-photo-info">
          <div class="oc-photo-name">{{ referenceFeature.props.image_name }}</div>
          <div class="oc-photo-ts">🕐 GPS: {{ refTimestamp }}</div>
        </div>
      </div>

      <!-- Offset slider -->
      <div class="oc-slider-wrap">
        <div class="oc-offset-label">Desfasaje: <strong>{{ offsetLabel }}</strong></div>
        <input
          id="offset-slider"
          type="range"
          v-model.number="offsetSeconds"
          min="-1200"
          max="1200"
          step="1"
          class="oc-slider"
        />
        <div class="oc-slider-limits">
          <span>−20 min</span>
          <span>0</span>
          <span>+20 min</span>
        </div>
      </div>
    </div>

    <!-- Action buttons -->
    <div class="oc-actions">
      <button class="oc-btn oc-btn-cancel" @click="handleCancel">Cancelar</button>
      <button
        v-if="!referenceFeature?.props?.manual_placement && referenceFeature?.props?.gps_matched !== false"
        class="oc-btn oc-btn-apply"
        @click="handleApply"
      >
        Aplicar
      </button>
    </div>
  </div>

  <!-- Waiting for user to select a reference photo -->
  <div v-else class="offset-calibrator oc-waiting">
    <div class="oc-header">
      <span class="oc-icon">🛰️</span>
      <span class="oc-title">Calibrar desfasaje GPS</span>
    </div>
    <div class="oc-instruction">
      📌 Haz click sobre un marcador del mapa para seleccionarlo como <strong>foto de referencia</strong>.
    </div>
    <button class="oc-btn oc-btn-cancel" @click="handleCancel">Cancelar</button>
  </div>
</template>

<style scoped>
.oc-warning {
  background: rgba(239, 68, 68, 0.1);
  border-left: 4px solid #ef4444;
  color: #fca5a5;
  padding: 10px;
  font-size: 13px;
  margin-bottom: 12px;
  border-radius: 4px;
}

.offset-calibrator {
  background: #1a1f35;
  border: 1px solid #2d3748;
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  color: #e2e8f0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.oc-header {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid #2d3748;
  padding-bottom: 10px;
}
.oc-icon { font-size: 18px; }
.oc-title {
  font-size: 14px;
  font-weight: 700;
  color: #90cdf4;
}

.oc-instruction {
  font-size: 12px;
  color: #a0aec0;
  line-height: 1.5;
}
.oc-instruction strong { color: #e2e8f0; }

.oc-photo-row {
  display: flex;
  gap: 10px;
  align-items: center;
  background: #0f1929;
  border-radius: 8px;
  padding: 8px;
}
.oc-thumb {
  width: 64px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  flex-shrink: 0;
  border: 1px solid #2d3748;
}
.oc-photo-info {
  flex: 1;
  min-width: 0;
}
.oc-photo-name {
  font-size: 10px;
  color: #a0aec0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.oc-photo-ts {
  font-size: 11px;
  color: #68d391;
  margin-top: 3px;
}

.oc-slider-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.oc-offset-label {
  font-size: 13px;
  text-align: center;
  color: #a0aec0;
}
.oc-offset-label strong {
  font-size: 16px;
  color: #f6ad55;
  letter-spacing: 0.5px;
}
.oc-slider {
  width: 100%;
  appearance: none;
  height: 4px;
  border-radius: 4px;
  background: linear-gradient(to right, #4a5568 0%, #2b6cb0 50%, #4a5568 100%);
  outline: none;
  cursor: pointer;
}
.oc-slider::-webkit-slider-thumb {
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #f97316;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  cursor: grab;
}
.oc-slider::-webkit-slider-thumb:active { cursor: grabbing; }

.oc-slider-limits {
  display: flex;
  justify-content: space-between;
  font-size: 10px;
  color: #4a5568;
}

.oc-actions {
  display: flex;
  gap: 8px;
}
.oc-btn {
  flex: 1;
  padding: 10px 8px;
  border: none;
  border-radius: 8px;
  font-size: 12px;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.15s;
}
.oc-btn-cancel {
  background: #2d3748;
  color: #a0aec0;
}
.oc-btn-cancel:hover { background: #4a5568; color: #e2e8f0; }
.oc-btn-apply {
  background: #1d9e75;
  color: white;
}
.oc-btn-apply:hover { background: #178a64; }

.oc-waiting .oc-instruction { text-align: center; padding: 8px 0; }
</style>
