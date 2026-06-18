<script setup>
import 'leaflet/dist/leaflet.css'
import BaseMap from './components/BaseMap.vue'
</script>

<template>
  <BaseMap />
</template>

<style>
/* ═══════════════════════════════════════════════════════ */
/*  ESTILOS POPUPS - globales porque Leaflet inyecta el     */
/*  contenido fuera del árbol de componentes Vue (sin       */
/*  scoping, por eso van en App.vue sin "scoped")           */
/* ═══════════════════════════════════════════════════════ */
.custom-map-popup h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  font-family: monospace;
  color: #333;
  word-break: break-all;
}
.popup-image-frame {
  width: 100%;
  height: 110px;
  background: #eaeaea;
  border-radius: 6px;
  overflow: hidden;
  margin-bottom: 8px;
  border: 1px solid #ddd;
}
.popup-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.popup-total {
  font-size: 12px;
  margin: 4px 0;
  color: #555;
}
.popup-classes-list {
  list-style: none;
  padding: 0;
  margin: 6px 0;
  max-height: 80px;
  overflow-y: auto;
  font-size: 11px;
}
.popup-classes-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
}
.popup-classes-list .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.popup-action-btn {
  background-color: #1d9e75;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 8px 0;
  width: 100%;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 5px;
}
.popup-action-btn:hover {
  background-color: #178a64;
}

body,
html,
#app {
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}
</style>
