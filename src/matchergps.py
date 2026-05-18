import sys
import os
from pathlib import Path

# --- EL TRUCO PARA MANTENER TU ESTRUCTURA ANIDADA ---
# Añadimos la primera carpeta 'LCI' al "radar" de Python para que
# pueda encontrar la segunda carpeta 'LCI' que está adentro.
directorio_actual = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(directorio_actual, 'LCI'))

# Importamos la función de geolocalización de tu paquete
from LCI.pfi import get_photoplace

# Restauramos el path original por las dudas
sys.path.append(directorio_actual)

# ==============================================================================
# SCRIPT DE EXTRACCIÓN DE COORDENADAS
# ==============================================================================

# 1. Configurar las rutas
carpeta_imagenes = Path("../data/images")
ruta_gps_txt = Path("../data/datosGPS_censos_aereos_2023/20231004-130551 - Censo PV 2023.txt")

# 2. Buscar todas las imágenes .JPG
imagenes = list(carpeta_imagenes.glob("*.JPG"))
print(f"Se encontraron {len(imagenes)} imágenes para procesar.\n")
print("-" * 50)

# 3. Procesar cada imagen en lote
for ruta_imagen in imagenes:
    print(f"📷 Imagen: {ruta_imagen.name}")
    
    try:
        # Llamar a la función de tu paquete
        info_lugar = get_photoplace(str(ruta_imagen), str(ruta_gps_txt))
        
        # Como devuelve un DataFrame de Pandas, sacamos el primer valor (.iloc[0])
        latitud = info_lugar['latitude'].iloc[0]
        longitud = info_lugar['longitude'].iloc[0]
        
        print(f"📍 Coordenadas: Latitud {latitud:.6f}, Longitud {longitud:.6f}")
        
    except Exception as e:
        # Si la foto no tiene metadatos de hora o no está en el TXT, te avisa
        print(f"❌ Error al obtener el GPS: {e}")
        
    print("-" * 50)

print("¡Proceso finalizado!")