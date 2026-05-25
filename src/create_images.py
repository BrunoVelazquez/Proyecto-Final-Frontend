import cv2
import json
from pathlib import Path

# 1. Configurar rutas relativas
ruta_base = Path("..")
carpeta_imagenes = ruta_base / "data" / "images"
carpeta_labels = ruta_base / "data" / "labels"
archivo_json = ruta_base / "data" / "notes.json"

carpeta_resultados_img = ruta_base / "resultados" / "imagenes_con_cajas"

# Crear carpeta de resultados si no existe
carpeta_resultados_img.mkdir(parents=True, exist_ok=True)

# 2. Cargar las clases desde notes.json
try:
    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos_json = json.load(f)
    diccionario_clases = {cat["id"]: cat["name"] for cat in datos_json["categories"]}
            
except Exception as e:
    print(f"Error al leer notes.json: {e}")
    exit()

# 3. --- PROCESAR TODAS LAS IMÁGENES EN LA CARPETA ---
# Buscamos archivos .jpg, .JPG, .png, etc. Podés agregar más extensiones si es necesario.
extensiones_validas = ["*.jpg", "*.JPG", "*.jpeg", "*.png"]
rutas_imagenes = []
for ext in extensiones_validas:
    rutas_imagenes.extend(carpeta_imagenes.glob(ext))

if not rutas_imagenes:
    print(f"No se encontraron imágenes en la carpeta: {carpeta_imagenes}")
    exit()

print(f"Se encontraron {len(rutas_imagenes)} imágenes. Iniciando procesamiento...")

for ruta_img in rutas_imagenes:
    # Buscar el archivo .txt correspondiente (mismo nombre, distinta extensión)
    ruta_txt_img = carpeta_labels / f"{ruta_img.stem}.txt"

    if ruta_img.exists() and ruta_txt_img.exists():
        img = cv2.imread(str(ruta_img))
        
        if img is not None:
            alto, ancho = img.shape[:2]
            
            with open(ruta_txt_img, 'r') as f:
                lineas = f.readlines()
                
            for linea in lineas:
                partes = linea.strip().split()
                if len(partes) != 5:
                    continue
                    
                class_id = int(partes[0])
                cx, cy, w, h = map(float, partes[1:])
                
                nombre_clase = diccionario_clases.get(class_id, f"ID_{class_id}")

                # Saltar negativo_dudoso (id 30), no dibujar su caja ni etiqueta
                if class_id == 30:
                    continue

                # Todas las cajas en verde flúor (sin distinción de color)
                color_caja = (0, 255, 0)
                
                # Desnormalizar coordenadas de YOLO a píxeles
                centro_x = int(cx * ancho)
                centro_y = int(cy * alto)
                ancho_caja = int(w * ancho)
                alto_caja = int(h * alto)
                
                x1 = int(centro_x - ancho_caja / 2)
                y1 = int(centro_y - alto_caja / 2)
                x2 = int(centro_x + ancho_caja / 2)
                y2 = int(centro_y + alto_caja / 2)
                
                # Dibujar caja y etiqueta
                cv2.rectangle(img, (x1, y1), (x2, y2), color_caja, 2)
                (w_texto, h_texto), _ = cv2.getTextSize(nombre_clase, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                cv2.rectangle(img, (x1, y1 - 25), (x1 + w_texto, y1), color_caja, -1)
                cv2.putText(img, nombre_clase, (x1, y1 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)

            # Guardar la imagen dibujada
            ruta_salida_img = carpeta_resultados_img / f"{ruta_img.name}"
            cv2.imwrite(str(ruta_salida_img), img)
            print(f"✅ Procesada y guardada: {ruta_salida_img.name}")
            
        else:
            print(f"⚠️ Error al abrir la imagen {ruta_img.name}. Revisá que no esté corrupta.")
    else:
        # Si no tiene un .txt asociado, la salteamos o avisamos.
        print(f"ℹ️ Omitiendo {ruta_img.name} (no se encontró su archivo .txt)")

print("\n¡Proceso finalizado con éxito!")