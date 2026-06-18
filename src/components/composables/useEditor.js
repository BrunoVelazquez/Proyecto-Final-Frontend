// components/composables/useEditor.js
import { ref, computed, nextTick, watch } from 'vue'

export function useEditor({ getCategoryColor, availableCategories, getImageUrl }) {
  // --- Estados del Editor Canvas ---
  const currentEditingImage = ref(null)
  const currentImageFeatures = ref([])
  const selectedBoxIndex = ref(-1)
  const editorTool = ref('select')
  const saveStatus = ref('')
  const showCharts = ref(false)

  // Referencias del DOM para el Canvas
  const canvasWrap = ref(null)
  const editorCanvas = ref(null)
  let ctx = null
  let imgObj = null
  let imgNat = { w: 1, h: 1 }

  // Variables de vista de la cámara del Canvas
  const scale = ref(1)
  const panX = ref(0)
  const panY = ref(0)

  // Estados de interacción del ratón
  const hoveredIdx = ref(-1)
  const drag = { active: false, type: null, idx: -1, sx: 0, sy: 0, ox: 0, oy: 0, obox: [] }
  const drawing = { active: false, sx: 0, sy: 0, ex: 0, ey: 0 }

  function openEditor(properties) {
    currentEditingImage.value = properties.image_name
    currentImageFeatures.value = JSON.parse(JSON.stringify(properties.detections))
    selectedBoxIndex.value = -1
    editorTool.value = 'select'
    saveStatus.value = ''
    showCharts.value = false

    nextTick(() => {
      if (!editorCanvas.value) return
      ctx = editorCanvas.value.getContext('2d')
      imgObj = new Image()
      imgObj.onload = () => {
        imgNat.w = imgObj.naturalWidth
        imgNat.h = imgObj.naturalHeight
        fitImage()
        renderCanvas()
      }
      imgObj.src = getImageUrl(properties.image_name)
    })
  }

  function fitImage() {
    if (!canvasWrap.value || !editorCanvas.value) return
    const W = canvasWrap.value.clientWidth
    const H = canvasWrap.value.clientHeight
    editorCanvas.value.width = W
    editorCanvas.value.height = H

    const scaleX = W / imgNat.w
    const scaleY = H / imgNat.h
    scale.value = Math.min(scaleX, scaleY) * 0.92
    panX.value = (W - imgNat.w * scale.value) / 2
    panY.value = (H - imgNat.h * scale.value) / 2
  }

  const absToCanvas = (x, y) => ({ x: x * scale.value + panX.value, y: y * scale.value + panY.value })
  const canvasToAbs = (cx, cy) => ({
    x: (cx - panX.value) / scale.value,
    y: (cy - panY.value) / scale.value,
  })

  function renderCanvas() {
    if (!ctx || !imgObj || !editorCanvas.value) {
      return
    }
    const W = editorCanvas.value.width
    const H = editorCanvas.value.height
    ctx.clearRect(0, 0, W, H)

    ctx.drawImage(imgObj, panX.value, panY.value, imgNat.w * scale.value, imgNat.h * scale.value)

    currentImageFeatures.value.forEach((b, i) => {
      const color = getCategoryColor(b.category)
      const [xmin, ymin, xmax, ymax] = b.bbox

      const tl = absToCanvas(xmin, ymin)
      const br = absToCanvas(xmax, ymax)
      const bw = br.x - tl.x
      const bh = br.y - tl.y

      const isHovered = i === hoveredIdx.value
      const isSelected = i === selectedBoxIndex.value

      if (isSelected) {
        ctx.fillStyle = color + '22'
        ctx.fillRect(tl.x, tl.y, bw, bh)
      }

      ctx.strokeStyle = color
      ctx.lineWidth = isSelected ? 2.5 : isHovered ? 2 : 1.5
      ctx.strokeRect(tl.x, tl.y, bw, bh)

      const label = b.category
      ctx.font = '11px system-ui'
      const tw = ctx.measureText(label).width
      ctx.fillStyle = color + 'cc'
      ctx.fillRect(tl.x, tl.y - 16, tw + 6, 16)
      ctx.fillStyle = '#000'
      ctx.fillText(label, tl.x + 3, tl.y - 3)

      if (isSelected) drawHandles(tl.x, tl.y, bw, bh, color)
    })

    if (drawing.active) {
      ctx.strokeStyle = '#1D9E75'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 3])
      ctx.strokeRect(
        Math.min(drawing.sx, drawing.ex),
        Math.min(drawing.sy, drawing.ey),
        Math.abs(drawing.ex - drawing.sx),
        Math.abs(drawing.ey - drawing.sy),
      )
      ctx.setLineDash([])
    }
  }

  function drawHandles(x, y, w, h, color) {
    const pts = [
      [x, y],
      [x + w / 2, y],
      [x + w, y],
      [x, y + h / 2],
      [x + w, y + h / 2],
      [x, y + h],
      [x + w / 2, y + h],
      [x + w, y + h],
    ]
    pts.forEach(([hx, hy]) => {
      ctx.fillStyle = color
      ctx.fillRect(hx - 4, hy - 4, 8, 8)
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 1
      ctx.strokeRect(hx - 4, hy - 4, 8, 8)
    })
  }

  watch([selectedBoxIndex, currentImageFeatures], () => renderCanvas(), { deep: true })

  function getMousePos(e) {
    const rect = editorCanvas.value.getBoundingClientRect()
    return { cx: e.clientX - rect.left, cy: e.clientY - rect.top }
  }

  function handleWheel(e) {
    const { cx, cy } = getMousePos(e)
    const factor = e.deltaY < 0 ? 1.12 : 0.89
    panX.value = cx - (cx - panX.value) * factor
    panY.value = cy - (cy - panY.value) * factor
    scale.value *= factor
    renderCanvas()
  }

  function handleMouseDown(e) {
    const { cx, cy } = getMousePos(e)

    if (editorTool.value === 'draw') {
      drawing.active = true
      drawing.sx = cx
      drawing.sy = cy
      drawing.ex = cx
      drawing.ey = cy
      return
    }

    if (selectedBoxIndex.value >= 0) {
      const h = hitHandle(cx, cy, selectedBoxIndex.value)
      if (h) {
        const bbox = currentImageFeatures.value[selectedBoxIndex.value].bbox
        drag.active = true
        drag.type = 'resize'
        drag.idx = selectedBoxIndex.value
        drag.handle = h
        drag.sx = cx
        drag.sy = cy
        drag.obox = [...bbox]
        return
      }
    }

    const hit = hitBox(cx, cy)
    if (hit >= 0) {
      selectedBoxIndex.value = hit
      const bbox = currentImageFeatures.value[hit].bbox
      drag.active = true
      drag.type = 'move'
      drag.idx = hit
      drag.sx = cx
      drag.sy = cy
      drag.obox = [...bbox]
      renderCanvas()
      return
    }

    selectedBoxIndex.value = -1
    drag.active = true
    drag.type = 'pan'
    drag.sx = cx
    drag.sy = cy
    drag.ox = panX.value
    drag.oy = panY.value
    renderCanvas()
  }

  function handleMouseMove(e) {
    const { cx, cy } = getMousePos(e)

    if (drawing.active) {
      drawing.ex = cx
      drawing.ey = cy
      renderCanvas()
      return
    }

    if (drag.active) {
      const dx = cx - drag.sx
      const dy = cy - drag.sy
      const dxAbs = dx / scale.value
      const dyAbs = dy / scale.value

      if (drag.type === 'pan') {
        panX.value = drag.ox + dx
        panY.value = drag.oy + dy
      } else if (drag.type === 'move') {
        const b = currentImageFeatures.value[drag.idx].bbox
        b[0] = drag.obox[0] + dxAbs
        b[1] = drag.obox[1] + dyAbs
        b[2] = drag.obox[2] + dxAbs
        b[3] = drag.obox[3] + dyAbs
      } else if (drag.type === 'resize') {
        let [xmin, ymin, xmax, ymax] = drag.obox
        if (drag.handle.includes('l')) xmin = Math.min(xmax - 1, drag.obox[0] + dxAbs)
        if (drag.handle.includes('r')) xmax = Math.max(xmin + 1, drag.obox[2] + dxAbs)
        if (drag.handle.includes('t')) ymin = Math.min(ymax - 1, drag.obox[1] + dyAbs)
        if (drag.handle.includes('b')) ymax = Math.max(ymin + 1, drag.obox[3] + dyAbs)
        currentImageFeatures.value[drag.idx].bbox = [xmin, ymin, xmax, ymax]
      }
      renderCanvas()
      return
    }

    const newHover = hitBox(cx, cy)
    if (newHover !== hoveredIdx.value) {
      hoveredIdx.value = newHover
      renderCanvas()
    }
    canvasWrap.value.style.cursor =
      editorTool.value === 'draw' ? 'crosshair' : newHover >= 0 ? 'pointer' : 'default'
  }

  function handleMouseUp(e) {
    if (drawing.active) {
      const { cx, cy } = getMousePos(e)
      if (Math.abs(cx - drawing.sx) > 8 && Math.abs(cy - drawing.sy) > 8) {
        const p1 = canvasToAbs(drawing.sx, drawing.sy)
        const p2 = canvasToAbs(cx, cy)
        const xmin = Math.min(p1.x, p2.x)
        const ymin = Math.min(p1.y, p2.y)
        const xmax = Math.max(p1.x, p2.x)
        const ymax = Math.max(p1.y, p2.y)

        const cat = availableCategories.value[0] || 'default'
        currentImageFeatures.value.push({ category: cat, score: 1.0, bbox: [xmin, ymin, xmax, ymax] })
        selectedBoxIndex.value = currentImageFeatures.value.length - 1
        editorTool.value = 'select'
      }
    }
    drag.active = false
    drawing.active = false
    renderCanvas()
  }

  function handleMouseLeave() {
    drag.active = false
    drawing.active = false
    hoveredIdx.value = -1
    renderCanvas()
  }

  function hitBox(cx, cy) {
    for (let i = currentImageFeatures.value.length - 1; i >= 0; i--) {
      const [xmin, ymin, xmax, ymax] = currentImageFeatures.value[i].bbox
      const tl = absToCanvas(xmin, ymin)
      const br = absToCanvas(xmax, ymax)
      if (cx >= tl.x && cx <= br.x && cy >= tl.y && cy <= br.y) return i
    }
    return -1
  }

  const HANDLE_NAMES = ['tl', 'tc', 'tr', 'ml', 'mr', 'bl', 'bc', 'br']
  function hitHandle(cx, cy, idx) {
    const [xmin, ymin, xmax, ymax] = currentImageFeatures.value[idx].bbox
    const tl = absToCanvas(xmin, ymin)
    const br = absToCanvas(xmax, ymax)
    const pts = [
      [tl.x, tl.y],
      [(tl.x + br.x) / 2, tl.y],
      [br.x, tl.y],
      [tl.x, (tl.y + br.y) / 2],
      [br.x, (tl.y + br.y) / 2],
      [tl.x, br.y],
      [(tl.x + br.x) / 2, br.y],
      [br.x, br.y],
    ]
    for (let i = 0; i < pts.length; i++) {
      if (Math.abs(cx - pts[i][0]) < 7 && Math.abs(cy - pts[i][1]) < 7) return HANDLE_NAMES[i]
    }
    return null
  }

  function removeBox(index) {
    currentImageFeatures.value.splice(index, 1)
    if (selectedBoxIndex.value === index) selectedBoxIndex.value = -1
    else if (selectedBoxIndex.value > index) selectedBoxIndex.value--
  }

  function closeEditor() {
    currentEditingImage.value = null

    ctx = null
    imgObj = null

    selectedBoxIndex.value = -1
    hoveredIdx.value = -1

    showCharts.value = false
  }

  // ── Computed para estadísticas de detección ──
  const detectionStats = computed(() => {
    const stats = {}
    currentImageFeatures.value.forEach((b) => {
      stats[b.category] = (stats[b.category] || 0) + 1
    })
    return Object.entries(stats)
      .map(([cat, count]) => ({
        category: cat,
        count: count,
        color: getCategoryColor(cat),
      }))
      .sort((a, b) => b.count - a.count)
  })

  const totalDetections = computed(() => currentImageFeatures.value.length)

  // ── Guardar cambios (no cierra el modal) ──
  async function saveChanges() {
    saveStatus.value = 'Guardando...'
    try {
      // Simulación de guardado - reemplazar con tu endpoint real
      await new Promise((r) => setTimeout(r, 500))
      saveStatus.value = `✅ ${currentImageFeatures.value.length} detecciones guardadas`
      setTimeout(() => {
        saveStatus.value = ''
      }, 3000)
    } catch (error) {
      saveStatus.value = '❌ Error al guardar'
      console.error(error)
    }
  }

  // ── Cambiar categoría del objeto seleccionado ──
  function changeSelectedCategory(newCat) {
    if (selectedBoxIndex.value >= 0 && currentImageFeatures.value[selectedBoxIndex.value]) {
      currentImageFeatures.value[selectedBoxIndex.value].category = newCat
    }
  }

  return {
    // Estado
    currentEditingImage,
    currentImageFeatures,
    selectedBoxIndex,
    editorTool,
    saveStatus,
    showCharts,
    // DOM refs
    canvasWrap,
    editorCanvas,
    // Computed
    detectionStats,
    totalDetections,
    // Métodos
    openEditor,
    closeEditor,
    handleWheel,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleMouseLeave,
    removeBox,
    changeSelectedCategory,
    saveChanges,
  }
}
