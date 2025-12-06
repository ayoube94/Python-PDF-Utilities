import os
import fitz  # PyMuPDF

def comprimir_pdf_simple(pdf_path, salida_path, max_kb=5120, zooms=[1.0, 0.8, 0.6, 0.5, 0.48]):
    """
    Prueba varias resoluciones y elige la salida cuyo tamaño esté más cerca de max_kb
    (por diferencia absoluta). Borra las demás variantes temporales.
    """
    resultados = []  # lista de tuplas (zoom, size_kb, temp_path)

    for zoom in zooms:
        doc_in = fitz.open(pdf_path)
        doc_out = fitz.open()
        for page in doc_in:
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            rect = fitz.Rect(0, 0, pix.width, pix.height)
            page_out = doc_out.new_page(width=pix.width, height=pix.height)
            page_out.insert_image(rect, pixmap=pix)

        temp_out = salida_path.replace(".pdf", f"_z{int(zoom*100)}.pdf")
        doc_out.save(temp_out, deflate=True, garbage=4, clean=True)
        doc_in.close()
        doc_out.close()

        size_out = os.path.getsize(temp_out) / 1024
        print(f"Zoom {zoom} -> {size_out:.2f} KB")
        resultados.append((zoom, size_out, temp_out))

    # Elegir la mejor versión: la cuyo tamaño esté más cerca de max_kb (por diferencia absoluta)
    mejor = min(resultados, key=lambda t: abs(t[1] - max_kb))

    # mover la mejor a salida y borrar las demás
    for zoom, size_kb, path in resultados:
        if path == mejor[2]:
            os.replace(path, salida_path)
            print(f"✅ PDF final seleccionado zoom {zoom}, tamaño final: {size_kb:.2f} KB")
            if size_kb > max_kb:
                print(f"⚠️ La versión seleccionada supera {max_kb} KB por {size_kb - max_kb:.2f} KB")
        else:
            try:
                os.remove(path)
            except OSError:
                pass
    
    # Si ninguna resolución baja del límite, guardar la última versión
    print(f"⚠️ No se logró bajar de {max_kb} KB, guardando la versión con zoom {zooms[-1]}")
    doc_in = fitz.open(pdf_path)
    doc_out = fitz.open()
    zoom = zooms[-1]
    for page in doc_in:
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        rect = fitz.Rect(0, 0, pix.width, pix.height)
        page_out = doc_out.new_page(width=pix.width, height=pix.height)
        page_out.insert_image(rect, pixmap=pix)
    doc_out.save(salida_path, deflate=True, garbage=4, clean=True)
    doc_in.close()
    doc_out.close()
    size_out = os.path.getsize(salida_path) / 1024
    print(f"PDF guardado con zoom {zoom}, tamaño final: {size_out:.2f} KB")


if __name__ == "__main__":
    carpeta_entrada = r"C:\Users\ayoub\Documents\Master\Yasmina"
    carpeta_salida = os.path.join(carpeta_entrada, "pdfs_salida")
    os.makedirs(carpeta_salida, exist_ok=True)

    for archivo in os.listdir(carpeta_entrada):
        if archivo.lower().endswith(".pdf"):
            ruta_in = os.path.join(carpeta_entrada, archivo)
            ruta_out = os.path.join(carpeta_salida, archivo)
            comprimir_pdf_simple(ruta_in, ruta_out, max_kb=5120)
