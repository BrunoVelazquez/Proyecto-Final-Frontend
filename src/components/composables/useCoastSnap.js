// components/composables/useCoastSnap.js
// Georreferenciación Inteligente (Actividad 2.2):
// Proyecta cada marcador al punto más cercano sobre la línea de costa,
// obtenida de OpenStreetMap via la API Overpass.

import { ref } from 'vue'

export function useCoastSnap() {
  const snapStatus = ref('') // '', 'loading', 'snapping', 'done', 'error'
  const snapMessage = ref('')

  /**
   * Fetches coastline ways from OpenStreetMap Overpass API
   * within the given bounding box, and returns an array of
   * coordinate pairs [[lat, lon], ...] representing all segments.
   */
  async function fetchCoastlineSegments(south, west, north, east) {
    // Add a small padding to the bounding box to catch coast near edges
    const pad = 0.05
    const bbox = `${south - pad},${west - pad},${north + pad},${east + pad}`
    const query = `[out:json][timeout:30];way["natural"="coastline"](${bbox});(._;>;);out body;`
    const apiUrl = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')
    const response = await fetch(`${apiUrl}/api/overpass/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `data=${encodeURIComponent(query)}`,
    })
    if (!response.ok) throw new Error(`Overpass API error: ${response.status}`)
    const data = await response.json()

    // Build a node map: id → {lat, lon}
    const nodeMap = {}
    for (const el of data.elements) {
      if (el.type === 'node') {
        nodeMap[el.id] = { lat: el.lat, lon: el.lon }
      }
    }

    // Extract ordered coordinate arrays from each way
    const segments = []
    for (const el of data.elements) {
      if (el.type === 'way' && el.nodes) {
        const coords = el.nodes
          .map((nid) => nodeMap[nid])
          .filter(Boolean)
        if (coords.length >= 2) {
          segments.push(coords)
        }
      }
    }

    return segments
  }

  /**
   * Projects point P onto segment AB and returns the closest point Q.
   * All values are in degrees (lat/lon treated as flat at local scale).
   */
  function projectPointOnSegment(pLat, pLon, aLat, aLon, bLat, bLon) {
    const dx = bLon - aLon
    const dy = bLat - aLat
    const lenSq = dx * dx + dy * dy
    if (lenSq === 0) return { lat: aLat, lon: aLon, distSq: squaredDist(pLat, pLon, aLat, aLon) }

    // Parameter t of projection, clamped to [0, 1]
    let t = ((pLon - aLon) * dx + (pLat - aLat) * dy) / lenSq
    t = Math.max(0, Math.min(1, t))

    const qLon = aLon + t * dx
    const qLat = aLat + t * dy
    return { lat: qLat, lon: qLon, distSq: squaredDist(pLat, pLon, qLat, qLon) }
  }

  function squaredDist(lat1, lon1, lat2, lon2) {
    const dlat = lat2 - lat1
    const dlon = lon2 - lon1
    // Approximate cos(lat) correction for lon degrees → same scale as lat degrees
    const cosLat = Math.cos((lat1 * Math.PI) / 180)
    return dlat * dlat + (dlon * cosLat) * (dlon * cosLat)
  }

  /**
   * Given all coast segments and a point (pLat, pLon),
   * returns the nearest point on any coast segment.
   */
  function nearestCoastPoint(pLat, pLon, coastSegments) {
    let best = null

    for (const segment of coastSegments) {
      for (let i = 0; i < segment.length - 1; i++) {
        const a = segment[i]
        const b = segment[i + 1]
        const proj = projectPointOnSegment(pLat, pLon, a.lat, a.lon, b.lat, b.lon)
        if (best === null || proj.distSq < best.distSq) {
          best = proj
        }
      }
    }

    return best // { lat, lon, distSq }
  }

  /**
   * Main function: snaps all features in geoJsonData to the nearest
   * coastline point and calls renderMarkers() to update the map.
   *
   * @param {Ref} geoJsonData - the reactive GeoJSON ref from useCampaign
   * @param {Function} renderMarkers - re-render function from useCampaign
   */
  async function snapAllToCoast(geoJsonData, renderMarkers) {
    if (!geoJsonData.value?.features?.length) {
      snapStatus.value = 'error'
      snapMessage.value = 'No hay marcadores cargados.'
      return
    }

    // Collect features that are positioned on the map
    const mappedFeatures = geoJsonData.value.features.filter(
      (f) =>
        f.geometry?.coordinates?.length === 2 &&
        !(f.properties.gps_matched === false && !f.properties.manual_placement)
    )

    if (mappedFeatures.length === 0) {
      snapStatus.value = 'error'
      snapMessage.value = 'No hay marcadores ubicados en el mapa.'
      return
    }

    // Compute bounding box from all mapped markers
    let south = Infinity, north = -Infinity, west = Infinity, east = -Infinity
    for (const f of mappedFeatures) {
      const [lon, lat] = f.geometry.coordinates
      if (lat < south) south = lat
      if (lat > north) north = lat
      if (lon < west) west = lon
      if (lon > east) east = lon
    }

    snapStatus.value = 'loading'
    snapMessage.value = 'Descargando datos de la línea de costa...'

    let coastSegments
    try {
      coastSegments = await fetchCoastlineSegments(south, west, north, east)
    } catch (err) {
      snapStatus.value = 'error'
      snapMessage.value = `Error al obtener la costa: ${err.message}`
      console.error('[useCoastSnap] fetchCoastlineSegments error:', err)
      return
    }

    if (coastSegments.length === 0) {
      snapStatus.value = 'error'
      snapMessage.value = 'No se encontró línea de costa en el área de los marcadores.'
      return
    }

    snapStatus.value = 'snapping'
    snapMessage.value = `Calculando proyecciones sobre ${coastSegments.reduce((s, seg) => s + seg.length - 1, 0)} segmentos de costa...`

    // Allow UI to update before the CPU-intensive loop
    await new Promise((r) => setTimeout(r, 50))

    let snapped = 0
    for (const feature of mappedFeatures) {
      const [lon, lat] = feature.geometry.coordinates
      const nearest = nearestCoastPoint(lat, lon, coastSegments)
      if (nearest) {
        feature.geometry.coordinates = [nearest.lon, nearest.lat]
        feature.properties.manual_placement = true
        if (feature.properties.gps) {
          feature.properties.gps.latitude = nearest.lat
          feature.properties.gps.longitude = nearest.lon
        }
        snapped++
      }
    }

    renderMarkers()

    snapStatus.value = 'done'
    snapMessage.value = `✔ ${snapped} marcadores ajustados a la costa.`

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      snapStatus.value = ''
      snapMessage.value = ''
    }, 4000)
  }

  function dismissSnap() {
    snapStatus.value = ''
    snapMessage.value = ''
  }

  return {
    snapStatus,
    snapMessage,
    snapAllToCoast,
    dismissSnap,
  }
}
