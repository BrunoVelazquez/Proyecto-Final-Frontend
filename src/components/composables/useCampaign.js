// components/composables/useCampaign.js
import L from 'leaflet'
import { ref, nextTick } from 'vue'

const API_BASE_URL = 'http://127.0.0.1:8000'

export function useCampaign(
  map,
  markersLayerGroup,
  { getCategoryColor, extractCategories, selectedCategories, availableCategories },
) {
  const geoJsonData = ref(null)
  const campaignLoaded = ref(false)

  // Feature seleccionada al hacer click en un marcador
  const selectedFeature = ref(null)

  // Callback inyectado desde BaseMap.vue para abrir el editor
  let onOpenEditor = null
  function setOpenEditorCallback(fn) {
    onOpenEditor = fn
  }

  let mapClickSetup = false

  function renderMarkers() {
    if (!geoJsonData.value) return
    markersLayerGroup.value.clearLayers()

    geoJsonData.value.features.forEach((feature) => {
      const props = feature.properties
      if (!props.detections || props.detections.length === 0) return

      const countByClass = {}
      props.detections.forEach((d) => {
        if (selectedCategories.value.includes(d.category)) {
          countByClass[d.category] = (countByClass[d.category] || 0) + 1
        }
      })

      const activeClasses = Object.keys(countByClass)
      if (activeClasses.length === 0) return

      activeClasses.sort((a, b) => countByClass[b] - countByClass[a])

      const [lon, lat] = feature.geometry.coordinates

      activeClasses.forEach((cat) => {
        const count = countByClass[cat]
        const radius = Math.max(8, Math.min(30, Math.sqrt(count) * 4.5))
        const color = getCategoryColor(cat)

        const marker = L.circleMarker([lat, lon], {
          color: color,
          fillColor: color,
          fillOpacity: 0.25,
          opacity: 0.8,
          weight: 2,
          radius: radius,
        })

        marker.on('click', (e) => {
          L.DomEvent.stopPropagation(e)
          selectedFeature.value = { props, summary: { ...countByClass } }
        })

        markersLayerGroup.value.addLayer(marker)
      })
    })
  }

  async function loadCampaign() {
    try {
      const response = await fetch(`${API_BASE_URL}/dummy`)
      const data = await response.json()
      geoJsonData.value = data

      extractCategories(data.features)

      campaignLoaded.value = true
      renderMarkers()

      nextTick(() => {
        map.value.invalidateSize()

        // Click en el fondo del mapa → deseleccionar
        if (!mapClickSetup) {
          map.value.on('click', () => { selectedFeature.value = null })
          mapClickSetup = true
        }

        const dummyLayer = L.geoJSON(data)
        if (data.features.length > 0) {
          map.value.fitBounds(dummyLayer.getBounds(), { padding: [50, 50] })
        }
      })
    } catch (error) {
      console.error('Error al conectar con la API:', error)
    }
  }

  function handleFilterChange() {
    selectedFeature.value = null
    renderMarkers()
  }

  // Escribe las detecciones editadas de vuelta al geoJSON y actualiza el mapa
  function updateFeatureDetections(imageName, newDetections) {
    if (!geoJsonData.value) return
    const feature = geoJsonData.value.features.find(
      (f) => f.properties.image_name === imageName,
    )
    if (feature) {
      feature.properties.detections = JSON.parse(JSON.stringify(newDetections))
      feature.properties.total_detections = newDetections.length
      // Actualizar el summary de la tarjeta si sigue seleccionada
      if (selectedFeature.value?.props.image_name === imageName) {
        const countByClass = {}
        newDetections.forEach((d) => {
          if (selectedCategories.value.includes(d.category)) {
            countByClass[d.category] = (countByClass[d.category] || 0) + 1
          }
        })
        selectedFeature.value = { props: feature.properties, summary: countByClass }
      }
    }
    renderMarkers()
  }

  return {
    geoJsonData,
    campaignLoaded,
    selectedFeature,
    loadCampaign,
    renderMarkers,
    handleFilterChange,
    updateFeatureDetections,
    setOpenEditorCallback,
  }
}
