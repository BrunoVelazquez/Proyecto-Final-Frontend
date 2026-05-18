import cv2
import json
from pathlib import Path
import matplotlib.pyplot as plt
from collections import Counter

# 1. Configurar rutas relativas
ruta_base = Path("..")
carpeta_imagenes = ruta_base / "data" / "images"
carpeta_labels = ruta_base / "data" / "labels"
archivo_json = ruta_base / "data" / "notes.json"

carpeta_resultados_img = ruta_base / "resultados" / "imagenes_con_cajas"
carpeta_resultados_hist = ruta_base / "resultados" / "histogramas"

# Crear carpetas si no existen
carpeta_resultados_img.mkdir(parents=True, exist_ok=True)
carpeta_resultados_hist.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# DEFINÍ ACÁ LA ÚNICA IMAGEN QUE QUERÉS DIBUJAR
IMAGEN_A_PROCESAR = "096be103__b5c870e2-_DSC2119.JPG" 
# ---------------------------------------------------------

# 2. Cargar las clases desde notes.json
try:
    with open(archivo_json, 'r', encoding='utf-8') as f:
        datos_json = json.load(f)
    diccionario_clases = {cat["id"]: cat["name"] for cat in datos_json["categories"]}
            
except Exception as e:
    print(f"Error al leer notes.json: {e}")
    exit()

# 3. --- LECTURA GLOBAL (Para el histograma general) ---
conteo_general = Counter()
print("Leyendo todas las etiquetas para el histograma general...")

for ruta_txt in carpeta_labels.glob("*.txt"):
    with open(ruta_txt, 'r') as f:
        for linea in f.readlines():
            partes = linea.strip().split()
            if len(partes) == 5:
                class_id = int(partes[0])
                nombre_clase = diccionario_clases.get(class_id, f"ID_{class_id}")
                conteo_general[nombre_clase] += 1

# 4. --- PROCESAR SOLO LA IMAGEN ESPECIFICADA ---
ruta_img = carpeta_imagenes / IMAGEN_A_PROCESAR
ruta_txt_img = carpeta_labels / f"{ruta_img.stem}.txt"

if ruta_img.exists() and ruta_txt_img.exists():
    print(f"\nProcesando imagen única: {IMAGEN_A_PROCESAR}")
    img = cv2.imread(str(ruta_img))
    
    if img is not None:
        alto, ancho = img.shape[:2]
        conteo_local = Counter()
        
        with open(ruta_txt_img, 'r') as f:
            lineas = f.readlines()
            
        for linea in lineas:
            partes = linea.strip().split()
            if len(partes) != 5:
                continue
                
            class_id = int(partes[0])
            cx, cy, w, h = map(float, partes[1:])
            
            nombre_clase = diccionario_clases.get(class_id, f"ID_{class_id}")
            conteo_local[nombre_clase] += 1

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
        ruta_salida_img = carpeta_resultados_img / f"box_{ruta_img.name}"
        cv2.imwrite(str(ruta_salida_img), img)
        print(f"✅ Imagen con cajas guardada en: {ruta_salida_img.name}")
        
        # --- Generar el histograma INDIVIDUAL de esta foto ---
        if conteo_local:
            plt.figure(figsize=(10, 6))
            plt.bar(conteo_local.keys(), conteo_local.values(), color='coral')
            plt.title(f'Conteo de clases en {ruta_img.name}')
            plt.xlabel('Clases')
            plt.ylabel('Cantidad')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            ruta_hist_local = carpeta_resultados_hist / f"hist_{ruta_img.stem}.png"
            plt.savefig(ruta_hist_local)
            plt.close()
            print(f"📊 Histograma individual guardado en: {ruta_hist_local.name}")
    else:
        print(f"⚠️ Error al abrir la imagen {IMAGEN_A_PROCESAR}. Revisá que no esté corrupta.")
else:
    print(f"⚠️ No se encontró la imagen {IMAGEN_A_PROCESAR} o su archivo .txt correspondiente.")

# 5. --- GENERAR EL HISTOGRAMA GENERAL ---
if conteo_general:
    print("\nGenerando histograma general con todas las etiquetas...")
    plt.figure(figsize=(12, 7))
    
    clases_ordenadas = [item[0] for item in conteo_general.most_common()]
    conteos_ordenados = [item[1] for item in conteo_general.most_common()]
    
    plt.bar(clases_ordenadas, conteos_ordenados, color='teal')
    plt.title('Conteo General de Clases en todas las imágenes')
    plt.xlabel('Clases')
    plt.ylabel('Cantidad Total')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    ruta_hist_general = carpeta_resultados_hist / "histograma_general_absoluto.png"
    plt.savefig(ruta_hist_general)
    plt.close()
    
    print(f"📊 Histograma general guardado en: {ruta_hist_general.name}")

print("\n¡Proceso finalizado!")