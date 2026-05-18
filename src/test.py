import sys
import os
from pathlib import Path
import pandas as pd

# Instalá esto si no lo tenés: pip install simplekml
try:
    import simplekml
except ImportError:
    print("Instalando simplekml...")
    os.system('pip install simplekml')
    import simplekml

# --- TRUCO PARA ESTRUCTURA ANIDADA ---
directorio_actual = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(directorio_actual, 'LCI'))

from LCI.pfi import get_photoplace

# 1. Configurar Rutas
carpeta_imagenes = Path("../data/images")
# Usamos el archivo .txt de GPS que mencionaste
ruta_gps_txt = Path("../data/datosGPS_censos_aereos_2023/20231004-130551 - Censo PV 2023.txt")
ruta_salida_kml = Path("../resultados/censo_peninsula_valdes.kml")

# Asegurar que exista la carpeta de resultados
ruta_salida_kml.parent.mkdir(parents=True, exist_ok=True)

# 2. Inicializar KML
kml = simplekml.Kml()
# Definimos el estilo del punto rojo grande
estilo_rojo = simplekml.Style()
estilo_rojo.iconstyle.icon.href = 'http://maps.google.com/mapfiles/kml/paddle/red-circle.png'
estilo_rojo.iconstyle.scale = 2  # Tamaño grande

# 3. Buscar imágenes
imagenes = list(carpeta_imagenes.glob("*.JPG"))
print(f"Procesando {len(imagenes)} imágenes para generar el KML...")

# 4. Procesar y Cruzar Datos
fotos_geolocalizadas = 0

for ruta_img in imagenes:
    try:
        # get_photoplace busca la coincidencia exacta de tiempo
        info_lugar = get_photoplace(str(ruta_img), str(ruta_gps_txt))
        
        if not info_lugar.empty:
            # Extraemos coordenadas (asumiendo nombres de columna estándar de GPS)
            # Si tus columnas se llaman distinto en el .txt, ajustá 'lat' y 'lon'
            lat = info_lugar.iloc[0]['latitude']
            lon = info_lugar.iloc[0]['longitude']
            
            # Crear punto en el KML
            pnt = kml.newpoint(name=ruta_img.name)
            pnt.coords = [(lon, lat)]
            pnt.style = estilo_rojo
            pnt.description = f"Foto: {ruta_img.name}\nFecha/Hora coincidente"
            
            fotos_geolocalizadas += 1
            print(f"✅ Ubicada: {ruta_img.name} -> Lat: {lat}, Lon: {lon}")
        else:
            print(f"⚠️ Sin coincidencia de hora para: {ruta_img.name}")
            
    except Exception as e:
        print(f"❌ Error procesando {ruta_img.name}: {e}")

# 5. Guardar Archivo
kml.save(str(ruta_salida_kml))

print(f"\n¡Listo! Se geolocalizaron {fotos_geolocalizadas} fotos.")
print(f"Archivo guardado en: {ruta_salida_kml.absolute()}")