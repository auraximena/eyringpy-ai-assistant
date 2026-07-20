"""
Proyecto: Eyringpy AI Assistant
Desarrolladora: Aura Ximena Gómez Heredia
================================================================================
  lector_manual.py — LECTURA Y PROCESAMIENTO DEL MANUAL DE EYRINGPY
================================================================================
Este modulo es el encargado de ACCEDER AL ARCHIVO y EXTRAER SU CONTENIDO.
"""
#Importación de las librerías.
#Habilitar la versión actual de python:
from __future__ import annotations
import os
#Manejo de rutas y archivos:
from pathlib import Path
# PyPDFLoader: abre el PDF y extrae el texto pagina por pagina:
from langchain_community.document_loaders import PyPDFLoader
#Guarda el texto con sus metadatos:
from langchain_core.documents import Document
# RecursiveCharacterTextSplitter con el que se hace el chunk.
from langchain_text_splitters import RecursiveCharacterTextSplitter


# ==============================================================================
#  CONFIGURACION
# ==============================================================================
ARCHIVO_PDF = os.getenv("EYRINGPY_PDF", "eyringpy3.0_manual.pdf")
TAMANO_CHUNK = 1000 #cuantos caracteres tiene cada fragmento.
SOLAPAMIENTO_CHUNK = 150 #cuantos caracteres se repiten entre un fragmento y el siguiente

# ==============================================================================
#  ACCEDER AL ARCHIVO Y EXTRAER SU CONTENIDO
# ==============================================================================
def cargar_pdf(ruta: str | Path = ARCHIVO_PDF) -> list[Document]:
    ruta = Path(ruta)

    # Validación de que exista el archivo:
    if not ruta.exists():
        raise FileNotFoundError(
            f"No se encontro el PDF del manual: '{ruta}'.\n"
            f"Coloca el archivo '{ARCHIVO_PDF}' en la carpeta del proyecto."
        )

    # Validación del formato del archivo:
    if ruta.suffix.lower() != ".pdf":
        raise ValueError(
            f"Este proyecto solo acepta archivos PDF, pero recibio: '{ruta.name}'.\n"
            f"Usa el manual en PDF ('{ARCHIVO_PDF}')."
        )

    # Extracción del contenido:
    # .load() recorre el PDF hoja por hoja y saca el texto de cada una.
    loader = PyPDFLoader(str(ruta))
    paginas = loader.load()
    #Obtención de metadatos para poder citar la página en el chatbot.
    for pagina in paginas:
        pagina.metadata["source"] = ruta.name

    print(f"  · PDF leido: {ruta.name} -> {len(paginas)} paginas.")
    return paginas


# ==============================================================================
#  CHUNKING
# ==============================================================================
def dividir_en_chunks(paginas: list[Document]) -> list[Document]:
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=TAMANO_CHUNK,             # tamano objetivo de cada fragmento
        chunk_overlap=SOLAPAMIENTO_CHUNK,    # repeticion entre fragmentos vecinos
        separators=["\n\n", "\n", ". ", " ", ""],  # orden de corte preferido
    )
    chunks = divisor.split_documents(paginas)
    print(f"  · Texto dividido en {len(chunks)} fragmentos (chunks).")
    return chunks

# ==============================================================================
#  UNIÓN DE AMBAS FUNCIONES PARA PASAR AL AGENTE
# ==============================================================================
def procesar_manual(ruta: str | Path = ARCHIVO_PDF) -> list[Document]:
    paginas = cargar_pdf(ruta)
    return dividir_en_chunks(paginas)


# ==============================================================================
# PRUEBA INDEPENDIENTE LOCAL
# ==============================================================================

if __name__ == "__main__":
    import sys
    ruta = sys.argv[1] if len(sys.argv) > 1 else ARCHIVO_PDF

    print("=" * 70)
    print("  PRUEBA DE LECTURA DEL DOCUMENTO")
    print("=" * 70)

    try:
        paginas = cargar_pdf(ruta)
        chunks = dividir_en_chunks(paginas)
    except (FileNotFoundError, ValueError) as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    # Resume la información extraida:
    caracteres = sum(len(p.page_content) for p in paginas)
    print("\n--- RESUMEN ---")
    print(f"Paginas leidas      : {len(paginas)}")
    print(f"Caracteres extraidos: {caracteres:,}")
    print(f"Fragmentos generados: {len(chunks)}")
    print(f"Tamano de fragmento : {TAMANO_CHUNK} caracteres "
          f"(con {SOLAPAMIENTO_CHUNK} de solapamiento)")

    # Muestra el contenido extraido:
    print("\n--- MUESTRA: primeros 300 caracteres de la pagina 1 ---")
    print(paginas[0].page_content[:300].strip())
    print("\n--- MUESTRA: un fragmento intermedio y sus metadatos ---")
    medio = chunks[len(chunks) // 2]
    print(f"Metadatos: {medio.metadata}")
    print(medio.page_content[:300].strip())
    
    #Mensaje de finalización:
    print("\nLectura del documento completada correctamente.")
