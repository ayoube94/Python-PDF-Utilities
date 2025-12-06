import os
from PIL import Image

def redimensionar_imagen(ruta_entrada, ruta_salida, ancho_nuevo, alto_nuevo, max_size_bytes):
    try:
        # Abrir la imagen original
        imagen = Image.open(ruta_entrada)

        # Redimensionar la imagen
        imagen_redimensionada = imagen.resize((ancho_nuevo, alto_nuevo))

        # Guardar temporalmente para comprobar tamaño
        imagen_redimensionada.save(ruta_salida)

        # Comprobar el tamaño del archivo
        size_bytes = os.path.getsize(ruta_salida)

        if size_bytes > max_size_bytes:
            # Si excede el límite, eliminar el archivo
            os.remove(ruta_salida)
            print(f"❌ Imagen descartada (excede {max_size_bytes} bytes): {ruta_entrada}")
        else:
            print(f"✅ Imagen guardada: {ruta_salida} ({size_bytes} bytes)")

    except Exception as e:
        print(f"Error procesando {ruta_entrada}: {e}")

# Procesar todas las imágenes de una carpeta
if __name__ == "__main__":
    carpeta_entrada = "imagenes_entrada"
    carpeta_salida = "imagenes_salida"
    nuevo_ancho = 800
    nuevo_alto = 600
    max_size_kb = 0.5
    max_size_bytes = int(max_size_kb * 1024)

    # Crear carpeta de salida si no existe
    os.makedirs(carpeta_salida, exist_ok=True)

    # Extensiones válidas de imagen
    extensiones = (".jpg", ".jpeg", ".png", ".gif", ".bmp")

    for archivo in os.listdir(carpeta_entrada):
        if archivo.lower().endswith(extensiones):
            ruta_original = os.path.join(carpeta_entrada, archivo)
            ruta_guardado = os.path.join(carpeta_salida, archivo)
            redimensionar_imagen(ruta_original, ruta_guardado, nuevo_ancho, nuevo_alto, max_size_bytes)