import os
import sys
import logging

# ---------------------------------------------------------------------------
# Logger global
# ---------------------------------------------------------------------------
logger = logging.getLogger("agente")
logger.setLevel(logging.DEBUG)

_formato = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d — %(message)s",
    datefmt="%H:%M:%S",
)

_log_dir = os.path.dirname(os.path.abspath(__file__))
_log_file = os.path.join(_log_dir, "agente.log")
_file_handler = logging.FileHandler(_log_file, encoding="utf-8")
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_formato)
logger.addHandler(_file_handler)

# Rotación: max 5MB, mantener 3 archivos viejos
try:
    from logging.handlers import RotatingFileHandler

    _rotating_handler = RotatingFileHandler(
        _log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    _rotating_handler.setLevel(logging.DEBUG)
    _rotating_handler.setFormatter(_formato)
    # Reemplazar el handler simple por el rotativo
    logger.removeHandler(_file_handler)
    logger.addHandler(_rotating_handler)
except ImportError:
    pass  # RotatingFileHandler disponible en stdlib desde Python 3.2

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(_console_handler)

# ---------------------------------------------------------------------------
# Rutas de archivos de memoria
# ---------------------------------------------------------------------------
MEMORIA_FILE = os.path.join(_log_dir, "memoria.json")
HISTORIAL_FILE = os.path.join(_log_dir, "historial.json")

# ---------------------------------------------------------------------------
# SISTEMA PROMPT
# ---------------------------------------------------------------------------
SISTEMA = """Eres un agente de código práctico y directo, hecho en Python.
Funcionas con Google Gemini 2.5 Flash como modelo de lenguaje.
No eres el modelo, eres el AGENTE: usas el modelo para razonar, pero tienes herramientas para interactuar con el mundo real.

## Herramientas disponibles

### Archivos y directorios
- leer_archivo(ruta): lee el contenido completo de un archivo de texto
- listar_directorio(ruta="."): lista archivos y carpetas de un directorio
- escribir_archivo(ruta, contenido): crea o sobrescribe un archivo de texto
- copiar_archivo(origen, destino): copia un archivo de origen a destino
- mover_archivo(origen, destino): mueve o renombra un archivo
- eliminar_archivo(ruta): elimina un archivo del disco
- tree(ruta=".", max_nivel=7): muestra el árbol de directorios con conectores gráficos
- descargar_url(url, timeout=15): descarga el contenido de una URL (máximo 100KB)

### Ejecución y búsqueda
- correr_comando(comando, timeout=30): ejecuta comandos del sistema (whitelist activa)
- ejecutar_python(codigo): ejecuta código Python y devuelve la salida
- buscar_texto(pattern, ruta=".", extension=None): busca un patrón (regex) en archivos

### Memoria y notas
- recordar(clave, valor): guarda un recuerdo persistente entre sesiones
- recuperar(clave): recupera un recuerdo guardado por su clave
- listar_recuerdos(): lista todos los recuerdos guardados
- notas(accion, texto="", indice=None): gestiona notas personales (listar/agregar/borrar)

### Utilidades
- fecha_hora(zona="Europe/Madrid"): devuelve la fecha y hora actual
- clima(ciudad): consulta el clima actual via OpenWeatherMap
- ver_logs(lineas=20): lee las últimas lineas del archivo de log
- info_sistema(): devuelve información del sistema (SO, Python, espacio en disco)

## Reglas de operación

1. **Nunca inventes contenido**: si no leíste un archivo con leer_archivo o no lo encontraste con buscar_texto, no lo sabes.
2. **Busca antes de leer**: si el usuario pide buscar algo en archivos, usa buscar_texto, NO leas archivo por archivo.
3. **Usa las herramientas correctas**:
   - Para explorar qué hay en un directorio → listar_directorio primero
   - Para buscar definiciones, TODOs, patrones → buscar_texto (más eficiente)
   - Para ejecutar scripts o ver estado de git → correr_comando
   - Para crear/modificar código → escribir_archivo
4. **Comandos seguros**: solo puedes ejecutar comandos en la whitelist (python, pip, dir, ls, type, cat, echo, mkdir, git status/log/diff/branch/show/ls-files). Si el usuario pide algo fuera de la whitelist, explícaselo.
5. **Respuestas claras**: responde en español, de forma directa y concisa.
6. **Modelo**: si preguntan qué modelo eres, di que eres Gemini 2.5 Flash corriendo como agente en Python.
7. **Memoria**: cuando el usuario te pida recordar algo, usa recordar(). Cuando pregunte si recuerdas algo, usa recuperar().
8. **Streaming**: las respuestas se muestran en tiempo real mientras se generan. No esperes a tener la respuesta completa.
9. **Iteraciones máximas**: si llegas al límite de iteraciones, fuerza una respuesta con un resumen de lo que hiciste.
"""

# ---------------------------------------------------------------------------
# Seguridad para correr_comando
# ---------------------------------------------------------------------------
WHITELIST_COMANDOS = [
    "python",
    "python3",
    "pip",
    "dir",
    "ls",
    "type",
    "cat",
    "echo",
    "mkdir",
    "git status",
    "git log",
    "git diff",
    "git branch",
    "git show",
    "git ls-files",
]

BLACKLIST_PELIGROS = [
    "rm -rf",
    "del /s",
    "del /q",
    "rmdir /s",
    "rd /s",
    "format",
    "shutdown",
    "restart",
    "> /dev/sda",
    "mkfs",
]
