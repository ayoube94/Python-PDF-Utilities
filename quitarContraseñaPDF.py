import PyPDF2
import os
import sys
from pathlib import Path

def quitar_contraseña_pdf(ruta_pdf, contraseña="", ruta_salida=None):
    """
    Quita la contraseña de un archivo PDF y guarda el resultado.
    
    Args:
        ruta_pdf (str): Ruta del archivo PDF protegido
        contraseña (str): Contraseña del PDF (si está vacía, lo intenta sin contraseña)
        ruta_salida (str): Ruta donde guardar el PDF sin contraseña. 
                          Si es None, guarda en la carpeta 'pdfs_salida'
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(ruta_pdf):
            print(f"❌ Error: El archivo '{ruta_pdf}' no existe.")
            return False
        
        # Crear carpeta de salida si no existe
        if ruta_salida is None:
            carpeta_salida = "pdfs_salida"
            os.makedirs(carpeta_salida, exist_ok=True)
            nombre_archivo = Path(ruta_pdf).stem + "_sin_contraseña.pdf"
            ruta_salida = os.path.join(carpeta_salida, nombre_archivo)
        
        # Abrir el PDF protegido
        print(f"📂 Procesando: {ruta_pdf}")
        with open(ruta_pdf, 'rb') as archivo_entrada:
            lector_pdf = PyPDF2.PdfReader(archivo_entrada)
            
            # Si el PDF está encriptado, desencriptarlo
            if lector_pdf.is_encrypted:
                print("🔒 PDF protegido detectado. Intentando desencriptar...")
                
                # Intentar con la contraseña proporcionada
                if contraseña:
                    if not lector_pdf.decrypt(contraseña):
                        print(f"❌ Error: Contraseña incorrecta.")
                        return False
                    print("✓ PDF desencriptado correctamente.")
                else:
                    # Intentar desencriptar sin contraseña
                    try:
                        lector_pdf.decrypt("")
                    except:
                        print("⚠️  No se pudo desencriptar sin contraseña. Intente proporcionando una.")
                        return False
            else:
                print("ℹ️  El PDF no está protegido.")
            
            # Crear un nuevo PDF sin protección
            escritor_pdf = PyPDF2.PdfWriter()
            
            # Copiar todas las páginas
            for num_pagina in range(len(lector_pdf.pages)):
                pagina = lector_pdf.pages[num_pagina]
                escritor_pdf.add_page(pagina)
            
            # Guardar el PDF sin contraseña
            with open(ruta_salida, 'wb') as archivo_salida:
                escritor_pdf.write(archivo_salida)
            
            print(f"✓ PDF guardado sin contraseña: {ruta_salida}")
            return True
            
    except Exception as e:
        print(f"❌ Error al procesar el PDF: {str(e)}")
        return False

def main():
    """Función principal para procesar PDFs desde línea de comandos."""
    
    if len(sys.argv) < 2:
        print("=" * 60)
        print("ELIMINADOR DE CONTRASEÑAS PDF")
        print("=" * 60)
        print("\nUso:")
        print("  python quitarContraseñaPDF.py <archivo.pdf> [contraseña]")
        print("\nEjemplos:")
        print("  python quitarContraseñaPDF.py documento.pdf")
        print("  python quitarContraseñaPDF.py documento.pdf micontraseña")
        print("\nEl PDF sin contraseña se guardará en: pdfs_salida/")
        return
    
    ruta_pdf = sys.argv[1]
    contraseña = sys.argv[2] if len(sys.argv) > 2 else ""
    
    quitar_contraseña_pdf(ruta_pdf, contraseña)

if __name__ == "__main__":
    main()
