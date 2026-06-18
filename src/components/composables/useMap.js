// components/composables/useMap.js
import L from 'leaflet'
import { ref, onMounted } from 'vue'

export function useMap(mapContainerRef) {
  const map = ref()
  const markersLayerGroup = ref(L.layerGroup())

  onMounted(() => {
    map.value = L.map(mapContainerRef.value, { zoomControl: true }).setView(
      [-42.15, -64.15],
      11,
    )

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map.value)

    markersLayerGroup.value.addTo(map.value)

    setTimeout(() => {
      if (map.value) map.value.invalidateSize()
    }, 200)
  })

  return { map, markersLayerGroup }
}
