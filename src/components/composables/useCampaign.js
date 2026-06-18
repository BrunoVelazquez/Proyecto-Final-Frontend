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

  // Callback inyectado desde BaseMap.vue para abrir el editor
  let onOpenEditor = null
  function setOpenEditorCallback(fn) {
    onOpenEditor = fn
  }

  function getImageUrl(imageName) {
    return new URL(`../../assets/images/${imageName}`, import.meta.url).href
  }

  function createPopupContent(props, summary) {
    let listItemsHtml = Object.entries(summary)
      .map(
        ([cat, count]) =>
          `<li><span class="dot" style="background:${getCategoryColor(cat)}"></span> <b>${cat}:</b> ${count}</li>`,
      )
      .join('')

    const container = document.createElement('div')
    container.className = 'custom-map-popup'
    container.innerHTML = `
      <h4>${props.image_name}</h4>
      <div class="popup-image-frame">
        <img src="${getImageUrl(props.image_name)}" alt="Cargando..." class="popup-preview-img" />
      </div>
      <p class="popup-total">Total detectados: <b>${props.total_detections}</b></p>
      <ul class="popup-classes-list">${listItemsHtml}</ul>
    `
    const btn = document.createElement('button')
    btn.className = 'popup-action-btn'
    btn.innerText = '🔍 Abrir editor'
    btn.onclick = () => {
      map.value.closePopup()
      if (onOpenEditor) onOpenEditor(props)
    }
    container.appendChild(btn)
    return container
  }

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
      const popupFactory = () => createPopupContent(props, countByClass)

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

        marker.bindPopup(popupFactory, { minWidth: 220, maxWidth: 240 })
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
    renderMarkers()
  }

  return {
    geoJsonData,
    campaignLoaded,
    loadCampaign,
    renderMarkers,
    handleFilterChange,
    setOpenEditorCallback,
  }
}
