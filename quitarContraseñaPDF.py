import PyPDF2
import os
import argparse
import getpass
import glob
import shlex
from pathlib import Path

DIRECTORIO_BASE = r"C:\Users\ayoub\Documents\Proyectos GitHub"

def quitar_contraseña_pdf(ruta_pdf, contraseña="", ruta_salida=None, pedir_password=False):
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
                estado = 0
                if contraseña:
                    estado = lector_pdf.decrypt(contraseña)
                    if not estado:
                        print("❌ Error: Contraseña incorrecta.")
                        return False
                    print("✓ PDF desencriptado correctamente.")
                else:
                    # Intentar desencriptar con contraseña vacía
                    estado = lector_pdf.decrypt("")

                # Si no pudo desencriptar y se habilitó modo interactivo, pedir clave y reintentar
                if not estado and pedir_password:
                    contraseña_usuario = getpass.getpass("Introduce la contraseña del PDF: ")
                    estado = lector_pdf.decrypt(contraseña_usuario)

                if not estado:
                    print("⚠️  No se pudo desencriptar el PDF. Usa --password o --ask-password.")
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


def resolver_ruta_pdf(entrada_pdf, directorio_base):
    """Resuelve la ruta del PDF desde una ruta completa o desde el directorio base."""
    entrada_path = Path(entrada_pdf).expanduser()

    if entrada_path.is_absolute():
        return entrada_path

    return Path(directorio_base) / entrada_path


def construir_ruta_salida(ruta_pdf, directorio_salida=None):
    """Genera la ruta de salida final para el PDF sin contraseña."""
    if directorio_salida:
        carpeta_salida = Path(directorio_salida)
    else:
        carpeta_salida = Path("pdfs_salida")

    carpeta_salida.mkdir(parents=True, exist_ok=True)
    return str(carpeta_salida / f"{Path(ruta_pdf).stem}_sin_contraseña.pdf")


def obtener_archivos_pdf(entradas_pdf, directorio_base):
    """Devuelve una lista única de archivos PDF a procesar."""
    archivos = []
    vistos = set()

    for entrada in entradas_pdf:
        tiene_wildcard = any(char in entrada for char in "*?[]")

        if tiene_wildcard:
            patron = entrada
            if not Path(entrada).is_absolute():
                patron = str(Path(directorio_base) / entrada)

            for match in glob.glob(patron):
                match_path = Path(match)
                if match_path.is_file() and match_path.suffix.lower() == ".pdf":
                    match_resuelto = str(match_path.resolve())
                    if match_resuelto not in vistos:
                        vistos.add(match_resuelto)
                        archivos.append(match_resuelto)
            continue

        ruta = resolver_ruta_pdf(entrada, directorio_base)

        if ruta.is_dir():
            for pdf in ruta.glob("*.pdf"):
                pdf_resuelto = str(pdf.resolve())
                if pdf_resuelto not in vistos:
                    vistos.add(pdf_resuelto)
                    archivos.append(pdf_resuelto)
            continue

        if ruta.is_file() and ruta.suffix.lower() == ".pdf":
            ruta_resuelta = str(ruta.resolve())
            if ruta_resuelta not in vistos:
                vistos.add(ruta_resuelta)
                archivos.append(ruta_resuelta)

    return archivos


def procesar_entrada_interactiva(entrada):
    """Parsea entrada interactiva y extrae archivos + opciones comunes."""
    segmentos = [valor.strip() for valor in entrada.split(",") if valor.strip()]
    entradas_pdf = []
    ask_password = False
    password = None

    for segmento in segmentos:
        tokens = shlex.split(segmento, posix=False)
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token == "--ask-password":
                ask_password = True
                i += 1
                continue
            if token == "--password" and i + 1 < len(tokens):
                password = tokens[i + 1]
                i += 2
                continue
            entradas_pdf.append(token)
            i += 1

    return entradas_pdf, ask_password, password


def parse_args():
    parser = argparse.ArgumentParser(
        description="Quita la contraseña de un PDF desde un directorio base."
    )
    parser.add_argument(
        "pdfs",
        nargs="*",
        help=(
            "Uno o varios PDFs, carpetas o patrones (ej: *.pdf). "
            "Si no se indica, se pedirá por consola."
        ),
    )
    parser.add_argument(
        "--password",
        default="",
        help="Contraseña de los PDFs. Si no se indica, se intentará sin contraseña.",
    )
    parser.add_argument(
        "--dir",
        default=DIRECTORIO_BASE,
        help=f"Directorio base de búsqueda (por defecto: {DIRECTORIO_BASE})",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Carpeta de salida. Si no se indica, usa 'pdfs_salida'.",
    )
    parser.add_argument(
        "--ask-password",
        action="store_true",
        help="Pide la contraseña de forma oculta por consola.",
    )
    return parser.parse_args()

def main():
    """Función principal para procesar PDFs desde línea de comandos."""
    args = parse_args()

    print("=" * 60)
    print("ELIMINADOR DE CONTRASEÑAS PDF")
    print("=" * 60)
    print(f"📁 Directorio base: {args.dir}")

    entradas_pdf = args.pdfs
    if not entradas_pdf:
        entrada = input(
            "\nIntroduce PDF(s), carpeta(s) o patrón(es) separados por coma: "
        ).strip()
        if not entrada:
            print("❌ No se indicó ningún archivo o patrón PDF.")
            return

        entradas_pdf, ask_password_prompt, password_prompt = procesar_entrada_interactiva(
            entrada
        )
        if ask_password_prompt:
            args.ask_password = True
        if password_prompt is not None:
            args.password = password_prompt

        if not entradas_pdf:
            print("❌ No se detectaron rutas PDF válidas en la entrada.")
            return

    archivos_pdf = obtener_archivos_pdf(entradas_pdf, args.dir)
    if not archivos_pdf:
        print("❌ No se encontraron archivos PDF para procesar.")
        return

    print(f"📄 Archivos a procesar: {len(archivos_pdf)}")

    contraseña = args.password
    if args.ask_password and not contraseña:
        contraseña = getpass.getpass("Introduce la contraseña del PDF: ")

    exitos = 0
    fallos = 0

    for ruta_pdf in archivos_pdf:
        ruta_salida = construir_ruta_salida(ruta_pdf, args.out)
        if quitar_contraseña_pdf(str(ruta_pdf), contraseña, ruta_salida, args.ask_password):
            exitos += 1
        else:
            fallos += 1

    print("\n" + "=" * 60)
    print(f"Resumen: {exitos} correctos, {fallos} con error")
    print("=" * 60)

if __name__ == "__main__":
    main()
