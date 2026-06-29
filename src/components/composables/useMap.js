// components/composables/useMap.js
import L from 'leaflet'
import { shallowRef, onMounted } from 'vue'

export function useMap(mapContainerRef) {
  const map = shallowRef()
  const markersLayerGroup = shallowRef(L.layerGroup())

  onMounted(() => {
    map.value = L.map(mapContainerRef.value, { zoomControl: false }).setView(
      [-40.253607149186045, -64.14643163026199],
      4.3,
    )

    const ignLayer = L.tileLayer(
      'https://wms.ign.gob.ar/geoserver/gwc/service/tms/1.0.0/capabaseargenmap@EPSG%3A3857@png/{z}/{x}/{-y}.png',
      {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.ign.gob.ar/AreaServicios/Argenmap" target="_blank">IGN Argentina</a>',
      }
    )

    const esriLayer = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 19,
        attribution: '&copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
      }
    )

    ignLayer.addTo(map.value)

    const baseMaps = {
      'Argenmap (IGN)': ignLayer,
      'Esri Satélite': esriLayer,
    }

    L.control.zoom({ position: 'bottomright' }).addTo(map.value)
    L.control.layers(baseMaps, null, { position: 'bottomright' }).addTo(map.value)
    markersLayerGroup.value.addTo(map.value)

    setTimeout(() => {
      if (map.value) map.value.invalidateSize()
    }, 200)
  })

  return { map, markersLayerGroup }
}
