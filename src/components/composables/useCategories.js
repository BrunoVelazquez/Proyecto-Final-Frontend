// components/composables/useCategories.js
import { ref } from 'vue'

const CLASS_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
  '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
  '#F1948A', '#82E0AA', '#F8C471', '#AED6F1', '#A9DFBF',
]

export function useCategories() {
  const categoryColorMap = ref({})
  const availableCategories = ref([])
  const selectedCategories = ref([])
  let nextColorIndex = 0

  function getCategoryColor(category) {
    if (!categoryColorMap.value[category]) {
      categoryColorMap.value[category] = CLASS_COLORS[nextColorIndex % CLASS_COLORS.length]
      nextColorIndex++
    }
    return categoryColorMap.value[category]
  }

  function extractCategories(features) {
    const categoriesSet = new Set()
    features.forEach((f) => {
      if (f.properties.detections) {
        f.properties.detections.forEach((d) => categoriesSet.add(d.category))
      }
    })
    availableCategories.value = Array.from(categoriesSet)
    selectedCategories.value = [...availableCategories.value]
  }

  return {
    categoryColorMap,
    availableCategories,
    selectedCategories,
    getCategoryColor,
    extractCategories,
  }
}
