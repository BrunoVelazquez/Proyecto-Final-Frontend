/**
 * trajectoryUtils.js
 * Utilities for GPS trajectory parsing and time-offset photo geolocation.
 */

/**
 * Parse a GPS Logger TXT file content (CSV format) into an array of row objects.
 * Skips rows where `type !== 'T'`.
 *
 * @param {string} fileContent - Raw text content of the GPS logger .txt file.
 * @returns {Array<Object>} Array of GPS rows: { 'date time', latitude, longitude, ... }
 */
export function parseTrajectoryCSV(fileContent) {
  const lines = fileContent.split(/\r?\n/).filter(l => l.trim() !== '')
  if (lines.length < 2) return []

  const headers = lines[0].split(',').map(h => h.trim())
  const rows = []

  for (let i = 1; i < lines.length; i++) {
    const parts = lines[i].split(',')
    if (parts.length < headers.length) continue

    const row = {}
    headers.forEach((h, idx) => {
      row[h] = parts[idx]?.trim() ?? ''
    })

    // Only keep track points (type 'T'), skip waypoints and others
    if (row['type'] !== 'T') continue

    row.latitude = parseFloat(row.latitude)
    row.longitude = parseFloat(row.longitude)

    rows.push(row)
  }

  return rows
}

/**
 * Add N seconds to a "YYYY-MM-DD HH:MM:SS" string and return the new string.
 *
 * @param {string} timestamp - "YYYY-MM-DD HH:MM:SS"
 * @param {number} offsetSeconds - positive or negative integer
 * @returns {string} New timestamp string "YYYY-MM-DD HH:MM:SS"
 */
export function shiftTimestamp(timestamp, offsetSeconds) {
  // Parse as naive string components and reconstruct as UTC for arithmetic.
  // This avoids browser DST/timezone applying to naive local time strings.
  const [datePart, timePart] = timestamp.split(' ')
  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, minute, second] = timePart.split(':').map(Number)

  // Build an ISO string with 'Z' so Date parses it as UTC (pure offset arithmetic)
  const isoStr = `${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}T${String(hour).padStart(2,'0')}:${String(minute).padStart(2,'0')}:${String(second).padStart(2,'0')}Z`
  const date = new Date(isoStr)
  date.setTime(date.getTime() + offsetSeconds * 1000)

  const yyyy = date.getUTCFullYear()
  const mm = String(date.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(date.getUTCDate()).padStart(2, '0')
  const hh = String(date.getUTCHours()).padStart(2, '0')
  const min = String(date.getUTCMinutes()).padStart(2, '0')
  const ss = String(date.getUTCSeconds()).padStart(2, '0')

  return `${yyyy}-${mm}-${dd} ${hh}:${min}:${ss}`
}

/**
 * Find the GPS row in the trajectory that best matches a given timestamp + offset.
 * Tries exact match first, then falls back to the closest row within ±5 seconds.
 *
 * @param {string} gpsTimestamp - Original "YYYY-MM-DD HH:MM:SS" from gps.timestamp
 * @param {Array<Object>} trajectoryData - Parsed GPS rows from parseTrajectoryCSV()
 * @param {number} offsetSeconds - The time correction to apply (positive = later, negative = earlier)
 * @returns {{ latitude: number, longitude: number, 'date time': string } | null}
 */
export function getPhotoPlace(gpsTimestamp, trajectoryData, offsetSeconds = 0) {
  if (!gpsTimestamp || !trajectoryData?.length) return null

  const targetTime = shiftTimestamp(gpsTimestamp, offsetSeconds)

  // Exact match
  const exact = trajectoryData.find(row => row['date time'] === targetTime)
  if (exact) return exact

  // Closest match fallback
  const targetMs = new Date(targetTime.replace(' ', 'T') + 'Z').getTime()
  let best = null
  let bestDiff = Infinity

  for (const row of trajectoryData) {
    const rowMs = new Date(row['date time'].replace(' ', 'T') + 'Z').getTime()
    const diff = Math.abs(rowMs - targetMs)
    if (diff < bestDiff) {
      bestDiff = diff
      best = row
    }
  }

  // Return closest match within 12 hours (covers timezone-sized offsets during calibration)
  return bestDiff <= 43200000 ? best : null
}

/**
 * Format seconds as ±h:mm:ss label for the slider.
 * @param {number} seconds
 * @returns {string} e.g. "+1:05:30" or "-00:02:15"
 */
export function formatOffsetLabel(seconds) {
  const sign = seconds >= 0 ? '+' : '-'
  const abs = Math.abs(seconds)
  const hh = Math.floor(abs / 3600)
  const mm = String(Math.floor((abs % 3600) / 60)).padStart(2, '0')
  const ss = String(abs % 60).padStart(2, '0')
  return hh > 0 ? `${sign}${hh}:${mm}:${ss}` : `${sign}${mm}:${ss}`
}
