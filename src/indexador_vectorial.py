"""
Proyecto: Eyringpy AI Assistant
Desarrolladora: Aura Ximena Gómez Heredia
================================================================================
INDEXACIÓN VECTORIAL DEL MANUAL
================================================================================
Este modulo convierte los fragmentos de texto en vectores numericos (embeddings)
y los guarda en una base de datos vectorial (FAISS)
"""
#Importación de las librerías.
#Habilitar la versión actual de python:
from __future__ import annotations
import os
#Manejo de rutas y archivos:
from pathlib import Path
#FAISS: base de datos vectorial (busca por similitud):
from langchain_community.vectorstores import FAISS
#Modelo de Google que convierte texto en vectores:
from langchain_google_genai import GoogleGenerativeAIEmbeddings
#Lectura del PDF (paso previo a la indexación):
from lector_manual import ARCHIVO_PDF, cargar_pdf, dividir_en_chunks


# ==============================================================================
#  CONFIGURACION
# ==============================================================================
#Modelo de embeddings:
MODELO_EMBEDDING = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
#Carpeta donde se guarda el índice ya calculado:
DIR_INDICE = os.getenv("EYRINGPY_INDEX_DIR", "faiss_index_eyringpy")

# ==============================================================================
#  MODELO DE EMBEDDINGS
# ==============================================================================
def crear_embeddings() -> GoogleGenerativeAIEmbeddings:    #Un embedding es una lista de números (3072 aquí) que captura el significado del texto. . 
    return GoogleGenerativeAIEmbeddings(model=MODELO_EMBEDDING)

# ==============================================================================
#  CONSTRUIR O CARGAR EL ÍNDICE VECTORIAL
# ==============================================================================
def construir_vectorstore(
    ruta_pdf: str | Path = ARCHIVO_PDF,
    dir_indice: str | Path = DIR_INDICE,
    reconstruir: bool = False,
) -> FAISS:
    embeddings = crear_embeddings()
    dir_indice = Path(dir_indice)

    # Camino A: si el índice ya existe en disco, se reutiliza.
    if dir_indice.exists() and not reconstruir:
        print(f"  · Cargando indice vectorial existente desde '{dir_indice}'.")
        return FAISS.load_local(
            str(dir_indice),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    # Camino B: construir el índice desde cero.
    paginas = cargar_pdf(ruta_pdf)        # abre el PDF y extrae el texto
    chunks = dividir_en_chunks(paginas)   # lo trocea en fragmentos

    print("  · Generando embeddings e indexando en FAISS...")
    # FAISS.from_documents() hace dos cosas: manda los chunks al modelo de embeddings y guarda los vectores en un índice de búsqueda rápida.
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(dir_indice))   # se guarda para no repetir el gasto
    print(f"  · Indice guardado en '{dir_indice}'.")
    return vectorstore


# ==============================================================================
# PRUEBA INDEPENDIENTE LOCAL
# Requiere GOOGLE_API_KEY porque los embeddings se generan con la API de Google.
# ==============================================================================

if __name__ == "__main__":
    import sys
    #Carga la clave desde el archivo .env si está disponible:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    reconstruir = "--rebuild" in sys.argv

    print("=" * 70)
    print("  PRUEBA DE INDEXACION VECTORIAL")
    print("=" * 70)

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        print("\nERROR: falta la variable GOOGLE_API_KEY (ponla en el archivo .env).")
        sys.exit(1)

    try:
        vs = construir_vectorstore(reconstruir=reconstruir)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

    # Resume el índice generado:
    total = vs.index.ntotal            # cuántos vectores hay almacenados
    dimension = vs.index.d             # cuántos números tiene cada vector
    print("\n--- RESUMEN ---")
    print(f"Modelo de embeddings : {MODELO_EMBEDDING}")
    print(f"Vectores indexados   : {total}")
    print(f"Dimensiones por vector: {dimension}")
    print(f"Carpeta del indice   : {DIR_INDICE}")

    # Prueba de búsqueda por significado:
    consulta = "efecto tunel"
    print(f"\n--- BUSQUEDA DE PRUEBA: '{consulta}' ---")
    resultados = vs.similarity_search(consulta, k=2)
    for i, doc in enumerate(resultados, start=1):
        pagina = doc.metadata.get("page")
        pagina = "?" if pagina is None else int(pagina) + 1
        print(f"\n[{i}] {doc.metadata.get('source')} (pag. {pagina})")
        print(doc.page_content[:200].strip().replace("\n", " "))

    #Mensaje de finalización:
    print("\nIndexacion vectorial verificada correctamente.")
