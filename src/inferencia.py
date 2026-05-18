import sys
import os
from pathlib import Path

# --- EL TRUCO PARA MANTENER TU ESTRUCTURA ANIDADA ---
# Añadimos la primera carpeta 'LCI' al "radar" de Python para que
# pueda encontrar la segunda carpeta 'LCI' que está adentro.
directorio_actual = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(directorio_actual, 'LCI'))

# Ahora sí, esto va a funcionar sin errores de "ModuleNotFoundError"
from LCI.pfi import get_photoplace

from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

sys.path.append(directorio_actual)
# 1. Configurar rutas relativas a la carpeta 'src'
ruta_modelo = Path("../modelos/best.pt")
carpeta_imagenes = Path("../data/images")
carpeta_gps = Path("../data/datosGPS_censos_aereos_2023")
carpeta_resultados = Path("../resultados/predicciones_sahi")

# Asegurarse de que la carpeta de resultados exista
carpeta_resultados.mkdir(parents=True, exist_ok=True)

# 2. Cargar el modelo YOLOv8 a través de SAHI
print(f"Cargando el modelo desde: {ruta_modelo}")
detection_model = AutoDetectionModel.from_pretrained(
    model_type='yolov8',
    model_path=str(ruta_modelo),
    confidence_threshold=0.3, # Ajustá este valor si detecta mucha basura
    device="cuda:0" # Cambiá a "cpu" si tu compu no tiene placa de video NVIDIA
)

# 3. Buscar todas las imágenes .JPG en la carpeta
imagenes = list(carpeta_imagenes.glob("*.JPG"))
print(f"Se encontraron {len(imagenes)} imágenes para procesar.")

# 4. Procesar en lote (Batch)
for ruta_imagen in imagenes:
    print(f"Procesando: {ruta_imagen.name}...")
    
    # ---------------------------------------------------------
    # EJEMPLO DE USO DE LA FUNCIÓN DE GEOLOCALIZACIÓN

    ruta_label = carpeta_gps / ("20231004-130551 - Censo PV 2023.txt")

    info_lugar = get_photoplace(str(ruta_imagen), str(ruta_label))
    print("info_lugar")
    print(info_lugar)
    # ---------------------------------------------------------

    # SAHI corta la imagen, predice, y une las predicciones
    resultado = get_sliced_prediction(
        str(ruta_imagen),
        detection_model,
        slice_height=512, # Tamaño del parche
        slice_width=512,
        overlap_height_ratio=0.2, # Superposición 
        overlap_width_ratio=0.2
    )

    # 5. Exportar la imagen con las cajas (bounding boxes) dibujadas
    resultado.export_visuals(
        export_dir=str(carpeta_resultados), 
        file_name=ruta_imagen.stem # Usa el nombre original sin el .JPG
    )

print(f"\n¡Inferencia completada! Podés ver los resultados en: {carpeta_resultados}")