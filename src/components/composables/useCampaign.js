// components/composables/useCampaign.js
import L from 'leaflet'
import { ref, computed, nextTick } from 'vue'
import exifr from 'exifr'
import { getPhotoPlace } from '../../utils/trajectoryUtils.js'

const API_BASE_URL = '/api'

export function useCampaign(
  map,
  markersLayerGroup,
  { getCategoryColor, extractCategories, selectedCategories, getImageUrl },
) {
  const geoJsonData = ref(null)
  const campaignLoaded = ref(false)

  // Feature seleccionada al hacer click en un marcador
  const selectedFeature = ref(null)

  // Funcionalidad para ubicar manualmente fotos sin GPS
  const placementModeFeature = ref(null)

  // Funcionalidad para mover un marcador libremente en el mapa
  const moveMarkerMode = ref(false)
  const moveMarkerTarget = ref(null) // { props, geometry } of the feature being moved
  let moveMarkerPreviewCircle = null

  const unmappedFeatures = computed(() => {
    if (!geoJsonData.value) return []
    return geoJsonData.value.features.filter(
      (f) => f.properties.gps_matched === false && !f.properties.manual_placement
    )
  })

  let mapClickSetup = false
  let moveMarkerClickHandler = null
  let moveMarkerMoveHandler = null

  // ── Trajectory polyline ──
  let trajectoryPolyline = null

  /** Draw the GPS trajectory polyline on the map */
  function showTrajectory(trajectoryData) {
    if (!map.value || !trajectoryData?.length) return
    clearTrajectoryLayer()
    const latLngs = trajectoryData.map(row => [row.latitude, row.longitude])
    trajectoryPolyline = L.polyline(latLngs, {
      color: '#ef4444',
      weight: 2,
      opacity: 0.7,
      dashArray: '4 4',
    }).addTo(map.value)
  }

  /** Remove the trajectory polyline from the map */
  function clearTrajectoryLayer() {
    if (trajectoryPolyline) {
      trajectoryPolyline.remove()
      trajectoryPolyline = null
    }
  }

  /**
   * Apply a time offset to all features — updates geometry.coordinates and gps.timestamp,
   * then re-renders all markers on the map.
   *
   * @param {number} offsetSeconds - The calibrated offset to apply to every feature
   * @param {Array} trajectoryData - Parsed GPS rows from useTrajectory
   */
  function applyOffset(offsetSeconds, trajectoryData) {
    if (!geoJsonData.value || !trajectoryData?.length) return

    let noTimestamp = 0
    let noMatch = 0
    let updated = 0

    geoJsonData.value.features.forEach((feature, i) => {
      // Ignorar los marcadores ubicados a mano, deben quedarse donde los puso el usuario
      if (feature.properties.manual_placement) return

      const ts = feature.properties?.gps?.timestamp
      if (!ts) {
        noTimestamp++
        if (i === 0) console.warn('[applyOffset] Feature 0 has no gps.timestamp:', feature.properties)
        return
      }

      if (i === 0) console.log(`[applyOffset] Feature 0 timestamp: "${ts}"`)

      const match = getPhotoPlace(ts, trajectoryData, offsetSeconds)
      if (match) {
        feature.geometry.coordinates = [match.longitude, match.latitude]
        feature.properties.gps.latitude = match.latitude
        feature.properties.gps.longitude = match.longitude
        updated++
      } else {
        noMatch++
        if (noMatch <= 2) {
          const { shiftTimestamp } = { shiftTimestamp: (t, s) => {
            const [dp, tp] = t.split(' ')
            const [y, mo, d] = dp.split('-').map(Number)
            const [h, mi, se] = tp.split(':').map(Number)
            const isoStr = `${y}-${String(mo).padStart(2,'0')}-${String(d).padStart(2,'0')}T${String(h).padStart(2,'0')}:${String(mi).padStart(2,'0')}:${String(se).padStart(2,'0')}Z`
            const date = new Date(isoStr)
            date.setTime(date.getTime() + s * 1000)
            return `${date.getUTCFullYear()}-${String(date.getUTCMonth()+1).padStart(2,'0')}-${String(date.getUTCDate()).padStart(2,'0')} ${String(date.getUTCHours()).padStart(2,'0')}:${String(date.getUTCMinutes()).padStart(2,'0')}:${String(date.getUTCSeconds()).padStart(2,'0')}`
          }}
          console.warn(`[applyOffset] No match for feature ts="${ts}" → shifted="${shiftTimestamp(ts, offsetSeconds)}" (first GPS="${trajectoryData[0]['date time']}", last="${trajectoryData[trajectoryData.length-1]['date time']}")`)
        }
      }
    })

    console.log(`[applyOffset] Updated ${updated} / ${geoJsonData.value.features.length} | noTimestamp=${noTimestamp} | noMatch=${noMatch}`)
    renderMarkers()
  }

  function renderMarkers() {
    if (!geoJsonData.value) return
    markersLayerGroup.value.clearLayers()

    geoJsonData.value.features.forEach((feature) => {
      const props = feature.properties
      if (!props.detections || props.detections.length === 0) return

      // No renderizar si no tiene match GPS y no fue ubicado manualmente
      if (props.gps_matched === false && !props.manual_placement) return

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

      // Add EXIF timestamp parsing concurrently
      await Promise.all(data.features.map(async (feature) => {
        if (!feature.properties.gps) {
          feature.properties.gps = {}
        }
        if (!feature.properties.gps.timestamp && getImageUrl) {
          try {
            const url = getImageUrl(feature.properties.image_name)
            const exifData = await exifr.parse(url, { tiff: true, ifd0: false, exif: true })
            // Reemplaza el bloque dentro de loadCampaign() en useCampaign.js

if (exifData?.DateTimeOriginal) {
  const d = exifData.DateTimeOriginal

  // PROBLEMA: exifr ya parseó el string EXIF asumiendo timezone LOCAL del browser,
  // entonces d.getFullYear()/getHours()/etc devuelven los componentes naive
  // tal cual estaban en el EXIF (porque exifr no tiene info de timezone real),
  // SIEMPRE Y CUANDO usemos los getters LOCALES, no los UTC.
  const yyyy = d.getFullYear()
  const mo = d.getMonth()
  const dd = d.getDate()
  const hh = d.getHours()
  const mi = d.getMinutes()
  const ss = d.getSeconds()

  // Réplica exacta de Python: localize(Etc/GMT) → astimezone(Etc/GMT-3) = +3h
  // Construimos un Date "puro" en UTC con los componentes naive, y le sumamos 3h.
  const naiveAsUTC = new Date(Date.UTC(yyyy, mo, dd, hh, mi, ss))
  naiveAsUTC.setUTCHours(naiveAsUTC.getUTCHours() + 3)

  const y2 = naiveAsUTC.getUTCFullYear()
  const m2 = String(naiveAsUTC.getUTCMonth() + 1).padStart(2, '0')
  const d2 = String(naiveAsUTC.getUTCDate()).padStart(2, '0')
  const h2 = String(naiveAsUTC.getUTCHours()).padStart(2, '0')
  const mn2 = String(naiveAsUTC.getUTCMinutes()).padStart(2, '0')
  const s2 = String(naiveAsUTC.getUTCSeconds()).padStart(2, '0')

  feature.properties.gps.timestamp = `${y2}-${m2}-${d2} ${h2}:${mn2}:${s2}`
  console.log(`[EXIF] ${feature.properties.image_name} → naive EXIF: ${yyyy}-${mo+1}-${dd} ${hh}:${mi}:${ss} → +3h: ${feature.properties.gps.timestamp}`)
} else {
              console.warn(`[EXIF] No DateTimeOriginal for ${feature.properties.image_name}`)
            }
          } catch (e) {
            console.error('Error reading EXIF for', feature.properties.image_name, e)
          }
        }
      }))

      geoJsonData.value = data

      extractCategories(data.features)

      campaignLoaded.value = true
      renderMarkers()

      nextTick(() => {
        map.value.invalidateSize()

        // Click en el fondo del mapa
        if (!mapClickSetup) {
          map.value.on('click', (e) => {
            if (placementModeFeature.value) {
              const f = placementModeFeature.value
              f.geometry = { type: 'Point', coordinates: [e.latlng.lng, e.latlng.lat] }
              f.properties.manual_placement = true

              placementModeFeature.value = null
              renderMarkers()
            } else {
              selectedFeature.value = null
            }
          })
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

  function startMoveMarker(featureProps) {
    if (!map.value || !geoJsonData.value) return

    // Find the actual feature object to track
    const feature = geoJsonData.value.features.find(
      (f) => f.properties.image_name === featureProps.image_name
    )
    if (!feature) return

    moveMarkerTarget.value = feature
    moveMarkerMode.value = true
    selectedFeature.value = null // Close the info card while relocating

    const [initLon, initLat] = feature.geometry.coordinates

    // Draw a draggable preview circle
    if (moveMarkerPreviewCircle) {
      moveMarkerPreviewCircle.remove()
    }
    moveMarkerPreviewCircle = L.circleMarker([initLat, initLon], {
      color: '#f97316',
      fillColor: '#f97316',
      fillOpacity: 0.4,
      opacity: 1,
      weight: 2,
      radius: 12,
    }).addTo(map.value)

    // Follow mouse on move
    moveMarkerMoveHandler = (e) => {
      moveMarkerPreviewCircle.setLatLng(e.latlng)
    }
    // Confirm position on click
    moveMarkerClickHandler = (e) => {
      L.DomEvent.stopPropagation(e)
      saveMarkerPosition(e.latlng.lat, e.latlng.lng)
    }

    map.value.on('mousemove', moveMarkerMoveHandler)
    map.value.once('click', moveMarkerClickHandler)
    map.value.getContainer().style.cursor = 'crosshair'
  }

  function saveMarkerPosition(lat, lon) {
    if (!moveMarkerTarget.value) return

    // Update the feature coordinates
    moveMarkerTarget.value.geometry.coordinates = [lon, lat]
    moveMarkerTarget.value.properties.manual_placement = true
    if (moveMarkerTarget.value.properties.gps) {
      moveMarkerTarget.value.properties.gps.latitude = lat
      moveMarkerTarget.value.properties.gps.longitude = lon
    }

    cancelMoveMarker()
    renderMarkers()
  }

  function cancelMoveMarker() {
    moveMarkerMode.value = false
    moveMarkerTarget.value = null
    if (moveMarkerPreviewCircle) {
      moveMarkerPreviewCircle.remove()
      moveMarkerPreviewCircle = null
    }
    if (map.value) {
      if (moveMarkerMoveHandler) map.value.off('mousemove', moveMarkerMoveHandler)
      if (moveMarkerClickHandler) map.value.off('click', moveMarkerClickHandler)
      map.value.getContainer().style.cursor = ''
    }
    moveMarkerMoveHandler = null
    moveMarkerClickHandler = null
  }

  return {
    geoJsonData,
    campaignLoaded,
    selectedFeature,
    unmappedFeatures,
    placementModeFeature,
    moveMarkerMode,
    moveMarkerTarget,
    loadCampaign,
    renderMarkers,
    handleFilterChange,
    updateFeatureDetections,
    showTrajectory,
    clearTrajectoryLayer,
    applyOffset,
    startMoveMarker,
    cancelMoveMarker,
  }
}
