"""
Proyecto: Eyringpy AI Assistant
Desarrolladora: Aura Ximena Gómez Heredia
================================================================================
  EyringpyAI: Agente "Eyri" Asistente Virtual
================================================================================
Agente de inteligencia artificial que responde preguntas sobre el manual del software eyringpy 3.0.
"""

#importación de librerias: 
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

#Lectura del archivo .env para la API de Gemini.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Importación de librerias de Langchain:
from langchain_community.vectorstores import FAISS  # tipo de la base vectorial
from langchain_core.documents import Document  # objeto "fragmento de texto"
from langchain_core.output_parsers import StrOutputParser  # deja la salida como str
from langchain_core.prompts import ChatPromptTemplate  # plantilla del prompt
from langchain_google_genai import ChatGoogleGenerativeAI  # modelo Gemini

#Importación de modulos:
from lector_manual import ARCHIVO_PDF
from indexador_vectorial import DIR_INDICE, construir_vectorstore


# ==============================================================================
#  CONFIGURACION
# ==============================================================================

# Definición del modelo de lenguaje:
MODELO_LLM = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Cuantos fragmentos del manual se le pasan a Gemini en cada pregunta.
K_FRAGMENTOS = 4 

# ==============================================================================
#  EL AGENTE 
# ==============================================================================

# Aqui se genera un template del promt que se le da a gemini. Aquí se prohibe utilizar conocimiento externo
#esto evita las alucinaciones.

PLANTILLA_PROMPT = """Eres EyringpyAI Assistant, un asistente experto en el manual del \
software cientifico eyringpy 3.0.

Responde la PREGUNTA del usuario utilizando UNICAMENTE la informacion del \
CONTEXTO que aparece mas abajo.

Reglas:
- Si la respuesta no esta en el contexto, responde exactamente:
  "No encontre esa informacion en el manual de eyringpy."
- No inventes datos ni uses conocimiento externo al contexto.
- Responde de forma clara y directa, en el mismo idioma de la pregunta (por defecto, espanol).
- Cuando menciones keywords, comandos, rutas o valores, copialos tal cual aparecen en el manual.
- Si la pregunta esta en español, traduce esa pregunta a ingles para buscar acertivamente en el manual

CONTEXTO:
{context}

PREGUNTA: {question}

RESPUESTA:"""


class AgenteEyringpy:
    def __init__(self, vectorstore: FAISS, k: int = K_FRAGMENTOS):
        # retriver corresponde al buscador que recibe una pregunta y devuelve los k fragmentos mas parecidos que encuentre en la base vectorial.
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": k})

        # El modelo que redacta.
        self.llm = ChatGoogleGenerativeAI(model=MODELO_LLM, temperature=0.2)
        self.prompt = ChatPromptTemplate.from_template(PLANTILLA_PROMPT)
        self.cadena = self.prompt | self.llm | StrOutputParser()

    # Constructor de convivencia:
    @classmethod
    def desde_documento(
        cls,
        ruta_doc: str | Path = ARCHIVO_PDF,
        dir_indice: str | Path = DIR_INDICE,
        reconstruir: bool = False,
        k: int = K_FRAGMENTOS,
    ) -> "AgenteEyringpy":
        """Crea el agente preparando (o cargando) el indice vectorial del PDF."""
        vectorstore = construir_vectorstore(ruta_doc, dir_indice, reconstruir)
        return cls(vectorstore, k=k)

#En esta seccion se unen los fragmentos de texto en un bloque.
    @staticmethod
    def _formatear_contexto(docs: list[Document]) -> str:
        bloques = []
        for i, doc in enumerate(docs, start=1):
            fuente = doc.metadata.get("source", "documento")
            pagina = doc.metadata.get("page")  # viene del PDF (empieza en 0)
            etiqueta = f"[Fragmento {i} | fuente: {fuente}"
            if pagina is not None:
                etiqueta += f" | pagina: {int(pagina) + 1}"  
            etiqueta += "]"
            bloques.append(f"{etiqueta}\n{doc.page_content}")
        return "\n\n".join(bloques)

#Arma la linea final con las fuentes citadas.
    @staticmethod
    def _formatear_fuentes(docs: list[Document]) -> str:
        paginas_por_archivo: dict[str, set[int]] = {}
        for doc in docs:
            fuente = doc.metadata.get("source", "documento")
            pagina = doc.metadata.get("page")
            paginas_por_archivo.setdefault(fuente, set())
            if pagina is not None:
                # +1 porque PyPDF numera desde 0 y las personas desde 1
                paginas_por_archivo[fuente].add(int(pagina) + 1)

        partes: list[str] = []
        for archivo, paginas in paginas_por_archivo.items():
            if paginas:
                numeros = ", ".join(str(p) for p in sorted(paginas))
                etiqueta = "pag." if len(paginas) == 1 else "pags."
                partes.append(f"{archivo} ({etiqueta} {numeros})")
            else:
                partes.append(archivo)
        return "Fuente(s): " + "; ".join(partes)

    # Metodo principal
    def responder(self, pregunta: str) -> str:
        pregunta = (pregunta or "").strip()
        if not pregunta:
            return "Por favor, escribe una pregunta."

        try:
            docs = self.retriever.invoke(pregunta)
            if not docs:
                return "No encontre esa informacion en el manual de eyringpy."

            contexto = self._formatear_contexto(docs)
            respuesta = self.cadena.invoke({"context": contexto, "question": pregunta})

        except Exception as e:
            # Para errores típicos
            return (
                "Ocurrio un error al consultar el modelo de lenguaje. "
                "Puede deberse a la conexion o al limite de cuota de la API. "
                f"Detalle: {e}"
            )

        #citar la fuente.
        if "No encontre esa informacion" in respuesta:
            return respuesta.strip()
        return f"{respuesta.strip()}\n\n{self._formatear_fuentes(docs)}"


# ==============================================================================
# ESTA SECCIÓN ES PARA PROBAR EL AGENTE EN LOCAL
# ==============================================================================
#  Nota: la interfaz del proyecto es el chat de Eyri dentro de la app
#  web (Streamlit) de Eyringpy. Esta seccion es solo para probar el agente en el local.
# ==============================================================================

#Comprueba que exista la API KEY
def _verificar_api_key() -> bool:
    clave = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not clave:
        print(
            "ERROR: falta la variable de entorno GOOGLE_API_KEY.\n"
            "Obtén una clave gratuita en https://aistudio.google.com/app/apikey\n"
            "y defínela, por ejemplo:\n"
            '   PowerShell:  $env:GOOGLE_API_KEY = "tu_clave"\n'
            "   o crea un archivo .env con:  GOOGLE_API_KEY=tu_clave",
            file=sys.stderr,
        )
        return False
    os.environ.setdefault("GOOGLE_API_KEY", clave)
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="EyringpyAI — agente que responde sobre el manual PDF de eyringpy."
    )
    parser.add_argument(
        "--pdf",
        default=ARCHIVO_PDF,
        help=f"Ruta al PDF del manual (por defecto: {ARCHIVO_PDF}).",
    )
    parser.add_argument(
        "-q",
        "--pregunta",
        help="Hace una sola pregunta, imprime la respuesta y termina.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Fuerza la reconstruccion del indice vectorial.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=K_FRAGMENTOS,
        help="Numero de fragmentos a recuperar por pregunta.",
    )
    args = parser.parse_args()

    if not _verificar_api_key():
        sys.exit(1)

    # Construccion del agente.
    try:
        agente = AgenteEyringpy.desde_documento(
            ruta_doc=args.pdf, reconstruir=args.rebuild, k=args.k
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if args.pregunta:
        print("\n" + agente.responder(args.pregunta))
        return

#Prueba en la terminal
    print("\n" + "=" * 60)
    print("  EyringpyAI (Eyri)  |  respuestas basadas en el manual PDF")
    print("  Escribe tu pregunta. Para salir: 'salir', 'exit' o Ctrl+C.")
    print("=" * 60)
    while True:
        try:
            pregunta = input("\nTú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n¡Hasta luego!")
            break
        if pregunta.lower() in {"salir", "exit", "quit", "q"}:
            print("¡Hasta luego!")
            break
        if not pregunta:
            continue
        respuesta: str = agente.responder(pregunta)
        print(f"\nEyri: {respuesta}")


if __name__ == "__main__":
    main()

