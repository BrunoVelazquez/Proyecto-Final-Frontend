// components/composables/useCategories.js
import { ref } from 'vue'

// Golden-ratio hue step ensures maximal angular distance between successive colors
const GOLDEN_ANGLE = 137.508

export function useCategories() {
  const categoryColorMap = ref({})
  const availableCategories = ref([])
  const selectedCategories = ref([])
  let nextColorIndex = 0

  function getCategoryColor(category) {
    if (!categoryColorMap.value[category]) {
      // Spread hue using golden angle, vary lightness slightly to add more separation
      const hue = (nextColorIndex * GOLDEN_ANGLE) % 360
      const lightness = 55 + (nextColorIndex % 3) * 8   // 55%, 63%, 71%
      const saturation = 72 - (nextColorIndex % 2) * 12  // 72% or 60%
      categoryColorMap.value[category] = `hsl(${hue.toFixed(1)}, ${saturation}%, ${lightness}%)`
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
