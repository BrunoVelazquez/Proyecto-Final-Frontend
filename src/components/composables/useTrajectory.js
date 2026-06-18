// components/composables/useTrajectory.js
import { ref } from 'vue'
import { parseTrajectoryCSV, getPhotoPlace } from '../../utils/trajectoryUtils.js'

export function useTrajectory() {
  const trajectoryData = ref([])
  const trajectoryLoaded = ref(false)
  const trajectoryError = ref(null)

  /**
   * Read and parse a GPS logger File object.
   * @param {File} file
   */
  function loadTrajectory(file) {
    return new Promise((resolve, reject) => {
      trajectoryError.value = null
      const reader = new FileReader()

      reader.onload = (e) => {
        try {
          const content = e.target.result
          trajectoryData.value = parseTrajectoryCSV(content)
          trajectoryLoaded.value = trajectoryData.value.length > 0
          if (!trajectoryLoaded.value) {
            trajectoryError.value = 'No se encontraron puntos GPS en el archivo.'
          }
          resolve(trajectoryData.value)
        } catch (err) {
          trajectoryError.value = 'Error al parsear el archivo GPS.'
          reject(err)
        }
      }

      reader.onerror = () => {
        trajectoryError.value = 'Error al leer el archivo.'
        reject(new Error('FileReader error'))
      }

      reader.readAsText(file)
    })
  }

  /**
   * Given the original GPS timestamp of a feature, get the [lat, lng] position at offset.
   * @param {string} gpsTimestamp - from feature.properties.gps.timestamp
   * @param {number} offsetSeconds
   * @returns {{ lat: number, lng: number } | null}
   */
  function getPositionAtOffset(gpsTimestamp, offsetSeconds) {
    const row = getPhotoPlace(gpsTimestamp, trajectoryData.value, offsetSeconds)
    if (!row) return null
    return { lat: row.latitude, lng: row.longitude }
  }

  function clearTrajectory() {
    trajectoryData.value = []
    trajectoryLoaded.value = false
    trajectoryError.value = null
  }

  return {
    trajectoryData,
    trajectoryLoaded,
    trajectoryError,
    loadTrajectory,
    getPositionAtOffset,
    clearTrajectory,
  }
}
