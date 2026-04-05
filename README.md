# Python PDF Utilities

Conjunto de herramientas en Python para procesamiento de PDFs e imágenes.

## Utilidades

- **compressPDF.py** - Comprimir archivos PDF reduciendo su tamaño
- **quitarContraseñaPDF.py** - Remover protecciones de contraseña en PDFs
- **redimensionarIMG.py** - Redimensionar imágenes en lote
- **TN3toJPEG.py** - Convertir imágenes TN3 a formato JPEG
- **mypdfeditor/agregarTextoPDF.py** - Editor visual para abrir un PDF, colocar texto y exportarlo a un PDF aplanado

## Requisitos

```bash
pip install PyPDF2 Pillow PyMuPDF
```

`tkinter` suele venir incluido con Python en Windows.

## Instalación

1. Clona o descarga el repositorio
2. Instala las dependencias: `pip install -r requirements.txt`
3. Ejecuta los scripts según necesites

## Uso

Cada script es independiente. Edita las variables de configuración según tus necesidades y ejecuta:

```bash
python compressPDF.py
python quitarContraseñaPDF.py
python redimensionarIMG.py
python TN3toJPEG.py
python mypdfeditor/agregarTextoPDF.py
```

## Editor visual PDF

La herramienta `mypdfeditor/agregarTextoPDF.py` permite:

- Abrir un PDF y previsualizar sus paginas
- Hacer clic sobre una pagina para insertar texto
- Configurar fuente, tamano, color, rotacion y alineacion
- Arrastrar el texto para recolocarlo
- Exportar el resultado a un PDF final aplanado

## Licencia

MIT
