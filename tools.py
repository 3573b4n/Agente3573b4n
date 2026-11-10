import os
import subprocess

from config import logger, _log_file
from memory import cargar_memoria, guardar_memoria
from notas import Notas


# ---------------------------------------------------------------------------
# Seguridad de correr_comando
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


def _comando_permitido(comando: str) -> tuple[bool, str]:
    cmd_lower = comando.strip().lower()
    if not cmd_lower:
        return False, "comando vacio"
    for peligroso in BLACKLIST_PELIGROS:
        if peligroso in cmd_lower:
            return False, f"comando peligroso detectado: '{peligroso}'"
    for permitido in WHITELIST_COMANDOS:
        if cmd_lower.startswith(permitido):
            resto = cmd_lower[len(permitido) :]
            if resto == "" or resto[0] in (" ", "\t"):
                return True, "OK"
    return False, f"comando '{comando}' no esta en la whitelist"


# ---------------------------------------------------------------------------
# Herramientas
# ---------------------------------------------------------------------------


def leer_archivo(ruta: str) -> str:
    """Lee el contenido de un archivo de texto del disco."""
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return f"ERROR: No existe el archivo '{ruta}'"
    except Exception as e:
        return f"ERROR al leer '{ruta}': {e}"


def listar_directorio(ruta: str = ".") -> str:
    """Lista los archivos y carpetas de un directorio."""
    try:
        entries = os.listdir(ruta)
        dirs = [d + "/" for d in entries if os.path.isdir(os.path.join(ruta, d))]
        files = [f for f in entries if not os.path.isdir(os.path.join(ruta, f))]
        if not dirs and not files:
            return f"(directorio vacio: {ruta})"
        return "\n".join(dirs + files)
    except Exception as e:
        return f"ERROR al listar '{ruta}': {e}"


def escribir_archivo(ruta: str, contenido: str) -> str:
    """Crea o sobrescribe un archivo de texto con el contenido dado."""
    try:
        directorio_padre = os.path.dirname(ruta)
        if directorio_padre and not os.path.exists(directorio_padre):
            os.makedirs(directorio_padre, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        return f"OK: archivo '{ruta}' escrito ({len(contenido)} caracteres)"
    except Exception as e:
        return f"ERROR al escribir '{ruta}': {e}"


def correr_comando(comando: str, timeout: int = 30) -> str:
    """Ejecuta un comando del sistema operativo de forma segura (whitelist activa)."""
    permitido, motivo = _comando_permitido(comando)
    if not permitido:
        return f"ERROR: comando rechazado. Motivo: {motivo}"
    import subprocess

    try:
        resultado = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        salida = ""
        if resultado.stdout:
            salida += resultado.stdout
        if resultado.stderr:
            salida += f"\n[STDERR]\n{resultado.stderr}"
        MAX_SALIDA = 4000
        if len(salida) > MAX_SALIDA:
            salida = (
                salida[:MAX_SALIDA]
                + f"\n[... truncado, {len(salida) - MAX_SALIDA} caracteres mas]"
            )
        return f"[exit code {resultado.returncode}]\n{salida}"
    except subprocess.TimeoutExpired:
        return f"ERROR: el comando supero el timeout de {timeout} segundos y fue cancelado."
    except Exception as e:
        return f"ERROR al ejecutar '{comando}': {e}"


def buscar_texto(pattern: str, ruta: str = ".", extension: str = None) -> str:
    """Busca un patron (regex) en archivos de texto y devuelve las coincidencias."""
    import re
    import glob

    try:
        regex = re.compile(pattern)
    except re.error as e:
        return f"ERROR: regex invalido '{pattern}': {e}"
    if extension:
        search_path = os.path.join(ruta, "**", extension)
        archivos = glob.glob(search_path, recursive=True)
    else:
        archivos = []
        for root, dirs, files in os.walk(ruta):
            for f in files:
                archivos.append(os.path.join(root, f))
    if not archivos:
        return (
            f"(sin archivos en {ruta}"
            + (f" con extension {extension}" if extension else "")
            + ")"
        )
    resultados = []
    MAX_RESULTADOS = 50
    for archivo in archivos:
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                for i, linea in enumerate(f, 1):
                    if regex.search(linea):
                        contenido = linea.rstrip("\n")
                        if len(contenido) > 200:
                            contenido = contenido[:200] + "..."
                        resultados.append(f"{archivo}:{i}:{contenido}")
                        if len(resultados) >= MAX_RESULTADOS:
                            break
                if len(resultados) >= MAX_RESULTADOS:
                    break
        except (UnicodeDecodeError, PermissionError):
            continue
        except Exception as e:
            resultados.append(f"{archivo}:ERROR:{e}")
    if not resultados:
        return f"(sin coincidencias para '{pattern}' en {ruta})"
    salida = "\n".join(resultados)
    if len(resultados) >= MAX_RESULTADOS:
        salida += f"\n[... truncado, maximo {MAX_RESULTADOS} resultados]"
    return salida


def recordar(clave: str, valor: str) -> str:
    """Guarda un recuerdo persistente (clave=valor) entre sesiones."""
    memoria = cargar_memoria()
    memoria[clave] = valor
    guardar_memoria(memoria)
    return f"OK: recordado '{clave}' = '{valor}'"


def recuperar(clave: str) -> str:
    """Recupera un recuerdo guardado previamente por su clave."""
    memoria = cargar_memoria()
    valor = memoria.get(clave)
    if valor is None:
        return f"(no tengo nada recordado sobre '{clave}')"
    return f"{clave}: {valor}"


def listar_recuerdos() -> str:
    """Lista todos los recuerdos guardados."""
    memoria = cargar_memoria()
    if not memoria:
        return "(no tengo recuerdos guardados)"
    return "\n".join(f"  {k}: {v}" for k, v in memoria.items())


def fecha_hora(zona: str = "Europe/Madrid") -> str:
    """Devuelve la fecha y hora actual en una zona horaria especificada."""
    from datetime import datetime

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(zona)
    except (ImportError, KeyError):
        try:
            import pytz

            tz = pytz.timezone(zona)
        except ImportError:
            return f"ERROR: zona '{zona}' no disponible (sin zoneinfo ni pytz)"
    ahora = datetime.now(tz)
    return (
        f"Fecha: {ahora.strftime('%A, %d de %B de %Y')}\n"
        f"Hora: {ahora.strftime('%H:%M:%S')}\n"
        f"Zona: {zona}\n"
        f"ISO:  {ahora.isoformat()}"
    )


def tree(ruta: str = ".", max_nivel: int = 7) -> str:
    """Muestra el arbol de directorios con conectores graficos."""
    from pathlib import Path

    raiz = Path(ruta)
    if not raiz.is_dir():
        return f"ERROR: '{ruta}' no es un directorio"
    if max_nivel < 1:
        return f"ERROR: max_nivel debe ser >= 1"

    rama = "+-- "
    final = "\\-- "
    tubo = "|   "
    espacio = "    "

    lineas = [f"{raiz.resolve()}/"]

    def _recorrer(directorio: Path, nivel: int, prefijo: str):
        if nivel > max_nivel:
            lineas.append(f"{prefijo}{final}...")
            return

        entradas = sorted(
            directorio.iterdir(),
            key=lambda p: (not p.is_dir(), p.name.lower()),
        )

        for i, entrada in enumerate(entradas):
            es_ultimo = i == len(entradas) - 1
            conector = final if es_ultimo else rama

            if entrada.is_dir():
                lineas.append(f"{prefijo}{conector}{entrada.name}/")
                nuevo = espacio if es_ultimo else tubo
                _recorrer(entrada, nivel + 1, prefijo + nuevo)
            else:
                lineas.append(f"{prefijo}{conector}{entrada.name}")

    _recorrer(raiz, 0, "")
    return "\n".join(lineas)


def descargar_url(url: str, timeout: int = 15) -> str:
    """Descarga el contenido de una URL (maximo 100KB)."""
    import requests

    if not url.startswith(("http://", "https://")):
        return f"ERROR: URL debe empezar con http:// o https://"

    try:
        respuesta = requests.get(
            url, timeout=timeout, headers={"User-Agent": "Agente3573b4n/1.0"}
        )
    except requests.exceptions.Timeout:
        return f"ERROR: la URL no respondio en {timeout}s"
    except requests.exceptions.ConnectionError:
        return f"ERROR: no se pudo conectar a '{url}'"
    except requests.exceptions.RequestException as e:
        return f"ERROR al descargar: {e}"

    if respuesta.status_code != 200:
        return f"ERROR: HTTP {respuesta.status_code} ({respuesta.reason})"

    # Tamaño máximo: 100KB para no reventar el contexto del modelo
    limite = 100_000
    texto = respuesta.text[:limite]
    if len(respuesta.text) > limite:
        texto += f"\n[... truncado, {len(respuesta.text) - limite} bytes mas]"

    return texto


def notas(accion: str = "listar", texto: str = "", indice: int = None) -> str:
    """Gestiona notas personales: listar, agregar o borrar."""
    n = Notas()

    if accion == "listar":
        datos = n.listar()
        if not datos:
            return "(no hay notas guardadas)"
        return "\n".join(f"{i + 1}. {nota}" for i, nota in enumerate(datos))

    if accion == "agregar":
        return n.agregar(texto)

    if accion == "borrar":
        return n.borrar(indice)

    return f"ERROR: accion desconocida '{accion}'. Usa: listar, agregar, borrar"


def clima(ciudad: str) -> str:
    """Consulta el clima actual de una ciudad via OpenWeatherMap."""
    import requests

    api_key = os.environ.get("OPENWEATHER_API_KEY")
    if not api_key:
        return (
            "ERROR: falta la variable OPENWEATHER_API_KEY.\n"
            "  Consigue una clave gratis en https://openweathermap.org/api\n"
            "  Luego: $env:OPENWEATHER_API_KEY = 'tu-clave'"
        )

    try:
        respuesta = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": ciudad, "appid": api_key, "units": "metric", "lang": "es"},
            timeout=10,
        )
    except requests.exceptions.RequestException as e:
        return f"ERROR al consultar el clima: {e}"

    if respuesta.status_code == 404:
        return f"ERROR: ciudad '{ciudad}' no encontrada"
    if respuesta.status_code == 401:
        return "ERROR: API key invalida. Revisa tu OPENWEATHER_API_KEY"
    if respuesta.status_code != 200:
        return f"ERROR: API respondio con HTTP {respuesta.status_code}"

    datos = respuesta.json()
    main = datos["main"]
    viento = datos.get("wind", {})
    clima_str = datos["weather"][0]["description"]

    return (
        f"Ciudad: {datos['name']}, {datos.get('sys', {}).get('country', '')}\n"
        f"Clima: {clima_str}\n"
        f"Temperatura: {main['temp']}°C (sensacion: {main['feels_like']}°C)\n"
        f"Min/Max: {main['temp_min']}°C / {main['temp_max']}°C\n"
        f"Humedad: {main['humidity']}%\n"
        f"Viento: {viento.get('speed', 'N/A')} m/s"
    )


def ver_logs(lineas: int = 20) -> str:
    """Lee las ultimas N lineas del archivo de log del agente."""
    try:
        with open(_log_file, "r", encoding="utf-8") as f:
            todas = f.readlines()
        ultimas = todas[-lineas:]
        return "".join(ultimas)
    except FileNotFoundError:
        return "(aun no hay logs)"
    except Exception as e:
        return f"ERROR al leer logs: {e}"


# ---------------------------------------------------------------------------
# Herramientas adicionales
# ---------------------------------------------------------------------------


def ejecutar_python(codigo: str) -> str:
    """Ejecuta codigo Python y devuelve la salida estandar o el error."""
    import subprocess
    import sys

    try:
        resultado = subprocess.run(
            [sys.executable, "-c", codigo],
            capture_output=True,
            text=True,
            timeout=15,
        )
        salida = ""
        if resultado.stdout:
            salida += resultado.stdout[:5000]
        if resultado.stderr:
            salida += "\nSTDERR:\n" + resultado.stderr[:2000]
        if resultado.returncode != 0:
            salida += f"\n[exit code {resultado.returncode}]"
        else:
            salida = f"[exit code 0]\n{salida.strip()}"
        return salida
    except subprocess.TimeoutExpired:
        return "ERROR: ejecucion agoto el timeout (15s)"
    except Exception as e:
        return f"ERROR al ejecutar Python: {e}"


def copiar_archivo(origen: str, destino: str) -> str:
    """Copia un archivo de origen a destino, creando directorios si es necesario."""
    import shutil

    try:
        directorio_padre = os.path.dirname(destino)
        if directorio_padre and not os.path.exists(directorio_padre):
            os.makedirs(directorio_padre, exist_ok=True)
        shutil.copy2(origen, destino)
        tamano = os.path.getsize(destino)
        return f"OK: '{origen}' copiado a '{destino}' ({tamano} bytes)"
    except FileNotFoundError:
        return f"ERROR: origen no encontrado '{origen}'"
    except Exception as e:
        return f"ERROR al copiar: {e}"


def mover_archivo(origen: str, destino: str) -> str:
    """Mueve o renombra un archivo de origen a destino."""
    import shutil

    try:
        directorio_padre = os.path.dirname(destino)
        if directorio_padre and not os.path.exists(directorio_padre):
            os.makedirs(directorio_padre, exist_ok=True)
        shutil.move(origen, destino)
        return f"OK: '{origen}' movido a '{destino}'"
    except FileNotFoundError:
        return f"ERROR: origen no encontrado '{origen}'"
    except Exception as e:
        return f"ERROR al mover: {e}"


def eliminar_archivo(ruta: str) -> str:
    """Elimina un archivo especifico del disco (con confirmacion logica)."""
    try:
        if not os.path.exists(ruta):
            return f"(no existe '{ruta}', nada que borrar)"
        os.remove(ruta)
        return f"OK: '{ruta}' eliminado"
    except PermissionError:
        return f"ERROR: permiso denegado para eliminar '{ruta}'"
    except Exception as e:
        return f"ERROR al eliminar '{ruta}': {e}"


def info_sistema() -> str:
    """Devuelve informacion del sistema: espacio en disco, SO, Python."""
    import platform
    import shutil

    # Sistema operativo
    so = platform.system()
    release = platform.release()
    arquitectura = platform.machine()
    python_version = platform.python_version()

    # Espacio en disco de la unidad actual
    try:
        uso = shutil.disk_usage(".")
        total_gb = uso.total / (1024**3)
        usado_gb = uso.used / (1024**3)
        libre_gb = uso.free / (1024**3)
        disco = (
            f"Disco: {total_gb:.1f} GB total | {usado_gb:.1f} GB usado | "
            f"{libre_gb:.1f} GB libre"
        )
    except Exception:
        disco = "No se pudo obtener informacion del disco"

    return (
        f"Sistema: {so} {release}\n"
        f"Arquitectura: {arquitectura}\n"
        f"Python: {python_version}\n"
        f"{disco}"
    )


# ---------------------------------------------------------------------------
# Herramientas de Git
# ---------------------------------------------------------------------------


def git_status(ruta: str = ".") -> str:
    """Muestra el estado de git: archivos modificados, staged, untracked."""
    try:
        resultado = subprocess.run(
            ["git", "-C", ruta, "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not resultado.stdout.strip():
            return "OK: repositorio limpio (sin cambios)"
        lineas = resultado.stdout.strip().split("\n")
        resumen = f"{len(lineas)} archivo(s) con cambios:\n"
        for linea in lineas[:50]:
            resumen += f"  {linea}\n"
        if len(lineas) > 50:
            resumen += f"  ... y {len(lineas) - 50} mas\n"
        return resumen
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git status"
    except FileNotFoundError:
        return "ERROR: git no encontrado. ¿Estas en un repositorio git?"
    except Exception as e:
        return f"ERROR al ejecutar git status: {e}"


def git_diff(ruta: str = ".", archivo: str = None) -> str:
    """Muestra las diferencias sin staged de un archivo o todo el repositorio."""
    cmd = ["git", "-C", ruta, "diff"]
    if archivo:
        cmd.extend(["--", archivo])
    try:
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        diff = resultado.stdout[:3000]
        if not diff.strip():
            return "OK: sin diferencias"
        return f"--- Diferencias ---\n{diff}"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git diff"
    except FileNotFoundError:
        return "ERROR: git no encontrado"
    except Exception as e:
        return f"ERROR al ejecutar git diff: {e}"


def git_commit(mensaje: str, archivo: str = None) -> str:
    """Hace un commit de los cambios staged o de un archivo especifico."""
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10
        )
        if not status.stdout.strip():
            return "AVISO: no hay cambios para commitear"

        if not archivo:
            subprocess.run(["git", "add", "."], capture_output=True, timeout=10)

        cmd = ["git", "commit", "-m", mensaje]
        if archivo:
            cmd.append(archivo)

        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = resultado.stdout.strip()
        if resultado.returncode == 0:
            return f"OK: {output}"
        return f"ERROR: {resultado.stderr.strip() or output}"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git commit"
    except FileNotFoundError:
        return "ERROR: git no encontrado"
    except Exception as e:
        return f"ERROR al ejecutar git commit: {e}"


def git_log(max_commits: int = 20, ruta: str = ".") -> str:
    """Muestra el historial de commits recientes."""
    try:
        resultado = subprocess.run(
            [
                "git",
                "-C",
                ruta,
                "log",
                f"--max-count={max_commits}",
                "--pretty=format:%h %s (%an, %ar)",
                "--date=short",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if not resultado.stdout.strip():
            return "OK: repositorio sin commits"
        return resultado.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git log"
    except FileNotFoundError:
        return "ERROR: git no encontrado"
    except Exception as e:
        return f"ERROR al ejecutar git log: {e}"


def git_branch(ruta: str = ".") -> str:
    """Muestra las ramas del repositorio y la rama actual."""
    try:
        resultado = subprocess.run(
            ["git", "-C", ruta, "branch", "-v"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if resultado.returncode != 0:
            return f"ERROR: {resultado.stderr.strip()}"
        lineas = resultado.stdout.strip().split("\n")
        actual = "[no hay rama]"
        for linea in lineas:
            if linea.startswith("*"):
                actual = linea.replace("*", "→").strip()
                break
        return f"Branca actual: {actual}\n\nRamas:\n{resultado.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git branch"
    except FileNotFoundError:
        return "ERROR: git no encontrado"
    except Exception as e:
        return f"ERROR al ejecutar git branch: {e}"


def git_stash(accion: str = "save", mensaje: str = "") -> str:
    """Stash o pop de cambios temporales.

    Args:
        accion: 'save' (guardar), 'pop' (restaurar), 'list' (ver stash), 'drop' (eliminar ultimo)
        mensaje: mensaje opcional para el stash
    """
    try:
        if accion == "save":
            cmd = ["git", "stash", "save"]
            if mensaje:
                cmd.append(mensaje)
            else:
                cmd.append("auto-stash")
        elif accion == "pop":
            cmd = ["git", "stash", "pop"]
        elif accion == "list":
            cmd = ["git", "stash", "list"]
        elif accion == "drop":
            cmd = ["git", "stash", "drop"]
        else:
            return f"ERROR: accion '{accion}' desconocida. Usa save/pop/list/drop"

        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = resultado.stdout.strip()
        if resultado.returncode == 0:
            return f"OK: {output or 'comando ejecutado'}"
        return f"ERROR: {resultado.stderr.strip() or output}"
    except subprocess.TimeoutExpired:
        return "ERROR: timeout al ejecutar git stash"
    except FileNotFoundError:
        return "ERROR: git no encontrado"
    except Exception as e:
        return f"ERROR al ejecutar git stash: {e}"


TOOL_FUNCTIONS = {
    "leer_archivo": leer_archivo,
    "listar_directorio": listar_directorio,
    "escribir_archivo": escribir_archivo,
    "correr_comando": correr_comando,
    "buscar_texto": buscar_texto,
    "recordar": recordar,
    "recuperar": recuperar,
    "listar_recuerdos": listar_recuerdos,
    "ver_logs": ver_logs,
    "fecha_hora": fecha_hora,
    "tree": tree,
    "descargar_url": descargar_url,
    "notas": notas,
    "clima": clima,
    "ejecutar_python": ejecutar_python,
    "copiar_archivo": copiar_archivo,
    "mover_archivo": mover_archivo,
    "eliminar_archivo": eliminar_archivo,
    "info_sistema": info_sistema,
    # Git
    "git_status": git_status,
    "git_diff": git_diff,
    "git_commit": git_commit,
    "git_log": git_log,
    "git_branch": git_branch,
    "git_stash": git_stash,
}
