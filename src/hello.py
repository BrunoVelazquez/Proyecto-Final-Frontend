import sys
import json
import kml2geojson
from PyQt6 import QtCore, QtWidgets, QtGui
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QPushButton, QMainWindow, QWidget, QFileDialog, QMessageBox, QDialog, QLabel, QVBoxLayout
from pathlib import Path

class Comunicador(QtCore.QObject):
    pin_seleccionado = QtCore.pyqtSignal(dict)

    @QtCore.pyqtSlot(str)
    def pinClickeado(self, datos_json):
        datos = json.loads(datos_json)
        self.pin_seleccionado.emit(datos)


class VisorImagen(QDialog):
    def __init__(self, ruta_imagen, titulo_pin, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Imagen: {titulo_pin}")
        self.resize(800, 600)
        
        layout = QVBoxLayout(self)
        
        
        self.escena = QtWidgets.QGraphicsScene(self)
        self.vista = QtWidgets.QGraphicsView(self.escena)
        

        self.vista.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        self.vista.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        
        self.vista.setDragMode(QtWidgets.QGraphicsView.DragMode.ScrollHandDrag)
        
        layout.addWidget(self.vista)
        
        pixmap = QtGui.QPixmap(ruta_imagen)
        
        if pixmap.isNull():
            self.label_error = QLabel("No se pudo cargar la imagen.", self)
            self.label_error.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(self.label_error)
            self.vista.hide()
        else:
            self.item_pixmap = self.escena.addPixmap(pixmap)
            self.vista.fitInView(self.item_pixmap, QtCore.Qt.AspectRatioMode.KeepAspectRatio)
            
        self.vista.wheelEvent = self.evento_rueda_zoom

    def evento_rueda_zoom(self, evento):
        evento.accept()
        
        if evento.angleDelta().y() > 0:
            factor_zoom = 1.25
        else:
            factor_zoom = 0.8
            
        self.vista.scale(factor_zoom, factor_zoom)
        
    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'item_pixmap'):
            self.vista.fitInView(self.item_pixmap, QtCore.Qt.AspectRatioMode.KeepAspectRatio)


HTML_MAPA = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        #map { width: 100%; height: 100vh; }
        .leaflet-control-zoom a { background-color: #2b2b2b !important; color: white !important; border: 1px solid #444 !important; }
        .leaflet-control-zoom a:hover { background-color: #3b3b3b !important; color: #0078A8 !important; }
    </style>
</head>
<body>
    <div id="map"></div>
    <script>
        var map = L.map('map', { zoomControl: false }).setView([-42.5166667, -63.9166667], 8);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '© OpenStreetMap' }).addTo(map);
        L.control.zoom({ position: 'topright' }).addTo(map);

        window.kmlLayers = [];
        var backend_python = null;

        new QWebChannel(qt.webChannelTransport, function(channel) {
            backend_python = channel.objects.comunicador;
        });

        window.cargarGeoJSON = function(data) {
            var layer = L.geoJSON(data, {
                style: function(feature) {
                    return { color: '#0078A8', weight: 3, opacity: 0.8 };
                },
                onEachFeature: function(feature, layer) {
                    layer.on('click', function(e) {
                        var info = {
                            tipo: feature.geometry.type,
                            propiedades: feature.properties,
                            latitud: e.latlng.lat,
                            longitud: e.latlng.lng
                        };
                        if (backend_python) {
                            backend_python.pinClickeado(JSON.stringify(info));
                        }
                    });
                }
            }).addTo(map);
            window.kmlLayers.push(layer);
            map.flyToBounds(layer.getBounds(), { padding: [50, 50], duration: 1.5 });
        };

        window.eliminarCapas = function() {
            window.kmlLayers.forEach(function(layer) { map.removeLayer(layer); });
            window.kmlLayers = [];
        };
    </script>
</body>
</html>
"""

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proyecto Final")
        self.resize(800, 600)

        self.web_view = QWebEngineView()
        self.setCentralWidget(self.web_view)

        self.canal = QWebChannel()
        self.comunicador = Comunicador()
        self.canal.registerObject("comunicador", self.comunicador)
        self.web_view.page().setWebChannel(self.canal)
        self.comunicador.pin_seleccionado.connect(self.mostrar_info_pin)

        self.web_view.setHtml(HTML_MAPA)

        self.button_container = QWidget(self.web_view)
        self.btnNewCampaign = QPushButton("Subir nueva campaña (Cargar KML)")
        self.btnRemoveCampaign = QPushButton("Eliminar recorrido")

        estilo_botones = """
            QPushButton { background-color: #2b2b2b; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #3b3b3b; }
            QPushButton:disabled { background-color: #555555; color: #aaaaaa; }
        """
        self.btnNewCampaign.setStyleSheet(estilo_botones)
        self.btnRemoveCampaign.setStyleSheet(estilo_botones)
        self.btnNewCampaign.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.btnRemoveCampaign.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

        self.btnNewCampaign.clicked.connect(self.cargar_kml)
        self.btnRemoveCampaign.clicked.connect(self.eliminar_recorrido)

        button_layout = QtWidgets.QHBoxLayout(self.button_container)
        button_layout.addWidget(self.btnNewCampaign)
        button_layout.addWidget(self.btnRemoveCampaign)
        button_layout.setContentsMargins(20, 10, 20, 20)
        button_layout.setSpacing(15)

    def mostrar_info_pin(self, datos):
        nombre = datos.get('propiedades', {}).get('name', 'Punto seleccionado')
        
        carpeta_imagenes = Path("..") / "resultados" / "imagenes_con_cajas"
        
        ruta_imagen = carpeta_imagenes / nombre
        
        if ruta_imagen.exists():
            self.visor = VisorImagen(str(ruta_imagen), nombre, self)
            self.visor.show()
        else:
            QtWidgets.QMessageBox.warning(
                self, 
                "Imagen no encontrada", 
                f"No se encontró ninguna imagen en la ruta:\n{ruta_imagen.resolve()}"
            )

    def cargar_kml(self):
        self.btnNewCampaign.setEnabled(False)
        try:
            ruta_archivo, _ = QFileDialog.getOpenFileName(self, "Seleccionar Archivo KML", "", "Archivos KML (*.kml)")
            if not ruta_archivo:
                return

            geojson_dict_list = kml2geojson.main.convert(ruta_archivo)
            geojson_data = json.dumps(geojson_dict_list[0])
            self.web_view.page().runJavaScript(f"window.cargarGeoJSON({geojson_data})")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar el archivo KML:\n{str(e)}")
        finally:
            self.btnNewCampaign.setEnabled(True)

    def eliminar_recorrido(self):
        self.web_view.page().runJavaScript("window.eliminarCapas()")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        container_height = 80
        self.button_container.setGeometry(
            0, self.web_view.height() - container_height, self.web_view.width(), container_height
        )

if __name__ == "__main__":
    sys.argv.append("--disable-gpu") 
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec())