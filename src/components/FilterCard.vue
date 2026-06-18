<script setup>
defineProps({
  availableCategories: { type: Array, required: true },
  selectedCategories: { type: Array, required: true },
  getCategoryColor: { type: Function, required: true },
})

defineEmits(['change'])
</script>

<template>
  <div class="floating-filter-card">
    <h4>Filtros de Campaña</h4>
    <div class="filter-scroll-area">
      <div v-for="cat in availableCategories" :key="cat" class="checkbox-row">
        <input
          type="checkbox"
          :id="'filter-' + cat"
          :value="cat"
          :checked="selectedCategories.includes(cat)"
          @change="$emit('change', cat)"
        />
        <span class="legend-color-dot" :style="{ backgroundColor: getCategoryColor(cat) }"></span>
        <label :for="'filter-' + cat">{{ cat }}</label>
      </div>
    </div>
    <div class="card-footer-stats">Categorías activas: {{ selectedCategories.length }}</div>
  </div>
</template>

<style scoped>
.floating-filter-card {
  position: absolute;
  top: 20px;
  right: 20px;
  width: 260px;
  max-height: 400px;
  background: white;
  border-radius: 12px;
  padding: 16px;
  z-index: 1000;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
}
.floating-filter-card h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  color: #303133;
  border-bottom: 2px solid #5b5394;
  padding-bottom: 6px;
}
.filter-scroll-area {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.checkbox-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #606266;
}
.checkbox-row input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
.legend-color-dot {
  width: 12px;
  height: 12px;
  border-radius: 4px;
  flex-shrink: 0;
}
.card-footer-stats {
  margin-top: 12px;
  font-size: 11px;
  color: #909399;
  text-align: right;
  border-top: 1px solid #f2f6fc;
  padding-top: 6px;
}
</style>
