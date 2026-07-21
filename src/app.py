"""
Proyecto: Eyringpy AI Assistant
Desarrolladora: Aura Ximena Gómez Heredia
================================================================================
  APP WEB DE EYRI (Streamlit)
================================================================================
Interfaz web del asistente Eyri. Es una pantalla unica: el logo de eyringpy y
el chat. El usuario escribe su pregunta sobre el manual y el agente responde
citando la pagina de donde tomo la informacion.

Para ejecutarla:   streamlit run app.py
"""
#Importación de las librerías.
import base64
import os
from pathlib import Path
import streamlit as st

#Importación del agente (el que hace todo el trabajo de RAG):
from agente_eyringpy import AgenteEyringpy


# ==============================================================================
#  CONFIGURACION
# ==============================================================================
#Rutas calculadas desde la ubicación de este archivo, para que funcionen igual
#en local y en el servidor donde se despliegue:
BASE_DIR = Path(__file__).resolve().parent
RUTA_LOGO_EYRINGPY = BASE_DIR / "assets" / "logo_eyringpy.png"   # logo de cabecera
RUTA_LOGO_EYRI = BASE_DIR / "assets" / "eyri_icon.png"           # avatar del bot
RUTA_PDF = BASE_DIR / "eyringpy3.0_manual.pdf"
DIR_INDICE = BASE_DIR / "faiss_index_eyringpy"

#Avatares del chat: Eyri usa su logo, el usuario un emoji.
AVATAR_EYRI = str(RUTA_LOGO_EYRI)
AVATAR_USUARIO = "🧑‍🔬"

#Primer mensaje que ve el usuario:
SALUDO = (
    "¡Hola! Soy **Eyri**, tu asistente sobre *eyringpy*. "
    "Pregúntame lo que necesites del manual (instalación, keywords del archivo "
    "de entrada, tests, cómo citar el programa…) y te respondo citando la fuente."
)


# ==============================================================================
#  CONFIGURACION DE LA PAGINA
# ==============================================================================
st.set_page_config(
    page_title="Eyri — Asistente de eyringpy",
    page_icon=str(RUTA_LOGO_EYRI) if RUTA_LOGO_EYRI.exists() else "🤖",
    layout="centered",
    initial_sidebar_state="collapsed",   # no se usa barra lateral
)

#Se ocultan el menu, el pie de pagina y la barra superior de Streamlit para
#dejar la pantalla limpia: solo el logo y el chat.
st.markdown(
    """
    <style>
      #MainMenu, footer, header {visibility: hidden;}
      .block-container {padding-top: 2.5rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ==============================================================================
#  CARGA DEL AGENTE
# ==============================================================================
def _configurar_clave() -> None:
    #Streamlit guarda los secretos en .streamlit/secrets.toml, pero el agente
    #lee la clave desde las variables de entorno. Esta función hace de puente.
    #Si no hay secrets, se usa el archivo .env (que ya carga agente_eyringpy).
    try:
        for clave in ("GOOGLE_API_KEY", "GEMINI_MODEL", "GEMINI_EMBEDDING_MODEL"):
            if clave in st.secrets:
                os.environ[clave] = str(st.secrets[clave])
    except Exception:
        pass


@st.cache_resource(show_spinner="Preparando a Eyri (leyendo el manual)…")
def cargar_agente():
    #@st.cache_resource hace que el agente se construya UNA sola vez.
    #Sin esto se reconstruiria en cada mensaje, porque Streamlit vuelve a
    #ejecutar todo el script en cada interaccion del usuario.
    _configurar_clave()

    if not (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")):
        raise RuntimeError(
            "Falta la clave GOOGLE_API_KEY. Ponla en el archivo .env "
            "o en .streamlit/secrets.toml"
        )

    return AgenteEyringpy.desde_documento(
        ruta_doc=str(RUTA_PDF),
        dir_indice=str(DIR_INDICE),
    )


@st.cache_data
def _imagen_en_base64(ruta: Path) -> str:
    #st.markdown con HTML no puede cargar imágenes por ruta local, necesita una
    #URL. Convertir el PNG a base64 lo incrusta dentro del propio HTML.
    if not ruta.exists():
        return ""
    datos = base64.b64encode(ruta.read_bytes()).decode()
    return f"data:image/png;base64,{datos}"


# ==============================================================================
#  ENCABEZADO: SOLO EL LOGO DE EYRINGPY
# ==============================================================================
logo = _imagen_en_base64(RUTA_LOGO_EYRINGPY)
if logo:
    st.markdown(
        f"""
        <div style="text-align:center; margin-bottom:18px;">
            <img src="{logo}" style="width:320px; max-width:70%;"/>
        </div>
        """,
        unsafe_allow_html=True,
    )

#Aviso de que se conversa con una IA (elemento requerido por el proyecto):
st.markdown(
    "<p style='text-align:center; color:#8b95a5; font-size:13px; margin-top:-6px;'>"
    "Asistente de IA · responde solo con base en el manual de eyringpy y cita la fuente"
    "</p>",
    unsafe_allow_html=True,
)


# ==============================================================================
#  INICIALIZACION DE LA CONVERSACION
# ==============================================================================
#El historial vive en st.session_state para que sobreviva a las
#re-ejecuciones del script que hace Streamlit en cada interaccion.
if "mensajes" not in st.session_state:
    st.session_state.mensajes = [{"rol": "assistant", "texto": SALUDO}]

#Se carga el agente. Si algo falla (falta la clave, no hay red...) se avisa
#en la pagina en lugar de romper la aplicacion.
try:
    agente = cargar_agente()
except Exception as e:
    st.error(
        "No se pudo inicializar a Eyri. Revisa que **GOOGLE_API_KEY** esté "
        f"configurada.\n\nDetalle: {e}"
    )
    st.stop()


# ==============================================================================
#  ENTRADA DEL USUARIO
# ==============================================================================
#st.chat_input siempre se dibuja al final de la pagina, sin importar donde se
#llame. Se llama aqui arriba para tener su valor antes de pintar el historial.
pregunta = st.chat_input("Escribe tu pregunta sobre eyringpy…")

if pregunta:
    #Se guarda el mensaje del usuario:
    st.session_state.mensajes.append({"rol": "user", "texto": pregunta})
    #Se consulta al agente (aqui ocurre el RAG + Gemini):
    with st.spinner("Eyri está buscando en el manual…"):
        respuesta = agente.responder(pregunta)   # devuelve un str
    #Se guarda la respuesta:
    st.session_state.mensajes.append({"rol": "assistant", "texto": respuesta})


# ==============================================================================
#  HISTORIAL DE LA CONVERSACION
# ==============================================================================
for mensaje in st.session_state.mensajes:
    avatar = AVATAR_EYRI if mensaje["rol"] == "assistant" else AVATAR_USUARIO
    with st.chat_message(mensaje["rol"], avatar=avatar):
        st.markdown(mensaje["texto"])
